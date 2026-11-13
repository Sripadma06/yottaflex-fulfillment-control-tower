# AI Usage & Prompt History — scaffold (copy to `docs/ai/` in the repo)

Required by the YottaFlex submission guidelines: submit prompt history, and explain where AI accelerated the work, where it was relied on heavily, and what you personally reviewed, changed, or validated.

## `docs/ai/prompt_history/` convention
One file per tool/session, e.g. `2026-11-12_claude_planning.md`:

```
## Prompt 001 — 2026-11-12 14:50 IST — Claude (Sonnet 5.5)
<exact prompt text>
(Response optional; if the tool cannot export prompts, note the limitation here.)
```
Rule: log every prompt sent to any AI tool, including failed or discarded ones.

## `docs/ai/AI_USAGE.md` template

| Area | Tool | AI role | Reliance (low/med/high) | What I personally reviewed / changed / validated |
|---|---|---|---|---|
| Architecture & plan | | Drafted | | e.g. challenged FUL-ID interpretation, edited assumptions |
| Calendar/promise engine | | | | e.g. hand-computed 20 golden cases |
| Allocation engine | | | | |
| Data generator | | | | e.g. verified distributions vs config |
| Anomaly injector | | | | e.g. isolation diff test |
| Validator | | | | |
| Tests | | | | |
| Docs | | | | |

Also state: known limitations of AI-generated parts, bugs the AI introduced and how you found them, and parts you rewrote.
