# Order Fulfillment & Delivery Promise Optimization — Technical Implementation Plan

Status: **PLAN ONLY — no implementation code.** Version 1.0 · Seed `20261022`

## 1. What this plan is

An architecture and delivery plan for the YottaFlex AI candidate project:
*select fulfillment nodes and promise dates using inventory, warehouse capacity, carrier cutoffs and shipping service levels*, with a deterministic synthetic dataset (50,000 orders, 20 nodes, 10 carriers, ≥100,000 tracking events), five labelled anomaly scenarios, a validator, an evaluator and a FastAPI service.

## 2. Document index (maps to the 15 requested sections)

| # | Requested section | Document |
|---|---|---|
| 1 | Functional requirements | `01_requirements.md` §1 |
| 2 | Non-functional requirements | `01_requirements.md` §2 |
| 3 | System architecture | `02_architecture.md` §1–3 |
| 4 | Module breakdown | `02_architecture.md` §4 |
| 5 | Database architecture | `03_database.md` §1–4 |
| 6 | Entity relationship overview | `03_database.md` §5 |
| 7 | End-to-end business workflow | `04_workflows.md` §1 |
| 8 | Fulfillment allocation decision flow | `04_workflows.md` §2 |
| 9 | Delivery promise calculation flow | `04_workflows.md` §3 |
| 10 | Exception handling strategy | `04_workflows.md` §4 |
| 11 | Data generation strategy | `05_data_generation.md` |
| 12 | Validation and evaluation strategy | `06_validation_evaluation.md` |
| 13 | Project directory structure | `02_architecture.md` §6 |
| 14 | Development milestones | `07_milestones_acceptance.md` §1 |
| 15 | Acceptance criteria mapped to assignment | `07_milestones_acceptance.md` §2–3 |
| — | Assumption register, open questions, risks | `08_assumptions_and_risks.md` |
| — | AI-use / prompt-history scaffold | `docs_ai_README_template.md` |

## 3. Source-of-truth requirements used

Three project documents were analysed: **Problem statement**, **Submission Guidelines**, **FAQ**. Requirements from them that shape the plan beyond your brief:

* Mandatory ID formats: `ORD-2026-000001`, `FUL-2026-000001`, `SHP-2026-000001`, `TRK-<shipment-id>-001`, `PROM-<order-id>-01`.
* The five required edge cases (exact names): *promise before order time; allocation exceeds stock; carrier service unsupported for zone; shipment delivered before dispatch; split shipment status not rolled up correctly*.
* History must never be overwritten (explicit records/events; promise versions `-01`, `-02`).
* Anomalies carry an `issue_type`/ground-truth label and **must not silently corrupt unrelated rows**.
* Separate `ground_truth` file that never leaks into input features.
* Derived values come from source records, never independent random draws.
* Export CSV/JSON/SQL seed + README + data dictionary + generator command + seed + source manifest + validation summary.
* Regenerate twice and compare row counts/checksums.
* Submission: public GitHub repo, meaningful commits, runnable setup steps, **prompt history of every AI prompt**, honest AI-use disclosure, assumptions, limitations, testing approach.

## 4. Decisions that most need your confirmation

Full register in `08_assumptions_and_risks.md`. The ones that could change the build:

1. **`FUL-2026-000001` meaning.** The problem statement lists it as an ID convention but never defines the entity. Plan interprets it as the **fulfillment record** (one per order × node; the allocation unit). Fulfillment *nodes* get `NODE-001` style keys. Format is config-driven, so reversing this is cheap. (A-01)
2. **100,000 tracking events vs. ~50,000 orders.** With ~1.1 shipments/order, 100k events is only ~2 events per shipment. Plan makes service-level-driven "tracking detail levels" and treats 100,000 as a calibrated **minimum** (reported exact count). (A-02)
3. **Geography.** Plan uses a synthetic region/zone model (no real carrier tariffs, no external data), so no licensing exposure. (A-05)
4. **Anomaly volume.** Default 100 rows per scenario (500 total), configurable. (A-12)

## 5. Next step

On approval, start at Milestone M0/M1 (`07_milestones_acceptance.md`). The build will be staged and each stage delivered as a zip.
