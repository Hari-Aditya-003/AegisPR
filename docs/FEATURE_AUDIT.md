# Research-feature audit — October 23, 2026

This checks both user-supplied research lists against the source and verified tests. The lists are design suggestions, not evidence that AegisPR has run on real PRs. “Implemented” means code and local tests exist; the October 23 live Nemotron connectivity check does **not** imply a full PR run.

| Requested capability | Status and evidence limit |
| --- | --- |
| Compare labeled outputs rather than only assertion pass/fail | Implemented for generated `output` tests; missing/malformed observations are inconclusive. `backend/app/verification/differential.py`. |
| Inputs from old-code and new-code angles; 10 normal and 10 edge cases | After two truncated live plan responses, the budget-aware planner requests both angles in one compact test file with at most eight labeled examples. Actual model compliance, deduplication and coverage remain **unmeasured**; neither the original twenty-case request nor a 27–32-case Testora-equivalent result was demonstrated. See [October 24 attempt](live-pr-attempt-2026-10-24.md). |
| Intent review using PR title, description, commit messages, before/after output | Optional three-vote advisory review implemented. No PR comments are fetched; public-API legality and input validity are not independently proved. An “unintended” vote does not by itself become a confirmed regression or trigger repair. |
| Rerun behavioral differences to filter flaky output | Two additional executions on each commit implemented for output differences. Assertion-mode failure flakiness is not yet independently filtered. |
| Fix broken generated tests | Up to two budgeted, base-first refinements implemented after a failing base test. A static undefined-name precheck is not implemented. |
| Shrink a failing example | Not implemented. |
| Mutation-guided test quality | One Python changed-line comparison mutation per eligible test; catch rate shown for valid executions. JavaScript mutation and automatic strengthening of uncaught mutants are not implemented. |
| Validated JSON with one correction attempt | Implemented for malformed/invalid **plans**. The extra request is reserved against the persistent five-call and dollar limits; HTTP 402, transport failures and truncated responses are never retried. Other model stages do not yet have schema-correction retries. |
| Lightning / larger-model routing and measured savings | One configured model is used; no verified routing or comparative cost/quality data. |
| GPU code embeddings, function-level ranking, Nebius GPU hosting | Not implemented. Dell CuPy ranking is a real hashed-vector CUDA workload with dated evidence; it is not a code-embedding model or a Nebius GPU instance. |
| Coding-agent CLI and pre-push check | `aegispr verify` is implemented for committed local Git changes and machine-readable output. It has no MCP server. Opt-in hook instructions are in `docs/pre-push-verification.md`; no hook is installed automatically. |
| Performance regressions | Opt-in Docker base/head suite runner takes three repeated samples and screens time/cgroup peak memory. The real CLI path passed a controlled Docker fixture in [October 24 CI](https://github.com/Hari-Aditya-003/AegisPR/actions/runs/40040038098), but no real-PR performance claim or measured slowdown is available. |
| Property-based tests | The planner now conditionally asks for bounded Hypothesis/fast-check tests when those dependencies are declared. No live generated property tests or measured bug-finding result yet. |
| Security and API breaking changes | Token-free scanner flags selected removed auth/validation patterns and Python/simple named JS/TS public signatures. Heuristic review signals, not comprehensive detection or confirmed vulnerabilities. |
| CUDA/GPU kernel verification | Bounded `aegispr compare-gpu` compares caller-supplied numerical arrays and repeated latency on matching claimed CUDA devices. It does not run kernels or attest Nebius GPU execution; an automated Nebius GPU runner remains open. |
| Direct-import impact graph | Implemented for Python and relative JS/TS imports; no longer uses a filename-substring edge. Import-prioritized context selection, full call graph, batched Git reads and function chunks remain open. |
| Cached sandbox dependencies | Conservative Docker dependency layer for eligible root lockfiles/pinned requirements implemented; CI's controlled Docker build passed. Shared base/head images, parallel test runs, repair image reuse and a measured speedup remain open. |
| Repository clone reuse | Existing `git worktree` per commit is used. Cached bare mirror and repair workspace reuse are not implemented. |
| SQLite WAL | Implemented for run and budget ledgers. |
| Per-stage timing in proof card | Aggregate analysis/sandbox durations exist; detailed clone/rank/plan/build/execute/repair timing is not shown. |
| 10–20-case evaluation dataset | **12 synthetic, hand-labeled, executable code pairs** stored in `evals/seeded-prs/cases.json`; validation and local Git materialization are tested. This is fixture coverage, not a real-PR benchmark or model detection rate. |
| 10–20 real merged PR benchmark with bugs, false alarms, cost and time | Not run. Requires confirmed inference credits, selected public PRs, human labels and provider receipts. No results have been invented. |
| GitHub PR proof-card comment / Action | Not implemented. No third-party PR has been modified. |
| Tavily runtime API search | Not integrated or called. Submission answer remains “no.” |
| Judge-accessible full app and final demo video | Public browser fixture and private captioned draft exist, but neither proves a public full-app live PR run. Final URL/video remain open. |

The app-side ledger still admits at most **$20 estimated total, $0.25 estimated per run, and five provider attempts per run**, with zero SDK retries. The new correction request can consume one of those attempts; it does not bypass the cap. Token Factory completed the [October 23 model-only check](live-nebius-check.md) and two [October 24 real-PR attempts](live-pr-attempt-2026-10-24.md), but both PR planning responses were truncated before generating tests. No end-to-end acceptance, comparative quality, or benchmark metric has been measured. Read the [seeded dataset instructions](../evals/seeded-prs/README.md) and [research workflow](workflow-research-implementation.md) before quoting any performance number.
