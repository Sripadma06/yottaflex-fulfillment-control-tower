# 06 — Validation & Evaluation Strategy

Three separate concerns, three separate components:

| Component | Question | Reads ground truth? |
|---|---|---|
| **Validator** | Is the data internally consistent and rule-compliant? | **No** (import-linter enforced) |
| **Evaluator — detection** | Did the validator find exactly the injected anomalies? | Yes (only here) |
| **Evaluator — business** | How well do allocation and promises perform? | No |

## 1. Validator rule catalogue

Each rule is a class with `rule_id`, `severity`, `check(dataset) -> list[Finding]`, runs on CSV dataset **and** on PostgreSQL (same rule via a dataframe/SQL dual implementation tested for parity).

| Family | Rule IDs | Checks (Problem statement Step 8) |
|---|---|---|
| Primary keys | V-PK-* | Uniqueness and non-null per table; ID format regex per convention; counters contiguous |
| Foreign keys | V-FK-* | Every FK resolves (all joins listed in `03_database.md` §3.3); orphan counts |
| Enums | V-ENUM-* | Status/type/zone values ∈ config enums |
| Date ordering | V-DATE-01 promise ≥ order date; V-DATE-02 ship_date ≥ process_day ≥ order date; V-DATE-03 delivery ≥ ship; effective_from < effective_to | |
| Calendar | V-CAL-01 promised/ship dates on valid working/pickup/delivery days; V-CAL-02 not on carrier/node holiday; V-CAL-03 cutoff logic re-derivable | "promised dates follow calendars and cutoffs" |
| Arithmetic | V-ARITH-01 order_total = Σ lines; line_total = qty×price; V-ARITH-02 Σ fulfillment_line qty per order_line = qty (± recorded backorder); V-ARITH-03 capacity_units_used = Σ qty×handling_units | Reconciliation |
| Inventory | V-INV-01 allocation ≤ ATP at allocation time; V-INV-02 ledger balance chain reconciles to snapshot; V-INV-03 reserved ≤ on_hand | "allocation respects inventory" |
| Capacity | V-CAP-01 per node/date usage ≤ capacity | "…and capacity" |
| Network | V-NET-01 shipment service supported for shipment zone; node×service row exists; V-NET-02 zone = matrix(node region, ship-to region) | |
| Lifecycle | V-LIFE-* transitions ∈ allowed table, for order status history, shipment events | |
| Tracking | V-TRK-01 DELIVERED not before DISPATCHED; V-TRK-02 `sequence_no` contiguous from 001; timestamps non-decreasing; V-TRK-03 exactly one terminal event; V-TRK-04 shipment.status = last event status | "tracking timeline is valid" |
| Rollup | V-ROLL-01 order delivery status = rollup(shipment statuses) (re-derived independently of the engine code path); V-ROLL-02 split orders have ≥ 2 FUL | "order-level delivery status correctly derived" |
| Promise | V-PROM-01 versions contiguous; supersedes chain valid; order promise = max leg promise; V-PROM-02 history not overwritten (version immutability by checksum in meta) | |
| Duplicates | V-DUP-* | Duplicate natural keys (order_id+line_no, shipment tracking_number), duplicate events |

Output: `validation_summary.md/json` — per rule: status, rows checked, findings count, sample IDs.

**Independence principle:** validators re-derive expectations with *separate simple implementations* (e.g. a brute-force working-day walker) rather than calling the production calendar engine, so a bug in the engine can't hide itself. Where code is shared by design (calendar), property tests cross-check it against the brute-force version.

## 2. Evaluation

### 2.1 Detection quality (needs ground truth)
Join validator findings with ground truth on `(entity, entity_id, expected_rule)`:
* Per scenario: TP, FP, FN, precision, recall (target: **recall = 100 %, precision = 100 %** for the five scenarios; any FP on baseline is a bug since baseline must be clean).
* Declared secondary findings (e.g. V-INV-02 for scenario 2) count as expected, not FP.
* Isolation check: diff(baseline, injected) == ground-truth footprint.

### 2.2 Business metrics (evaluation focus a–g)
| Metric | Definition |
|---|---|
| On-time promise rate | delivered ≤ promised_date (final version vs initial) |
| Promise error (days) | actual − promised; mean, MAE, P50/P90 by carrier/zone/service |
| Single vs split share | % orders by # of FUL; avg nodes/order |
| Split value | median promise gain days when split chosen vs best single (from decision log) |
| Fill rate / shortage rate | % lines fully allocated first-pass; % orders backordered/partial |
| Capacity utilisation | per node/day: used/max; % node-days at cap; rolled-days distribution |
| Cutoff-miss rate | % legs with `cutoff_met=false` |
| Carrier delay rate & cause mix | by carrier |
| Re-promise rate | % orders with v02 |
| Holiday impact | mean promise lead time on holiday-crossing vs not |
| Distribution realism | order/hour, basket size, SKU popularity (Zipf fit), delay histograms (plots/tables) |

Metrics are computed from stored records (SQL + pandas), exposed at `/v1/metrics` and `docs/validation_summary.md`.

## 3. Test strategy (pytest)

| Layer | Tests |
|---|---|
| Unit | calendar arithmetic (weekend, holiday, DST, cutoff edges: exactly-at-cutoff, 1 min after), promise engine (golden table of hand-computed cases), allocation (single, split, shortage, tie-break), rollup table (all combinations), outcome model (given seed), ID factories, config validation (bad YAML rejected) |
| Property (hypothesis) | promise ≥ placed date; promise on delivery day; monotonicity (later order ⇒ not earlier promise, same state); calendar `add_working_days` matches brute-force |
| Integration | Alembic up/down; `COPY` load; FK/CHECK enforcement; append-only triggers; API flows (quote → fulfill → track → rollup); validator parity CSV vs PG; anomaly isolation; detection P/R = 100 % |
| Reproducibility | small-scale generation twice ⇒ identical checksums; golden checksum for starter scale |
| Static | `mypy --strict` (domain, services), `ruff`, import-linter, hardcode-literal gate |
| Performance | benchmark script: full generation time, quote latency |

## 4. Verification evidence artefacts (committed or generated)

`validation_summary.md`, `reproducibility_report.md`, `evaluation_report.md` (metrics + detection P/R), coverage report, CI log. These satisfy the guideline "demonstrate how you verified core functionality".
