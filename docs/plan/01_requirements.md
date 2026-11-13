# 01 — Requirements

Actors (from the problem statement): **Customer**, **Store/Warehouse Operator**, **Merchandising/E-commerce Analyst**, **Operations Manager**.

## 1. Functional requirements

IDs are referenced by tests and the traceability matrix (`07_…`).

### 1.1 Master data
| ID | Requirement |
|---|---|
| FR-01 | Generate/reference master data **before** transactions: SKU, FulfillmentNode, Carrier, ServiceLevel, Inventory, WarehouseCapacity, calendars, zones. |
| FR-02 | 20 fulfillment nodes, each with region, time zone, working calendar, pick cutoff, handling time, status and effective dates. |
| FR-03 | 10 carriers, each with calendar (pickup/delivery days), service levels, delay profile. |
| FR-04 | ServiceLevel defines transit rules per shipping zone (min/max days, business-day vs calendar-day), supported zones, tracking detail level, cost rate. Unsupported zone = explicit "unsupported", never a missing row ambiguity. |
| FR-05 | Node×ServiceLevel bridge carries carrier **cutoff time** (node-local) and effective dates. |
| FR-06 | Holiday & working-day calendars (node, carrier) with closed/partial days and effective dates. |
| FR-07 | Inventory per SKU×node with on-hand, reserved, safety stock; every change recorded in an append-only ledger. |
| FR-08 | WarehouseCapacity per node per date (units/day, orders/day); usage derived from fulfillments, not stored independently. |

### 1.2 Orders and fulfillment
| ID | Requirement |
|---|---|
| FR-10 | Generate/accept Orders with OrderLines (SKU, qty, unit price); totals derived from lines. |
| FR-11 | Order lifecycle with history table (no overwrite): `CREATED → ALLOCATED → PARTIALLY_SHIPPED → SHIPPED → PARTIALLY_DELIVERED → DELIVERED`; side states `BACKORDERED`, `UNFULFILLABLE`, `CANCELLED`. |
| FR-12 | Allocation engine selects node(s) per order: **single-node first**, **split** when no single node can serve or when policy says split materially improves the promise. |
| FR-13 | Allocation respects available-to-promise inventory and node capacity on the processing day. |
| FR-14 | Each allocation is recorded as a Fulfillment (`FUL-…`) with fulfillment lines; each Fulfillment yields one Shipment. |
| FR-15 | Allocation decisions are traceable: candidates considered, scores, rejection reasons stored in a decision log. |
| FR-16 | Support partial fulfillment / backorder per order policy flag. |

### 1.3 Delivery promise
| ID | Requirement |
|---|---|
| FR-20 | Calculate promise from: order release time, node cutoff/working calendar, capacity-feasible processing day, carrier pickup cutoff & calendar, zone transit time, carrier delivery calendar, holidays. |
| FR-21 | Order-level promise = latest leg promise (split shipments); leg-level detail stored with a calculation trace. |
| FR-22 | Promises are **versioned** (`PROM-<order>-01`, `-02`) — re-promise after an exception creates a new version; old versions retained. |
| FR-23 | Promise is never earlier than order time; never lands on a non-delivery day. |
| FR-24 | Optional "what-if" quote endpoint that persists nothing. |

### 1.4 Shipment, tracking, outcomes
| ID | Requirement |
|---|---|
| FR-30 | Shipment lifecycle: `PLANNED → PACKED → DISPATCHED → IN_TRANSIT → OUT_FOR_DELIVERY → DELIVERED`, with exception branches `DELIVERY_EXCEPTION`, `RETURNED_TO_SENDER`. |
| FR-31 | TrackingEvent is append-only, ordered by `sequence_no`, strictly non-decreasing timestamps; shipment status = status of latest event. |
| FR-32 | Actual delivery outcome derived from a documented carrier delay model + calendars; delay cause stored. |
| FR-33 | Order-level delivery status derived from shipment statuses via a documented rollup table (config). |
| FR-34 | Carrier delay events can trigger exception records and re-promise. |

