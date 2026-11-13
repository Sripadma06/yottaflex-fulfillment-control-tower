# 05 — Data Generation Strategy

Goal: a dataset whose every derived value is **computed by documented rules** from source rows; randomness is limited to a small set of *documented, parameterised input distributions* (arrivals, basket composition, carrier delay draws). Seed: **20261022**.

## 1. Determinism design

| Concern | Mechanism |
|---|---|
| Single seed → many streams | `numpy.random.SeedSequence(20261022)`; each stage gets `Generator(PCG64(SeedSequence(entropy=seed, spawn_key=(stable_hash(stage_name),))))` — adding/reordering stages doesn't shift other streams. `stable_hash` = first 8 bytes of SHA-256 (not Python `hash()`). |
| Faker | One `Faker('en_US')` instance per stage, `seed_instance(derived_int)`; used only for product names, city/postal text, carrier/node display names. Never for business numbers. |
| Ordering | Every table sorted by PK before export; no iteration over `set`/unsorted dict; sorts use total keys. |
| Time | No `datetime.now()`; simulation clock from config `window_start`; `created_at` = event time. `data_as_of` is a config value. |
| Identity | IDs are counters from `IdFactory`; no UUIDs. |
| Floats | Money = `Decimal`; rates/probabilities quantised before use; CSV floats written with fixed formatting; LF newlines, UTF-8, fixed column order, `\n` terminator. |
| Environment | Pinned dependency versions (`uv.lock`/`requirements.lock`); manifest records Python/NumPy/Faker versions; golden checksums asserted per pinned version (cross-version drift documented as a limitation). |
| Proof | `make repro` runs the full pipeline twice into separate dirs, compares row counts and SHA-256 per file, writes `reproducibility_report.md`. |

## 2. Pipeline stages (each = one module, one RNG stream, one log summary)

| # | Stage | Output | Rule source |
|---|---|---|---|
| 0 | Load/validate config; compute config hash | `RunContext` | YAML |
| 1 | Regions, zone matrix, calendars, holidays | `region, zone_matrix, calendar, holiday` | Holiday rules in YAML (named public holidays for 2026 computed from fixed rules — e.g. "4th Thursday of Nov"); plus node/carrier-specific closures declared in config |
| 2 | Carriers (10), service levels, service×zone transit/rates, delay profiles | `carrier, service_level, service_level_zone, delay_profile` | Config tables (transit by zone & service) |
| 3 | Fulfillment nodes (20), node×service cutoffs | `fulfillment_node, node_service_level` | Config: region assignment, time zones, handling hours, cutoffs |
| 4 | SKUs | `sku` | Category mix from config; Faker names; log-normal price/weight with documented parameters |
| 5 | Inventory baseline + replenishment schedule | `inventory`, scheduled receipts | Stocking model: per SKU, node stocking probability by category/node type (config); on-hand ~ NegBinomial around demand × cover-days (config). Shortages arise from *real depletion*, not random flags |
| 6 | Warehouse capacity | `warehouse_capacity` | Base units/orders per node-type; weekend/holiday reduction factors from config; optional outage days list |
| 7 | Orders + lines (arrival process) | `order, order_line` | Non-homogeneous Poisson by hour-of-day/day-of-week + seasonal multiplier (config); basket size ~ shifted geometric; SKU popularity Zipf (exponent in config); qty ~ small discrete dist; ship-to region ~ population weights (config). Totals **derived** |
| 8 | Simulation: allocate → reserve → capacity consume → promise (time-ordered) | `fulfillment, fulfillment_line, shipment(PLANNED), delivery_promise(+legs), inventory_ledger, allocation_decision_log, fulfillment_exception, order_status_history` | Real engine (`domain/allocation`, `domain/promise`) |
| 9 | Outcomes: dispatch, tracking events, delays, actual delivery, re-promise | `tracking_event`, shipment actuals, promise v02 | Outcome model §4 |
| 10 | Status rollup | order/shipment current status | Rollup table in config |
| 11 | Baseline validation (must be **zero** findings) | validation summary | Validator |
| 12 | Anomaly injection (copy-on-select) | mutated rows + `ground_truth` | §5 |
| 13 | Post-injection validation + evaluation | detection P/R | Validator/Evaluator |
| 14 | Export + manifest + checksums | CSV/JSON/SQL, docs | Exporters |

Stage 11 is a hard gate: injection never starts unless the baseline is clean, so every later finding is attributable to an injected label.

## 3. Volume plan and how targets are met

| Target | How | Note |
|---|---|---|
| 50,000 orders | `scale.orders` | Exact |
| 20 nodes / 10 carriers | config lists | Exact; ≥ 2 service levels per carrier |
| Split shipments | emerge from allocation when no single node covers all lines or split-gain rule triggers | Expected share reported (metric), not forced; config knob `basket_size`/stocking density tunes it; acceptance: ≥ 5 % orders split (A-11 for how tuned *inputs*, not outputs) |
| Inventory shortages | emerge from depletion + intentionally thin stocking for a configured SKU subset ("hot/scarce SKUs") | Exception counts reported |
| Capacity constraints | peak-day multipliers + capacity limits make some nodes saturate | `capacity_rolled_days` distribution reported |
| Holidays | calendar tables; some orders placed on/near holidays by arrival seasonality | Coverage test: ≥ N promises whose path crosses a holiday |
| Carrier delays | delay profile per carrier (probability × magnitude by cause) | Delay cause recorded |
| **100,000 tracking events** | Event template per service-level `tracking_detail`: BASIC = {DISPATCHED, DELIVERED}; STANDARD adds {IN_TRANSIT, OUT_FOR_DELIVERY}; FULL adds hub scans; exceptions add delay/attempt events. Config sets detail mix; generator **calibrates detail-mix at config time** (not by trimming rows) so total ≥ 100,000; actual count reported in manifest | A-02. ~50–60k shipments ⇒ ≈ 1.8–2.0 events/shipment minimum, so most shipments get BASIC/STANDARD; this is stated honestly in README |

