# October 18 hardening and acceptance evidence

This is a dated engineering receipt, not a security certification or a guarantee of eligibility, a prize, or employment. Live, mocked, historical, and illustrative results are kept separate.

## Automated checks

The complete local command `make test PYTEST=backend/.venv312/bin/pytest` passed on Python 3.12.11 and Node 25.9.0:

| Layer | Result | What this establishes |
| --- | --- | --- |
| Backend | 123 tests; 89.94% coverage | API gates/CORS, durable budget concurrency/accounting, bounded model requests/cache/errors, Git/patch/path rules, sandbox lifecycle/output bounds, orchestration and persistence. Provider responses are mocked. |
| Frontend | 28 tests; 95.42% statements, 88.81% branches | Private session access, honest evidence, retries, actual command rendering, configured-origin CSP, input and error handling. |
| Chromium | Seven E2E tests | Production UI journeys with intercepted backend responses, keyboard interaction, reduced motion, mobile layout and repair display. Not a live model run. |
| Public website | Eight Node tests | Coupon boundary arithmetic, invalid inputs, stale evidence invalidation and motion-control contract. |
| GPU worker | Six CPU-fallback tests | Authentication, ranking and result bounds. Not live CUDA proof. |
| Seeded repository | One test | Controlled baseline coupon behavior. |

Total: **173 automated tests**. TypeScript checking, production Next.js build, Python compilation, shell syntax, Compose validation and Git whitespace checks also passed. Starlette currently emits a test-client HTTPX deprecation warning; it did not fail the suite. Chromium is the only automated browser engine in this receipt.

The UI was also inspected at 320, 390, 700, 768, 1024 and 1440 CSS pixels with no horizontal overflow or runtime errors. Pausing animation keeps newly entered panels visible. Screenshots are local development artifacts, not live model evidence.

## Security and dependency checks

The audit reproduced and fixed symlinked generated-file writes, repository-controlled Dockerfile/patch paths, inherited Git subprocess secrets, noncanonical remote input, repair rename/copy/mode metadata scope bypass, and scope expansion through a model-suggested affected file. Additional regression checks cover timeouts and container/image cleanup, unbounded Docker output, runner-option paths, generated test targeting and stale UI evidence.

Docker build/run output is limited to 1 MiB combined, with a bounded retained tail. Runtime uses a read-only root, no network/host binds, UID 10001, dropped capabilities and bounded memory/CPU/processes. A 512 MiB ephemeral executable worktree supports native Node test dependencies; `/tmp` remains noexec. Setup/output-limit/missing-command failures are executor errors, not reproduced regressions. Projects with `.dockerignore` or unsupported generated runners are skipped rather than falsely verified.

The resolved fresh Python backend environment and resolved package freezes from both deployed backend and worker images reported **no known vulnerabilities** in pip-audit. npm audit reported zero frontend vulnerabilities. Previously flagged Python packages were updated or removed; the unused GitPython dependency was removed. These checks do not scan OS packages or prove an absence of undiscovered vulnerabilities. The final source review found no new critical/high blockers within the trusted-operator MVP boundary; [remaining executor risks](security.md#remaining-boundaries) remain explicit.

## Credits and authentication

The app now checks persistent atomic admission estimates before paid requests: $20 total, $0.25 per run including repairs, five attempts per run, bounded context/output, exact-request caching and zero SDK automatic retries. This is not a provider billing cap or a verified account balance. See [model-budget.md](model-budget.md).

No paid inference requests were sent during this pass. Deployed `/api/budget` reported zero calls, tokens and estimated dollars in the new ledger; this does not establish past provider spending. An unauthenticated request returned 401; authenticated budget access returned 200 without exposing credentials. The live browser now shows the private-access guidance rather than a CSP connection failure. The production API requires a separate random deployment access code; the provider key stays server-side.

## Dell deployment and current GPU blocker

All three images built and services were restored. The backend uses host port 8080; the frontend uses 3000, and the worker remains loopback-only on 8091. Unrelated services on the Dell were preserved.

Recreating the GPU container exposed a **host** failure:

```text
Host nvidia-smi: Failed to initialize NVML: Driver/library version mismatch
Loaded NVIDIA kernel module: 595.91.07
Installed NVML library:       595.99.02
```

No reboot, driver rollback or module unload was performed. The app was restored using the explicit `docker-compose.cpu.yml` override and health now truthfully returns:

```json
{"status":"degraded","checks":{"nebius":"configured","gpu_worker":"ok","gpu_accelerator":"cpu","sandbox":"enabled"}}
```

An administrator must arrange safe host recovery after saving other work. Once host `nvidia-smi` succeeds, restore normal Compose, rerun authenticated CUDA ranking and capture new evidence. The October 17 CUDA record is historical, not current GPU readiness.

## Real sandbox acceptance

`scripts/sandbox-acceptance.py` executes fixed Python and Node fixtures directly through Docker, with no model requests. The Python observation is base PASS, seeded head FAIL, and manually restored existing/generated checks PASS; build/lint are unconfigured and SKIPPED. This is not a model-generated test or repair.

Live Node acceptance exposed two additional issues hidden by subprocess mocks: npm 10.9.9 crashed resolving the tiny Vitest dependency tree, and Docker's tmpfs defaulted to noexec. The trusted npm 12.2.0 installer is now pinned before loading repository files, and the isolated worktree explicitly supports execution. Re-running the real Node/Vitest fixture produced base PASS, seeded head FAIL, and manually repaired existing/generated/build checks PASS; lint was unconfigured and SKIPPED. Both language fixtures passed without model requests. These tiny fixtures do not establish arbitrary repository/framework compatibility.

## Unfinished submission gates

1. Restore current CUDA execution after host driver recovery.
2. Resolve usable Nebius credits; the last actual completion returned HTTP 402. Catalog access alone is not inference proof.
3. Capture a successful bounded real Nemotron call and an actual public PR base/head/repair run; measure model quality rather than inventing a rating.
4. Provide reliable judge access to the full application or reproducible full test build. GitHub Pages hosts a clearly labeled deterministic browser fixture, not a public model/GPU service.
5. Record the actual working application, verify the final video URL and organizer requirements, and complete truthful personal eligibility/disclosure fields.

MIT licensing and setup documentation are present, but the gates above mean the project is **not yet submission-complete**. The five-hour continuation remains active with credit protection and no automatic host reboot.
