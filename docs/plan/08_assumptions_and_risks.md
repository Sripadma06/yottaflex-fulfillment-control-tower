# 08 — Assumption Register, Open Questions, Risks

Every assumption is explicit, has an owner-visible config key where it affects behaviour, and is repeated in `docs/00_assumptions.md` in the repo. "Impact if wrong" tells you what to change.

## 1. Assumptions

| ID | Assumption (the problem statement is silent/ambiguous) | Rationale | Config key | Impact if wrong |
|---|---|---|---|---|
| A-01 | `FUL-2026-000001` identifies a **Fulfillment** (order×node allocation unit). FulfillmentNode keys are `NODE-###`. | The statement lists FUL under ID conventions but there is no Fulfillment entity in the core 11; split shipments and "allocation exceeds stock" need an allocation record. | `id_formats` | Rename/re-key; schema otherwise unchanged |
| A-02 | 100,000 tracking events is a **minimum** reached by calibrated tracking-detail mix, not by padding or truncation. | ~50–60k shipments → ≈2 events each leaves little room; padding would be arbitrary. | `tracking.detail_mix` | Different template mix |
| A-03 | One Shipment per Fulfillment (1:1); one parcel per shipment. | Keeps split-shipment semantics clear. | — | Add `package` table |
| A-04 | Order window and as-of date are config values (default: orders 2026-01-01…2026-09-30; `data_as_of` 2026-10-31) so a realistic tail of in-transit shipments exists and `2026` matches the ID year. | Needed for non-trivial "actual outcomes"; seed hints at Oct 2026. | `window`, `data_as_of` | Edit dates |
| A-05 | Geography is **synthetic**: 8 regions, a region×region zone matrix (zones 1–8), no real postcodes/tariffs. | Avoids licensing/provenance risk (statement: use synthetic if unclear). | `zones.yaml` | Swap matrix |
| A-06 | Node holds stock for a SKU only per `inventory`; ATP = on_hand − reserved − safety_stock; inbound receipts are not promisable. | Conservative, common OMS default. | `allocation.atp` | Toggle inbound |
| A-07 | Handling time and cutoffs are per node (and node×service) values; same-day processing only if release time ≤ node pick cutoff. | Standard WMS wave/cutoff model. | `nodes.yaml` | Edit values |
| A-08 | Carriers pick up and deliver per their calendar (weekday set + holidays); Sunday/holiday behaviour differs per carrier via config. | Real carriers differ. | `calendars` | Edit calendar |
| A-09 | Promise buffer is by carrier reliability band, not by learned model. | Documented rule, not arbitrary. | `promise.buffer_days_by_reliability_band` | Set to 0 |
| A-10 | Split chosen if no single node covers the basket, **or** it improves promise by ≥ N days (config); capped at 3 legs. | Typical OMS trade-off between speed and shipping cost. | `allocation.split_*` | Tune |
| A-11 | Split %, shortage %, capacity saturation **emerge** from tuned *input* parameters (stocking density, capacity levels, basket sizes), never from forcing output labels. Acceptance thresholds are checks on emergence. | "Generate outcomes from rules, not independent random assignment." | `generation.yaml` | Retune inputs |
| A-12 | 100 injected rows per anomaly scenario (500 total). | Enough to measure P/R; small enough to not distort metrics. | `anomalies.per_scenario` | Change count |
| A-13 | Orders are placed in UTC-stored timestamps; customer region determines delivery zone; no customer entity table (opaque `customer_ref`). | Minimise PII and scope. | — | Add table |
| A-14 | Currency single (USD); prices informational; shipping cost used only as a scoring input. | Scope control. | `currency` | — |
| A-15 | Cancellations/returns beyond RETURNED_TO_SENDER are out of scope. | Not in required workflow. | — | Extend lifecycle |
| A-16 | Shipping cost = `rate_base + rate_per_kg × weight` from service×zone table (synthetic). | Needed for scoring; no real tariffs. | `service_level_zone` | Edit |
| A-17 | Delivery time-of-day is carrier delivery window midpoint ± deterministic offset; promise is date-granular. | Promise is a date in the statement. | `carriers.yaml` | — |
| A-18 | Holiday set = public-holiday *rules* for 2026 (US-style) + declared node/carrier closures; no external download. | Lawful, reproducible. | `holidays.yaml` | Swap set |
| A-19 | Re-promise happens only on carrier delay exceptions, once per exception. | Bounded complexity. | `promise.re_promise` | Extend |
| A-20 | Dependency versions pinned; byte-identical reproducibility is guaranteed for pinned versions only. | NumPy/Faker may change streams. | lockfile | Re-baseline checksums |

## 2. Open questions (ask recruiter if reachable; otherwise assumptions above stand)

1. Is `FUL-…` a node ID or a fulfillment/allocation ID? (A-01)
2. Is 100,000 tracking events an exact or minimum target? (A-02)
3. Preferred geography/currency? Any real-carrier naming expected? (A-05, A-14)
4. Is a DB load mandatory for review, or are CSV/JSON/SQL exports sufficient? (FAQ: tests/demo not mandatory)

## 3. Risks

| Risk | L | I | Mitigation |
|---|---|---|---|
| Scope too large for 72 h | M | H | Milestone buffer; explicit descoping order; core path first |
| Non-determinism via dict/set order, Faker or NumPy version | M | H | Named RNG streams, sorted iteration, pinned lock, repro test from M0 |
| Anomaly injection cascades into other rules ⇒ ground truth not exact | M | H | Eligibility pools, declared secondary rules, isolation diff test |
| Engine bug hidden because validator reuses it | M | H | Independent brute-force re-derivation in validator; property tests |
| 100k events constraint conflicts with realistic timelines | H | M | A-02, documented honestly |
| Split rate/shortage rate too low or too high | M | M | Tune *inputs* (A-11), report emergent rates |
| DB checks reject anomaly rows | H | M | Two-mode loader (§03 §4) |
| Generator performance (50k × candidate plans) | M | M | In-memory repos, pre-built calendar caches, vectorised ATP; benchmark in M5 |
| AI-disclosure/prompt-history forgotten | M | H | Capture prompts from M0; checklist in M10 |
| Plan contradicts "no scattered constants" through test fixtures | L | L | Fixtures read from test config |
