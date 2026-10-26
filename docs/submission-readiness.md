# Submission readiness and credit plan

Evidence update: October 26, 2026 (Asia/Kolkata); the rules audit below was performed October 18. This is an evidence audit, not a guarantee of eligibility, a prize, employment, or security against every attack. Official organizers make eligibility decisions. Do not turn unchecked items into claims in Devpost, the README, the site, or the recording. The owner selected **Best Apps and Agents** and personally confirmed the age, residence, ownership and conflict declarations October 24; that personal confirmation is not independent organizer approval. The owner will make the final YouTube video themselves.

## Required gates

The [official rules](https://nebiusglobalaihackathon.devpost.com/rules) require a functional application, at least one NVIDIA open model, and actual Nebius inference or AI Cloud execution. They also require public licensed source and setup guidance, an accessible demo/test build, English submission materials, a demonstration video under three minutes on publicly visible YouTube, and judging access through December 15. Submission closes October 30, 2026, at 22:30 IST. The owner selected Best Apps and Agents because the coding track describes writing/running/testing code in Token Factory Sandboxes while AegisPR uses local Docker. Using every model is not required. City awards require actual attendance; do not select a nearby city merely for proximity. Public/unlisted Vimeo wording in the form differs from the rules: use public YouTube or obtain written clarification. No tests can guarantee an award or eliminate all disqualification risks.

The [official FAQ](https://nebiusglobalaihackathon.devpost.com/details/faqs) confirms that the frontend and unrelated processing may be hosted elsewhere when NVIDIA inference uses Token Factory. Another inference provider does not replace this platform requirement. Billing and missing promotional credits are handled by Nebius case by case. A request to list models proves credential access, not completed model inference.

## Evidence ledger

| Area | Evidence checked | Current conclusion / next action |
| --- | --- | --- |
| Source and licensing | GitHub repository API reports `PUBLIC`, default branch `main`, license key `mit`; root `LICENSE` and README exist | Ready at audit time. Preserve dependency notices and verify rights to all submission assets. |
| Setup | README includes Compose, local development, environment configuration, Dell scripts and limitations | Re-run a fresh setup from the release commit before recording. |
| GPU workload | October 23 [health check](live-nebius-check.md) found missing NVIDIA userspace libraries. The [October 24 recovery receipt](gpu-recovery-2026-10-24.md) confirms matching `595.99.02` packages, host `nvidia-smi`, in-container CuPy and authenticated RTX 3050 Ti ranking. | CUDA is verified for the dated October 24 check. This is local compute, not a Nebius GPU instance or measured speedup; recheck before recording. |
| Sandbox | [Live stack evidence](live-stack-evidence.md) records baseline PASS, seeded change FAIL, manual repair PASS | Real Docker experiment verified. Generated-model test and repair are not proved by this controlled fixture. |
| Automated checks | Backend provider mocks, differential unit tests, UI/browser checks, CPU-worker tests and container contracts exist | These validate implementation paths; they do not establish real Nemotron quality, live CUDA on CI, or a successful cloud review. Use current test-run evidence rather than a permanently fixed test count. |
| Provider runtime | An October 23 [bounded model-only completion](live-nebius-check.md) succeeded. The [October 25 continuation](live-pr-continuation-2026-10-25.md) reused a Lightning test plan. The [October 26 run](live-pr-super-comparison-2026-10-26.md) generated a fresh Super-model test on the controlled public PR. | Super generated one executable changed-function example; separate Docker runs and four confirmations recorded a stable output change. Three fresh votes called it `unintended`, but the final product status was `INCONCLUSIVE` because intent remains a human decision. The run was $0.001450 app-estimated and the persistent ledger $0.007568 app-estimated, not a provider invoice. There is no independent real-PR benchmark or comparative model accuracy rate. |
| Public website | [Landing page](https://hari-aditya-003.github.io/AegisPR/), [fixture demo](https://hari-aditya-003.github.io/AegisPR/demo/) and [read-only controlled PR evidence viewer](https://hari-aditya-003.github.io/AegisPR/evidence/) | Local browser checks covered desktop/mobile evidence-page rendering. Recheck all three published URLs after the release workflow; the evidence page is not a live API. |
| Public fixture | `website/dist/demo/boundary.mjs` and its tests run a deterministic JavaScript coupon comparison | Working teaching/test fixture; cannot accept arbitrary GitHub PRs, run Docker, or call Nemotron. Label the mode explicitly. |
| Full application | The separate [local judging build](judge-test-build.md) runs the real interface/API/Docker on fixed fixtures without provider credentials; the [October 26 run](live-pr-super-comparison-2026-10-26.md) completed a fresh generated-test controlled public-PR behavior comparison and three live intent votes on the private Dell deployment. | Reproducible controlled local test build and dated private full-app evidence, not a public unrestricted live service. Production remains private owner access; never advertise Tailscale as a public link. |
| Recording | A [94.64-second real-time controlled-PR take and 34.12-second read-only evidence walkthrough](live-pr-super-comparison-2026-10-26.md) were saved and visually sampled in the private workspace. The submission kit still has no final public video URL. | **Owner-owned blocking item:** the owner will create/upload the final YouTube video; verify its URL, duration, visibility and factual claims before submission. Do not upload footage automatically. |
| Survey/disclosures | Submission form explicitly asks which AI tools helped during development | Answer accurately in that field. Product branding need not list development tools. Do not fabricate model ratings or a comparison. |

## Model choice with only $25

The repository defaults to `nvidia/Nemotron-3_5-Lightning` as an economical evaluation candidate, replacing Ultra. The October 26 private Dell container was temporarily configured to use `nvidia/nemotron-3-super-120b-a12b` for a single controlled trial. The saved `.env` still names Lightning, so a later Compose recreation without an explicit override can revert it. This one-case observation is not evidence that either model is universally best. The [official Nemotron page](https://nebius.com/services/token-factory/models/nvidia-nemotron-models-inference) recommends starting with Lightning for efficient coding/reasoning and explicitly advises validating the application's own behavior. Its current public price cards show:

| Candidate | Input / output USD per million tokens | Proposed role, pending evaluation |
| --- | --- | --- |
| Nemotron 3.5 Lightning | $0.06 / $0.24 | First economical text/code candidate; official linked ID `nvidia/Nemotron-3_5-Lightning`. |
| Nemotron 3 Super | $0.30 / $0.90 | One dated controlled-PR trial produced executable branch evidence; exact ID `nvidia/nemotron-3-super-120b-a12b`. |
| Nemotron 3 Ultra | $1.00 / $3.00 | Existing integration; comparator for difficult hypotheses and repairs. |
| Nemotron 3 Nano | $0.06 / $0.24 | Alternative if schema compatibility or coding results favor it. |
| Nemotron 3.5 Super VL | $0.30 / $0.90 | Visual/document workloads; no demonstrated need for vision in this text-only PR flow. |

The authenticated catalog and [public machine-readable catalog](https://tokenfactory.nebius.com/api/public/models_info) list the plain Super ID above. See [the exact model registry and budget policy](model-budget.md). Context windows and advertised benchmark scores do not establish AegisPR accuracy. The dated Super trial is one seeded case, not a statistical quality comparison.

For an illustrative 20,000-input/4,000-output-token request, the arithmetic cost is $0.00216 on Lightning/Nano, $0.00960 on Super VL, or $0.03200 on Ultra. These are estimates from the listed prices, not measurements, run limits, or predictions; multi-stage runs, reasoning tokens, retries, and larger prompts change the charge. The [official cost benchmark](https://dev.nebius.com/cookbook/agent-cost-benchmark) measures correctness, tokens, latency and cost together. Its example task is not AegisPR's evaluation set.

Recommended allocation, to be enforced by actual application controls before public inference:

| Reserve | Maximum planned amount |
| --- | ---: |
| Model selection and bounded live acceptance | $2 |
| Recording and a verified end-to-end example | $3 |
| Judge demonstrations and availability | $15 |
| Errors, retries and contingency | $5 |

The owner authorized a limited $1–$2 quality investigation; the October 26 Super run cost $0.001450 app-estimated, well below that ceiling. Any further paid evaluation should use predeclared fixed PR cases and record valid output, executable test, correct base/head classification, false alarms, total usage, latency and dollars per successful verification. Select the cheapest candidate meeting the criteria. A different prompt and validator were used for the Super trial, so do not turn this observation into an accuracy ranking. Calling every catalog model would consume credits without proving product quality.

Implemented and unit-tested during hardening: persistent atomic spending reservations, $20 total/$0.25 per-run admission estimates, five provider attempts per run, stage-specific input/output limits, exact-response caching, zero SDK automatic retries, explicit HTTP 402 handling, private deployment authentication, and create/repair rate limiting. These are app-side estimates, not a provider account spending cap or verified balance. Resource/concurrency behavior still needs a load test before any public untrusted multi-user service. Do not expose the private key to static hosting. Reserve the judging allocation before comparisons.

## Completion evidence to capture

1. A successful real provider call with timestamp, endpoint, exact model ID, response ID where available, schema-validation result, and provider token usage. Redact credentials.
2. A controlled public PR with known base/head commits. Save the generated test, actual Docker commands, isolated execution logs, durations and exit codes for both commits. Model output must not decide the pass/fail result.
3. If offering repairs, save the generated patch and rerun the generated regression test plus applicable existing/build/lint checks. A manually restored fixture is a separate observation.
4. A no-regression control, an existing failure, an environment failure and an adversarial input. Show bounded conclusions and visible CPU fallback/provider errors.
5. A clean-browser judging journey on the final URL or reproducible test build, including its disclosed limits. Leave enough usable budget for the judging period.
6. A final recording and submission review: truthful measured model feedback; exact source/demo/video URLs; access instructions; completed applicant declarations; no placeholder fields; no API secrets in logs/screenshots.

Until the remaining gates are met, describe Nemotron as integrated with bounded live controlled-PR test generation and execution. Distinguish the October 25 **zero-new-call replay** and saved-plan intent review from the October 26 **fresh Super-generated test** and four-call run. Both reached stable `BEHAVIOR_CHANGE` and `INCONCLUSIVE` overall status. Neither is a confirmed regression or independent real-PR benchmark. Keep live results, cached replay, manual replay and deterministic browser mode visually distinct for human and automated evaluation.
