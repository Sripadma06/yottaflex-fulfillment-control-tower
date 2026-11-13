# 04 — Business Workflow, Allocation, Promise, Exceptions

## 1. End-to-end business workflow

```mermaid
flowchart TD
  A[1 Reference data: regions, zones, calendars, holidays, nodes, carriers, services, SKUs] --> B[2 Inventory + capacity baseline per node/date]
  B --> C[3 Orders + lines generated in time order]
  C --> D[4 Release: order_release_lag, validity checks]
  D --> E{5 Allocation engine}
  E -- plan found --> F[6 Reserve inventory ledger + consume capacity]
  E -- partial / none --> X[Exception: shortage → backorder / partial / unfulfillable]
  F --> G[7 Create FUL records + lines, Shipments PLANNED]
  G --> H[8 Promise engine per leg → order promise v01 + legs + trace]
  H --> I[9 Outcome simulation: dispatch, tracking events, carrier delays, actual delivery]
  I --> J{Delay beyond promise?}
  J -- yes --> K[Exception CARRIER_DELAY → re-promise v02]
  J -- no --> L
  K --> L[10 Status rollup: shipment → order delivery status]
  L --> M[11 Anomaly injection on copies of valid rows → ground_truth]
  M --> N[12 Validate → Evaluate → Export + manifest + reproducibility check]
```

Mapping to the problem statement's workflow: step 1–2 = "generate master data first"; 3–9 = "generate dependent records with valid parent IDs, apply business logic"; every state change is an appended record (rule 4); outcomes derive from rules (rule 5).

The simulation processes orders in `(placed_at, order_seq)` order so inventory depletion, replenishment receipts and capacity consumption are causally consistent.

## 2. Fulfillment allocation decision flow

```mermaid
flowchart TD
  S([Order released]) --> V{Valid? lines>0, qty>0, SKU active, ship-to region known}
  V -- no --> E0[Exception INVALID_ORDER]
  V -- yes --> N1[Eligible nodes: ACTIVE at placed_at, node_service_level exists, service supports dest zone]
  N1 --> N2{Any eligible node?}
  N2 -- no --> E1[Exception NO_ELIGIBLE_NODE / SERVICE_UNSUPPORTED_FOR_ZONE]
  N2 -- yes --> A1[ATP per SKU×node = on_hand − reserved − safety_stock  inbound excluded unless configured]
  A1 --> P1[Single-node candidates: nodes with ATP ≥ qty for ALL lines]
  P1 --> Q{Any single-node candidate?}
  Q -- yes --> C1[Quote promise for each candidate × eligible service level, capacity-aware]
  C1 --> SPL{Split improves promise ≥ split_if_promise_gain_days?}
  Q -- no --> G1[Split planner: greedy cover — pick node maximising covered line-units, tie-break score; repeat ≤ max_split_nodes]
  SPL -- no --> W[Score and pick best single]
  SPL -- yes --> G1
  G1 --> G2{Fully covered?}
  G2 -- yes --> C2[Quote each leg; plan promise = latest leg]
  C2 --> W
  G2 -- no --> PF{allow_partial / policy?}
  PF -- yes --> PP[Allocate available qty; remainder → BACKORDER exception, order PARTIALLY_ALLOCATED path]
  PF -- no --> BO[Whole order BACKORDERED, exception INVENTORY_SHORTAGE]
  PP --> W
  W --> K1["Score = w1·promise_delay + w2·cost + w3·split_penalty·(legs−1) + w4·node_load; ties: promise_date, node_id"]
  K1 --> R[Transactional commit: ledger RESERVE, FUL+lines, shipment, promise, decision log]
```

Determinism rules: candidate lists are sorted by `node_id`; scores are `Decimal`; ties are resolved by the configured `tie_break` list — never by dict/set order or RNG.

**Capacity handling inside allocation:** a leg is feasible on day *D* only if `used_units(D)+leg_units ≤ max_units(D)` and `used_orders(D)+1 ≤ max_orders(D)`. If not, the promise engine rolls the processing day forward (up to `capacity_lookahead_days`); each rolled day is recorded (`capacity_rolled_days`) and adds to promise delay, which the scorer sees — so capacity pressure naturally steers orders to other nodes. If no day in the horizon fits ⇒ leg infeasible ⇒ `CAPACITY_OVERFLOW` exception and that node is dropped from candidates.

## 3. Delivery promise calculation flow

Per leg (node *n*, service level *s*), all arithmetic uses calendars; every step writes to `trace_json`.