`scale` parameter set: `starter` (e.g. 500 orders; still all 20 nodes / 10 carriers so every rule is exercised — only orders, SKUs and window shrink), `full` (50,000). Same code path (Step 4 of the statement).

## 4. Outcome model (actual delivery, delays) — no arbitrary outcomes

1. **Dispatch time:** `dispatched_at = ship_date @ pickup_time` of node×service (config); if capacity/handling slips are modelled they come from the capacity engine, not RNG.
2. **Baseline transit:** deterministic planned delivery (the un-buffered promise calculation).
3. **Delay draw:** per shipment, for each cause in the carrier's `delay_profile` (`WEATHER`, `VOLUME_SURGE`, `HUB_DELAY`, `ADDRESS_ISSUE`, `NONE`), a Bernoulli draw with probability = carrier base × zone factor × peak-season factor (all config). Magnitude (business days) from a documented discrete distribution per cause. Result = `delay_days`, `delay_cause`.
4. **Actual delivery:** planned delivery + `delay_days` snapped to carrier delivery calendar; time-of-day from carrier delivery window (config).
5. **Tracking events:** expanded from the template; event timestamps are monotone by construction (offsets from dispatch to delivery distributed by template fractions, then snapped to carrier operating hours). Delay → `DELIVERY_EXCEPTION` event + re-promise record.
6. **Shipments near `data_as_of`** remain `IN_TRANSIT`/`OUT_FOR_DELIVERY` with no delivery — a real boundary case, not an error.

The only randomness: arrival times/baskets (inputs), delay occurrence/magnitude (documented distributions). Everything downstream is a function.

## 5. Anomaly injection (five labelled scenarios)

Injection runs on the **already-valid** dataset. Rows are chosen by a seeded stream from an *eligibility pool* guaranteeing isolation (a row is eligible only if it has no other injection and mutation won't cascade into other validators).

| # | `issue_type` | Target table.field | Mutation | Isolation requirement | Expected detection rule |
|---|---|---|---|---|---|
| 1 | `PROMISE_BEFORE_ORDER_TIME` | `delivery_promise.promised_delivery_date` | Set earlier than `order.placed_at` date | single-version-promise orders | V-DATE-01 |
| 2 | `ALLOCATION_EXCEEDS_STOCK` | `fulfillment_line.qty_allocated` | Raise qty above ATP at allocation time (ledger untouched → reconciliation also breaks only for this row, labelled as expected secondary) | line of a single-node, non-shortage order | V-INV-01 (and V-INV-02 secondary, declared in label) |
| 3 | `SERVICE_UNSUPPORTED_FOR_ZONE` | `shipment.service_level_id` | Swap to a service whose `service_level_zone.supported=false` for that shipment's zone (FK stays valid) | shipments whose zone has ≥1 unsupported service | V-NET-01 |
| 4 | `DELIVERED_BEFORE_DISPATCH` | `shipment.actual_delivered_at` and DELIVERED event `event_ts` | Set earlier than `dispatched_at` | delivered shipments with ≥ 4 events | V-TRK-01 |
| 5 | `SPLIT_STATUS_ROLLUP_MISMATCH` | `order.delivery_status` | Set to value inconsistent with rollup (e.g. `DELIVERED` while one shipment `IN_TRANSIT`) | split orders with mixed shipment statuses | V-ROLL-01 |

**Ground-truth record** (`ground_truth.csv` + `.json`, and `gt.ground_truth_label`): `issue_id, scenario_no, issue_type, entity, entity_id, field, original_value, injected_value, expected_rule, expected_resolution, secondary_rules_expected, injected_seed_stream`.
Counts: `anomalies.per_scenario: 100` (A-12). Clean copies of mutated rows are kept **only** in ground truth (`original_value`), never in the feature tables. Features contain no `is_anomaly` column.

**Isolation test (automated):** diff(baseline, injected) must change exactly the rows/fields listed in ground truth — nothing else.

## 6. Provenance & lawful use

All data synthetic. No external datasets planned. Holiday rules are encoded from public calendar *conventions* (rule definitions, not a copied dataset); any reference consulted is listed in `source_manifest.md` with URL, version/date, licence, attribution, transformations, fields discarded (statement requirement). Faker outputs are fictional; no real PII.

## 7. Exports

`data/output/`: `csv/*.csv` (one per table), `json/*.json` (JSON Lines for big tables), `sql/seed.sql` (DDL-compatible `COPY`/INSERT), `ground_truth/ground_truth.{csv,json}`, `manifest.json` (seed, config hash, versions, row counts, SHA-256, tracking count, split %, generated command), `checksums.sha256`. Docs generated: `data_dictionary.md`, `validation_summary.md`, `reproducibility_report.md`, `source_manifest.md`.
Generator command (documented in README): `make gen SEED=20261022 SCALE=full` ≡ `python -m fulfillment.cli generate --seed 20261022 --scale full --out data/output`.
