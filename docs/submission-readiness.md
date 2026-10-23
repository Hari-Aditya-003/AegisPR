# Submission readiness and credit plan

Evidence update: October 23, 2026 (Asia/Kolkata); the rules audit below was performed October 18. This is an evidence audit, not a guarantee of eligibility, a prize, employment, or security against every attack. Official organizers make eligibility decisions. Do not turn unchecked items into claims in Devpost, the README, the site, or the recording.

## Required gates

The [official rules](https://nebiusglobalaihackathon.devpost.com/rules) require a functional application, at least one NVIDIA open model, and actual Nebius inference or AI Cloud execution. They also require public licensed source and setup guidance, an accessible demo/test build, English submission materials, a demonstration video under three minutes on publicly visible YouTube, and judging access through December 15. Submission closes October 30, 2026, at 22:30 IST. Adult eligibility, ownership, exclusions, and conflicts must be personally checked. Using every model is not required. City awards require attendance. The coding track describes writing/running/testing code in Token Factory; seek organizer confirmation that hosted reasoning plus local Docker execution qualifies for that track. Public/unlisted Vimeo wording in the form differs from the rules: use public YouTube or obtain written clarification. No tests can guarantee an award or eliminate all disqualification risks.

The [official FAQ](https://nebiusglobalaihackathon.devpost.com/details/faqs) confirms that the frontend and unrelated processing may be hosted elsewhere when NVIDIA inference uses Token Factory. Another inference provider does not replace this platform requirement. Billing and missing promotional credits are handled by Nebius case by case. A request to list models proves credential access, not completed model inference.

## Evidence ledger

| Area | Evidence checked | Current conclusion / next action |
| --- | --- | --- |
| Source and licensing | GitHub repository API reports `PUBLIC`, default branch `main`, license key `mit`; root `LICENSE` and README exist | Ready at audit time. Preserve dependency notices and verify rights to all submission assets. |
| Setup | README includes Compose, local development, environment configuration, Dell scripts and limitations | Re-run a fresh setup from the release commit before recording. |
| GPU workload | [October 19 recovery receipt](gpu-recovery-2026-10-19.md): matching driver `595.99.02`, CuPy arithmetic and authenticated RTX 3050 Ti ranking. October 23 [health check](live-nebius-check.md) found missing NVIDIA userspace libraries. | CUDA was real on October 19 but is **not currently verified healthy**. This is local compute, not a Nebius GPU instance or measured speedup. Restore and recheck before recording. |
| Sandbox | [Live stack evidence](live-stack-evidence.md) records baseline PASS, seeded change FAIL, manual repair PASS | Real Docker experiment verified. Generated-model test and repair are not proved by this controlled fixture. |
| Automated checks | Backend provider mocks, differential unit tests, UI/browser checks, CPU-worker tests and container contracts exist | These validate implementation paths; they do not establish real Nemotron quality, live CUDA on CI, or a successful cloud review. Use current test-run evidence rather than a permanently fixed test count. |
| Provider runtime | An October 23 [bounded model-only JSON completion](live-nebius-check.md) succeeded after credits were added. | Model connectivity is verified, but a generated PR plan, actual PR acceptance, quality evaluation and provider-charge reconciliation remain open. Protect the remaining credits. |
| Public website | [Landing page](https://hari-aditya-003.github.io/AegisPR/) and [fixture demo](https://hari-aditya-003.github.io/AegisPR/demo/) each returned HTTP 200 without credentials | Public access checked. A response status alone does not prove browser interaction; smoke-test it in a clean browser. |
| Public fixture | `website/dist/demo/boundary.mjs` and its tests run a deterministic JavaScript coupon comparison | Working teaching/test fixture; cannot accept arbitrary GitHub PRs, run Docker, or call Nemotron. Label the mode explicitly. |
| Full application | The separate [local judging build](judge-test-build.md) runs the real interface/API/Docker on fixed fixtures without credentials; October 23 production GPU health was degraded. | Reproducible controlled test build, not successful live Nemotron/PR verification. Production remains private owner access; never advertise Tailscale as a public link. |
| Recording | Submission kit still contains a video URL placeholder and live model stages not yet recorded | **Blocking:** record actual working behavior and verify the final URL, duration, and visibility. |
| Survey/disclosures | Submission form explicitly asks which AI tools helped during development | Answer accurately in that field. Product branding need not list development tools. Do not fabricate model ratings or a comparison. |

## Model choice with only $25

Current configuration defaults to `nvidia/Nemotron-3_5-Lightning` as an economical evaluation candidate, replacing Ultra. That is a cost choice, not evidence that it is the best model for this task. The [official Nemotron page](https://nebius.com/services/token-factory/models/nvidia-nemotron-models-inference) recommends starting with Lightning for efficient coding/reasoning and explicitly advises validating the application's own behavior. Its current public price cards show:

| Candidate | Input / output USD per million tokens | Proposed role, pending evaluation |
| --- | --- | --- |
| Nemotron 3.5 Lightning | $0.06 / $0.24 | First economical text/code candidate; official linked ID `nvidia/Nemotron-3_5-Lightning`. |
| Nemotron 3 Ultra | $1.00 / $3.00 | Existing integration; comparator for difficult hypotheses and repairs. |
| Nemotron 3 Nano | $0.06 / $0.24 | Alternative if schema compatibility or coding results favor it. |
| Nemotron 3.5 Super VL | $0.30 / $0.90 | Visual/document workloads; no demonstrated need for vision in this text-only PR flow. |

The authenticated catalog and [public machine-readable catalog](https://tokenfactory.nebius.com/api/public/models_info) were also checked without inference: plain `nvidia/nemotron-3-super-120b-a12b` is listed at $0.30/$0.90 per million input/output tokens. See [the exact model registry and budget policy](model-budget.md). Context windows and advertised benchmark scores do not establish AegisPR accuracy. No candidate was called for live quality evaluation by this audit.

For an illustrative 20,000-input/4,000-output-token request, the arithmetic cost is $0.00216 on Lightning/Nano, $0.00960 on Super VL, or $0.03200 on Ultra. These are estimates from the listed prices, not measurements, run limits, or predictions; multi-stage runs, reasoning tokens, retries, and larger prompts change the charge. The [official cost benchmark](https://dev.nebius.com/cookbook/agent-cost-benchmark) measures correctness, tokens, latency and cost together. Its example task is not AegisPR's evaluation set.

Recommended allocation, to be enforced by actual application controls before public inference:

| Reserve | Maximum planned amount |
| --- | ---: |
| Model selection and bounded live acceptance | $2 |
| Recording and a verified end-to-end example | $3 |
| Judge demonstrations and availability | $15 |
| Errors, retries and contingency | $5 |

Start with a sub-$0.50 comparison of Lightning and the existing Ultra configuration on the same fixed PR fixtures. Expand only when a measured failure justifies it. Evaluate valid structured output, executable generated test, correct base/head classification, confirmed repair, false positives, total usage, latency, and dollars per successful verification. Select the cheapest model that meets the acceptance criteria; use a more expensive model only for measured failures and record that escalation. Calling every catalog model would consume credit without proving product quality.

Implemented and unit-tested during hardening: persistent atomic spending reservations, $20 total/$0.25 per-run admission estimates, five provider attempts per run, stage-specific input/output limits, exact-response caching, zero SDK automatic retries, explicit HTTP 402 handling, private deployment authentication, and create/repair rate limiting. These are app-side estimates, not a provider account spending cap or verified balance. Resource/concurrency behavior still needs a load test before any public untrusted multi-user service. Do not expose the private key to static hosting. Reserve the judging allocation before comparisons.

## Completion evidence to capture

1. A successful real provider call with timestamp, endpoint, exact model ID, response ID where available, schema-validation result, and provider token usage. Redact credentials.
2. A controlled public PR with known base/head commits. Save the generated test, actual Docker commands, isolated execution logs, durations and exit codes for both commits. Model output must not decide the pass/fail result.
3. If offering repairs, save the generated patch and rerun the generated regression test plus applicable existing/build/lint checks. A manually restored fixture is a separate observation.
4. A no-regression control, an existing failure, an environment failure and an adversarial input. Show bounded conclusions and visible CPU fallback/provider errors.
5. A clean-browser judging journey on the final URL or reproducible test build, including its disclosed limits. Leave enough usable budget for the judging period.
6. A final recording and submission review: truthful measured model feedback; exact source/demo/video URLs; access instructions; completed applicant declarations; no placeholder fields; no API secrets in logs/screenshots.

Until these observations exist, describe Nemotron as configured/integrated with one successful bounded connectivity completion, not a completed PR review. Describe CUDA ranking as a dated October 19 observation and controlled Docker differential execution separately. Keep live results, recorded results and deterministic demo mode visually distinct for both human reviewers and automated evaluation.
