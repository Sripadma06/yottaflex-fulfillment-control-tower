# 07 — Milestones & Acceptance Criteria

## 1. Development milestones

The challenge window is **72 hours** (artifact timestamps are used to verify it). The plan budgets ~48 h of build and keeps ~24 h as buffer for review, README, and reproducibility proof. Commit at each milestone (meaningful commit messages = "show your work").

| M | Deliverable | Exit criteria | Est. |
|---|---|---|---|
| **M0** Foundations | Repo, `pyproject`, tooling, CI, config models + YAML skeleton, logging, ID factory, RNG streams, `docs/ai/` + prompt-history habit | `make test` green; config validation tests; determinism test for RNG streams | 3 h |
| **M1** Schema | Schema-spec module, SQLAlchemy models, Alembic 0001–0005, generated data dictionary + ER doc | up/down/up migration test; data dictionary covers all 11 entities | 5 h |
| **M2** Reference data | Calendars/holidays, zones, carriers, services, nodes, SKUs, inventory, capacity generators | FK + enum validators pass on reference data; counts 20/10 | 5 h |
| **M3** Calendar & promise engine | Calendar engine, promise engine with trace, golden + property tests | Hand-computed golden cases pass; no business literals in code | 7 h |
| **M4** Allocation engine | ATP, single/split planner, scoring, capacity integration, decision log, exceptions | Unit tests: single, split, shortage, capacity roll; deterministic tie-break | 7 h |
| **M5** Orders & simulation | Arrival/basket generators, time-ordered simulation, ledger, status history | 50k orders end-to-end; baseline validator = 0 findings for implemented rules | 6 h |
| **M6** Outcomes & tracking | Delay model, tracking templates, re-promise, rollup | ≥ 100,000 events; tracking validators pass; rollup tests | 5 h |
| **M7** Anomalies & ground truth | Injector (5 scenarios), ground-truth writer, isolation test | 100 % detection; isolation diff == ground truth | 4 h |
| **M8** Validation & evaluation | Full rule catalogue, runner, evaluator, reports | `validation_summary` + `evaluation_report` generated | 5 h |
| **M9** Persistence & API | PG bulk loader (clean + with-anomalies), FastAPI endpoints, problem-details | Integration tests incl. quote/fulfill/track flow | 6 h |
| **M10** Hardening & submission | Repro check x2, README, assumptions, limitations, AI_USAGE, prompt history export, final clean-clone run | Fresh-clone run-through succeeds; public repo pushed; checklist §3 ticked | 5 h |

