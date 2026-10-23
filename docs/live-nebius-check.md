# October 23, 2026 — bounded live Nebius check

This is a narrowly scoped **model connectivity check**, not a full AegisPR PR verification, NVIDIA GPU ranking run, benchmark, or final hackathon submission. The account UI showed active billing and a $29.50 balance before the check; the figures below come from AegisPR's separate app-side budget ledger, not a provider invoice.

The production backend on the Dell used its configured `nvidia/Nemotron-3_5-Lightning` model through the existing `NebiusGateway`. The request was an innocuous JSON connectivity prompt. No credential value was printed or placed in the video. `NebiusGateway` retained zero SDK automatic retries and the persistent **$20 estimated lifetime / $0.25 per-run / five-attempt** admission limits.

| Observation | Result |
| --- | --- |
| Initial 96-token output cap | HTTP response contained 37 input and 96 output tokens, but the model hit the output cap before completing valid JSON. AegisPR raised `InferenceUnavailable`; this was not a connectivity or billing rejection. |
| Final 512-token output cap | Valid JSON returned with `status: ready` from `nvidia/Nemotron-3_5-Lightning`. |
| Combined app ledger | Two calls, 74 input tokens, 388 output tokens, **$0.000099 estimated** total. |
| Provider billing | Not independently reconciled; the app estimate is not a provider-enforced spending cap or exact charge. |
| Screen recording | Private, Git-ignored `artifacts/demo/live-nebius-credit-check-retry-2026-10-23.webm`; 17.76 seconds, VP8, 1280×720. See [recording notes](demo-recording.md). |

The same-day local checks passed: 206 backend tests with 90.05% coverage, 33 frontend tests with 95.54% statement coverage, eight recorder safety tests, TypeScript checking and production build, six GPU-worker unit tests, one demo-store test, seven browser E2E tests, 16 website tests, and an npm audit with zero reported vulnerabilities. The umbrella `make test` command stopped at `npm audit` because the restricted shell could not resolve npm's advisory endpoint; that audit was run separately with network access and passed, then the remaining test targets passed. Unit tests of the GPU worker do **not** prove a working GPU on the Dell.

At this check, the Dell production `/health` was **degraded**: the GPU worker could not start because the host NVIDIA userspace library `libnvidia-ml.so.1` and `nvidia-smi` were missing, although the 595.99.02 kernel module was loaded. This supersedes the dated October 19 CUDA-ready observation. No driver, reboot, or unrelated service change was attempted. The live model check therefore does not establish the GPU portion of AegisPR. A real PR acceptance run, judge-accessible full application, and final supported video URL remain open.