### 1.4b Exceptions & anomalies
| ID | Requirement |
|---|---|
| FR-40 | Typed exception records for: inventory shortage, capacity overflow, unsupported service/zone, no feasible carrier, carrier delay, promise miss. |
| FR-41 | Five **labelled** anomaly scenarios injected *after* a valid baseline: (1) promise before order time, (2) allocation exceeds stock, (3) carrier service unsupported for zone, (4) shipment delivered before dispatch, (5) split shipment status not rolled up correctly. |
| FR-42 | Separate `ground_truth` outputs (CSV+JSON) with `issue_type`, entity, id, field, original/injected value, expected detection rule. Never read by the engine or validator. |

### 1.5 Data pipeline & API
| ID | Requirement |
|---|---|
| FR-50 | Generator CLI, scale-parameterised (starter vs full use same code), fixed seed `20261022`. |
| FR-51 | Exports: CSV, JSON, SQL seed, data dictionary, source manifest, validation summary, README. |
| FR-52 | Validator: PK uniqueness, FK integrity, enums, date ordering, arithmetic reconciliation, lifecycle transitions, duplicates, business-rule checks. |
| FR-53 | Evaluator: compares validator findings to ground truth (precision/recall per scenario) and reports business metrics. |
| FR-54 | Reproducibility check command: generate twice, compare row counts and SHA-256 per file. |
| FR-55 | FastAPI endpoints: quote promise, fulfill order, get order / trace / shipments / tracking, append tracking event, list exceptions, run validation, metrics, health. |
| FR-56 | Load generated data into PostgreSQL (Alembic-created schema) and run the same validator against the DB. |

## 2. Non-functional requirements

| ID | Category | Requirement | How verified |
|---|---|---|---|
| NFR-01 | Determinism | Same seed + same config ⇒ byte-identical outputs. Per-stage named RNG streams (NumPy `SeedSequence` + stage name), Faker seeded per stage, no wall-clock, no `uuid4`, no unordered iteration. | Twice-run checksum test |
| NFR-02 | Reproducibility | Config hash + code version + seed in manifest. | Manifest test |
| NFR-03 | Configurability | All business rules in versioned YAML validated by Pydantic; zero business constants in code (`ruff` custom check / grep gate in CI). | Config tests, lint gate |
| NFR-04 | Modularity | Layered: domain (pure) ← services ← adapters (DB/API/CLI). Domain has no SQLAlchemy/FastAPI imports. | Import-linter contract |
| NFR-05 | Correctness | Derived values computed only from source records. | Reconciliation validators |
| NFR-06 | Performance | Full generation ≤ 10 min on a laptop; PG load via `COPY` ≤ 3 min; single promise quote p95 < 100 ms (indexed lookups, in-memory calendars). | Benchmark script |
| NFR-07 | Observability | Structured logging (JSON option), correlation/run ID, per-stage counts and timings; decisions logged at DEBUG, exceptions at WARNING/ERROR. | Log tests |
| NFR-08 | Error handling | Domain exception hierarchy; API returns RFC 7807 problem details; generator fails fast on invalid config. | Unit tests |
| NFR-09 | Typing/quality | Full type hints, `mypy --strict` on domain/services, `ruff`, `black`. | CI |
| NFR-10 | Testing | Unit (rules, calendars, allocation, promise), integration (PG, API), property-based (calendar arithmetic), golden-file tests, coverage ≥ 85 % on domain+services. | pytest |
| NFR-11 | Portability | Runs locally with Docker Compose (Postgres) or SQLite-free pure-CSV mode for generator. Free/local only. | README run-through |
| NFR-12 | Security & privacy | No real PII (Faker-generated, opaque customer refs), no secrets in repo, `.env.example` only. | Secret scan |
| NFR-13 | Data integrity | FK + CHECK + UNIQUE constraints in DB mirror validator rules. | Integration tests |
| NFR-14 | Auditability | No update-in-place of history (status history, promises, ledger, tracking). | Validator + DB triggers/tests |
| NFR-15 | Provenance | All data synthetic; any public reference cited for schema inspiration only, with URL/date/licence in the source manifest. | Manifest |
| NFR-16 | Documentation | README, data dictionary, ADRs, assumptions, limitations, AI-use disclosure, prompt history. | Review checklist |
