# Controlled PR verification and Nemotron Super trial — October 26, 2026

This is a dated, deliberately seeded acceptance run, **not** an independent real-world PR benchmark or a measured model accuracy rate. The public [fixture PR](https://github.com/Hari-Aditya-003/AegisPR-acceptance/pull/1) claims to preserve coupon behavior, while its head commit removes the nonnegative-total clamp. Its description also contains an automated summary that describes the removal as a bug fix, so the recorded intent is not perfectly unambiguous.

## Reproducible evidence

| Item | Recorded result |
| --- | --- |
| AegisPR run | `cd1828ed-05e1-4739-a019-3ee1a9772f65` |
| Model | Nebius Token Factory `nvidia/nemotron-3-super-120b-a12b` |
| Base / PR commits | `1bfad69ed176946d23068f68eee8cadfdd3e3361` / `4f89ac80cc3cb11a5c646d8cae0851e964a689e1` |
| Generated experiment | One assertionless Python usage example calling the changed `coupon.apply_coupon` with four inputs |
| Branch execution | Separate local Docker checkouts; both returned `PASSED` |
| Changed output | `(total=5, discount=10)` returned `0` on base and `-5` on PR; `(0, 5)` also changed from `0` to `-5` |
| Stability | Two confirmation reruns per side (four additional executions) agreed with the initial outputs |
| Intent review | Three fresh model votes: `unintended`, `unintended`, `unintended` — advisory only |
| Final product result | `BEHAVIOR_CHANGE` finding, overall `INCONCLUSIVE` pending a human decision about intended behavior |
| Usage | 4 provider calls, 2,683 input and 715 output tokens, **$0.001450 app-estimated** for this run; 61.974 seconds analysis and 53.561 seconds sandbox time |

The report does **not** label this a confirmed regression merely because a model voted three times. Both commits executed successfully; the measured fact is a stable output change. The code and PR description together make an unintended regression plausible, but a reviewer must resolve the conflicting intent text. The evidence record retains the generated test, exact commits, commands, stdout, exit codes, and confirmation executions. This is stronger than an unexecuted model opinion, but does not prove the absence of other defects.

The Dell's RTX GPU performed local CUDA context ranking. Token Factory hosted the Nemotron inference. The base/head tests ran in local Docker, **not** on a Nebius AI Cloud GPU or Token Factory Sandbox.

## Cost-controlled model observation

The earlier Lightning trials on this same seeded PR did not produce a usable fresh test: one correction was double-escaped and syntactically incomplete; another generated simulated old/new values and then an invalid correction. They stopped without a false regression claim. One subsequent cached replay sent **zero** new provider calls. The fresh Super run above produced a parseable changed-function test and stable branch evidence. Planner wording and validation also changed between these trials, so this is **not** a controlled head-to-head quality benchmark or proof that Super is the best model generally. [Nebius's model page](https://nebius.com/services/token-factory/models/nvidia-nemotron-models-inference) lists Super at $0.30/$0.90 per million input/output tokens versus Lightning at $0.06/$0.24; prices may change.

The persistent app ledger after this run held **24 provider calls and $0.007568 estimated lifetime cost**. This is an application admission estimate, not a provider invoice, remaining-credit balance, or hard account cap. The $20 total / $0.25 per-run / five-call limits and zero SDK automatic retries remained in place. No further paid attempts were needed for the video review. The running Dell backend was temporarily configured for Super for this trial; its saved `.env` still names Lightning, so a later Compose recreation without an explicit model override can revert it. Model selection should be made explicit before a longer evaluation.

## Private recordings and verification

Two local-only recordings were visually sampled at 1280×720; neither is a public submission video:

- `artifacts/demo/aegispr-real-time-pr-after-output-gate-2026-10-26.webm` — 94.64 seconds, real UI submission and live execution; SHA-256 `b0ca8f2733257e0fbfdebcaa4acb60f596dda9de3677072d427de94ee6518b48`.
- `artifacts/demo/aegispr-super-pr-evidence-review-2026-10-26.webm` — 34.12 seconds, read-only replay of the saved result after the frontend was updated to show intent votes and confirmation counts; SHA-256 `e88a0db2e9c5433dc03d6bf454846750126ea5f50ce3b29f7a7857ccb616cd48`.

The production frontend/backend/GPU worker were healthy after the frontend refresh. Local backend tests passed **243 checks at 88.96% coverage**. [CI run 40225985200](https://github.com/Hari-Aditya-003/AegisPR/actions/runs/40225985200) passed backend, frontend, security, GPU-worker fallback, CLI Docker acceptance, and judge-build jobs for commit `31e37bf`. CI does not replay this paid-model run or prove current GPU availability on arbitrary hosts.

Remaining submission work includes the entrant's own public YouTube video and a judge-accessible route to the full live application if claimed; the published browser demo remains a fixed, token-free example. The entrant should review final Devpost ratings and eligibility declarations personally.