```mermaid
flowchart TD
  I([placed_at UTC]) --> R1[release_ts = placed_at + order_release_lag]
  R1 --> L1[Convert to node-local time]
  L1 --> D1{Day is node working day AND local time ≤ node pick_cutoff?}
  D1 -- yes --> P0[process_day = that day]
  D1 -- no --> P1[process_day = next node working day]
  P0 --> C1
  P1 --> C1{Capacity on process_day sufficient units+orders?}
  C1 -- no --> C2[process_day = next working day with capacity ≤ lookahead; count rolled days] --> C1
  C1 -- yes --> H1["ready_ts = max(release_local, open_time) + handling_hours on process_day; if process_day ≠ placed day, start = open_time"]
  C2 -. none within horizon .-> EX[infeasible → CAPACITY_OVERFLOW]
  H1 --> K1{ready_ts local ≤ node×service cutoff AND process_day is carrier pickup day?}
  K1 -- no --> K2[ship_date = next carrier pickup day  cutoff_met = false for process_day]
  K1 -- yes --> K3[ship_date = process_day  cutoff_met = true]
  K2 --> T1
  K3 --> T1[Lookup transit_days for service×zone: supported? else SERVICE_UNSUPPORTED_FOR_ZONE]
  T1 --> T2[Advance transit_days on service day-type: BUSINESS → skip non-delivery days & holidays; CALENDAR → add days]
  T2 --> T3{Landing day is carrier delivery day?}
  T3 -- no --> T4[snap forward to next carrier delivery day]
  T3 -- yes --> B1
  T4 --> B1[Add buffer_days from carrier reliability band, counted in delivery days]
  B1 --> M1[Leg promise_date]
  M1 --> M2[Order promise = max leg promise_date; earliest/latest window from transit min/max]
  M2 --> V1{promise ≥ placed_at date? ≤ requested_delivery_by?}
  V1 -- violates --> W1[Flag SLA_RISK exception; still persist promise with flag]
  V1 -- ok --> OUT([persist PROM-order-NN + legs + trace])
```

Rules worth stating explicitly:
* **Zone** = `zone_matrix[node.region, order.ship_to_region]`; unsupported (`supported=false` or missing) ⇒ the service is removed from candidates, never silently defaulted.
* **Cutoff** compared in node-local time; DST handled via `zoneinfo`; a `cutoff_met=false` is not an error, it's a rolled day with trace.
* **Holidays:** node holidays move *processing*; carrier holidays move *pickup* and *delivery*; both calendars are consulted independently.
* **Buffer** = lookup of carrier `reliability_band` in config (A-09); `0` allowed.
* **Re-promise:** on `CARRIER_DELAY` exceptions the engine recomputes from the current position (dispatched_at, delay event) and appends v(N+1) with `supersedes_promise_id`; v01 is never edited.
* **Actual outcome (not promise):** `actual_delivery = planned_delivery_without_delay + delay_days(delay profile)` re-snapped to carrier delivery calendar; delay cause label stored. Promise and outcome therefore differ *by rule*, producing a measurable on-time metric.

## 4. Exception handling strategy

### 4.1 Two kinds of "exception"

| Kind | Meaning | Handling |
|---|---|---|
| **Business exceptions** (runtime) | Valid situations the system must handle: shortage, capacity overflow, unsupported service/zone, carrier delay, promise at risk | Typed `fulfillment_exception` record + deterministic remedy + status history; processing continues |
| **Data anomalies** (injected) | Corrupt/contradictory records for testing detection | Labelled in ground truth; detected by validator; never produced by the engine |
| **Technical errors** | Bad config, DB failure, invalid input | Domain error hierarchy; fail fast (generator) or RFC 7807 response (API); logged with run ID |

### 4.2 Business exception catalogue

| Code | Detection | Remedy (config) | Resulting state |
|---|---|---|---|
| `INVENTORY_SHORTAGE` | ATP < qty on all single nodes and split cannot cover | partial (if `allow_partial`) else backorder | Order BACKORDERED / partial |
| `CAPACITY_OVERFLOW` | No capacity day within lookahead | drop node; try next candidate; else backorder | exception OPEN |
| `SERVICE_UNSUPPORTED_FOR_ZONE` | `service_level_zone.supported=false` | exclude service; fall back to next service level | candidate removed |
| `NO_ELIGIBLE_NODE` | eligibility filter empty | UNFULFILLABLE | terminal |
| `CARRIER_DELAY` | tracking delay event / delivery > promise | re-promise v+1 | exception RESOLVED on re-promise |
| `PROMISE_MISS` | actual > promised (after buffer) | record only (KPI) | metric |
| `SLA_RISK` | promise > requested_delivery_by | record + flag | exception OPEN |
| `INVALID_ORDER` | validation | reject | CANCELLED |

### 4.3 Technical error taxonomy

```
FulfillmentError
├── ConfigurationError          (invalid/missing YAML value → exit code 2 / startup failure)
├── DomainRuleViolation
│   ├── InsufficientInventoryError
│   ├── CapacityExceededError
│   ├── UnsupportedServiceZoneError
│   └── InvalidLifecycleTransitionError
├── NotFoundError               (→ 404)
├── ConflictError / IdempotencyError  (→ 409)
└── PersistenceError            (→ 503, retriable flag)
```

* API: global handlers map to RFC 7807 (`type`, `title`, `status`, `detail`, `instance`, `run_id`).
* Services never swallow exceptions; they either convert to a business-exception record (expected outcomes) or re-raise.
* Transactions: one unit of work per fulfill call; rollback on any error; exceptions-as-records written *in the same* transaction as the decision they explain.
* Generator: stage-level try/except logs stage, counts, config hash, then aborts non-zero — never emits a partially valid dataset.
* Logging: JSON lines, fields `ts, level, run_id, stage, order_id, event`; INFO per stage summary, DEBUG per decision, WARNING per business exception, ERROR per technical error. Per-record INFO is prohibited (50k orders).