Critical path: M0 → M1 → M2 → M3 → M4 → M5 → M6 → M7 → M8 → M10 (M9 parallelisable after M5).
Descoping order if time-pressed (state in README, per FAQ #11): property tests → API metrics endpoint → PG `with-anomalies` mode → FULL tracking detail level. **Never descoped:** the five anomalies, ground truth, validator, reproducibility proof, prompt history.

## 2. Acceptance criteria mapped to the assignment

### 2.1 Business objective & workflow (problem statement)

| # | Statement requirement | Acceptance criterion | Evidence |
|---|---|---|---|
| A1 | Select nodes using inventory | Every FUL line satisfies qty ≤ ATP at allocation time (V-INV-01 = 0 findings on baseline) | validation_summary |
| A2 | …warehouse capacity | Σ per node/date ≤ capacity (V-CAP-01); capacity-rolled legs exist (> 0) and are traced | validator + evaluation_report |
| A3 | …carrier cutoffs | Promise legs re-derive correctly from cutoff + calendars (V-CAL-03); cutoff-miss legs exist and roll to next pickup day | validator + unit golden tests |
| A4 | …shipping service levels | Transit from service×zone table; unsupported combos never chosen on baseline (V-NET-01 = 0) | validator |
| A5 | Holiday/working-day calendars | No promise/ship/delivery on closed days (V-CAL-01/02 = 0); ≥ N holiday-crossing promises present | validator + coverage test |
| A6 | Single-node and split shipments | ≥ 5 % split orders; split orders have ≥ 2 FUL/SHP; N:M bridge populated | evaluation_report |
| A7 | Expose key decisions & exceptions | Decision log per order; exception records for shortage, capacity, delay; `GET /orders/{id}/trace` | API integration test |
| A8 | Preserve traceability | History tables append-only; promise versions retained; trace_json per leg | trigger tests, V-PROM-02 |
| A9 | Produce measurable outputs | Metrics in §06 2.2 generated | evaluation_report |
| A10 | Medium complexity: ≥ 1 exception path | Shortage, capacity overflow, carrier-delay/re-promise paths all exercised in data | exception counts > 0 |

### 2.2 Data requirements

| # | Requirement | Criterion | Evidence |
|---|---|---|---|
| D1 | Master data first; valid parent IDs | Generation order enforced; FK integrity = 100 % | V-FK-* |
| D2 | Volumes | 50,000 orders; 20 nodes; 10 carriers; ≥ 100,000 tracking events (exact count in manifest) | manifest.json |
| D3 | IDs | Match regex for all five conventions; immutable; referenced identically across files | V-PK-* |
| D4 | Fixed seed + parameterised scale | `--seed 20261022`; starter and full use the same code | CLI, tests |
| D5 | Valid baseline first | Baseline validator = 0 findings before injection | pipeline gate log |
| D6 | Five labelled edge cases | Exactly the five `issue_type`s, count per config, all detected | ground_truth + evaluation |
| D7 | Derived values computed | Totals, statuses, dates, capacity use re-derive exactly | V-ARITH-*, V-ROLL-* |
| D8 | Separate ground truth | `ground_truth.csv/json` separate; no label columns in feature tables; import-linter + schema test | tests |
| D9 | Validation coverage | PK, FK, enum, date-order, arithmetic, lifecycle, duplicate checks all present | rule catalogue |
| D10 | Exports | CSV, JSON, SQL seed, README, data dictionary, generator command, seed, source manifest, validation summary | file existence test |
| D11 | Reproducibility | Two runs ⇒ identical row counts + SHA-256 | reproducibility_report.md |
| D12 | Lawful provenance | All synthetic; manifest documents any reference | source_manifest.md |
| D13 | Realistic variation | Distribution report shows non-degenerate variation (delay, basket, load) | evaluation_report |

### 2.3 Engineering requirements (your brief)

| Requirement | Criterion |
|---|---|
| Modular architecture | Module map of `02_architecture.md` §4; import-linter passes |
| Clean code / type hints | `ruff`, `black`, `mypy --strict` pass on domain/services |
| Proper logging | JSON logging with run_id; stage summaries; logging tests |
| Deterministic, seed 20261022 | D4 + D11 |
| No scattered hardcoded business decisions | Literal gate passes; all rules in `config/` |
| Config-driven rules | Changing YAML changes behaviour (test flips a weight and asserts different node choice) |
| Error handling | Exception hierarchy + RFC 7807 tests; generator fails fast on bad config |
| Unit + integration tests | pytest suite; coverage ≥ 85 % (domain+services) |
| Stack | Python, FastAPI, PostgreSQL, SQLAlchemy, Alembic, Pydantic, pytest, Faker, NumPy all in use |

## 3. Submission checklist (YottaFlex guidelines & FAQ)

- [ ] New dedicated **public** GitHub repo; link sent from the recruitment email address; kept editable until deadline.
- [ ] Working executable code with README steps: install → configure → run → verify.
- [ ] Meaningful commits per milestone (evolution visible).
- [ ] `docs/ai/prompt_history/` contains **every** prompt to every AI tool (responses optional; disclose any export limitation).
- [ ] `docs/ai/AI_USAGE.md`: where AI accelerated, where relied on heavily, what I reviewed/changed/validated.
- [ ] Assumptions, key decisions/trade-offs, testing approach, limitations, deviations, next steps documented.
- [ ] No secrets/PII/proprietary code; `.env.example` only; no imported full solutions; licences/attribution for dependencies.
- [ ] Individual work: understand and be able to walk through the core logic (allocation, promise calc, anomaly injection, validator).
- [ ] Submitted within 72 h of the project send timestamp.
