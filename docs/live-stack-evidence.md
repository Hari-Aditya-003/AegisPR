# Dell deployment and sandbox evidence

Current-state note (October 18): this page records the prior healthy CUDA milestone. The hardened stack is now running with explicit CPU fallback because of a host NVIDIA kernel/NVML mismatch. Backend health reports `degraded` and `gpu_accelerator: cpu`; historical CUDA results below are not current live GPU readiness. See [current hardening evidence](hardening-evidence.md).

Verified October 17, 2026, approximately 21:02 IST.

## Running deployment

The frontend, backend, and CUDA worker are running and Docker reports all three
healthy. The frontend was rebuilt with the actual browser-facing backend URL.
The backend uses host port 8080 because an unrelated application occupies 8000.
Container-to-container requests still use port 8000.

The application is reachable from the owner's Tailscale network at:

- Frontend: `http://hari-dell-g15-5510.tail8849b3.ts.net:3000/`
- Backend: `http://hari-dell-g15-5510.tail8849b3.ts.net:8080/health`

These are private-network URLs, not public judging links.

The live backend response was:

```json
{"status":"ok","checks":{"nebius":"configured","gpu_worker":"ok","sandbox":"enabled"}}
```

`nebius: configured` only means a credential is present. It does not validate
inference, credit balance, or end-to-end model behavior.

A Chromium smoke check against the deployed frontend observed the expected
page title, heading, and pull-request input, with no browser runtime errors.

## Backend production-image fix

Live verification found both Git and the Docker CLI missing from the original
backend image. The repository operations and sandbox executor require them.
The new `scripts/backend-smoke-test.sh` failed with `git: not found` before the
fix. The rebuilt image passed the same smoke test as the non-root application
user:

```text
git version 2.47.3
client=28.5.1 server=29.1.3
```

The image now installs Git and copies the Docker CLI from `docker:28.5.1-cli`.
The existing Docker group configuration permits the backend to reach the host
daemon. Sandbox containers do not inherit the daemon socket.

## Live sandbox experiment

The actual `DockerSandbox.execute` implementation was invoked inside the
deployed backend. Three temporary copies of the repository's demo-store fixture
were used. A manually supplied boundary test asserted that applying a discount
of 20 to a cart total of 10 produces zero.

| Fixture | Result | Exit code | Observed test output | Duration |
| --- | --- | --- | --- | --- |
| Baseline, clamped total | PASSED | 0 | 2 passed | 8044 ms |
| Seeded change, clamp removed | FAILED | 1 | 1 failed, 1 passed; actual total -10 | 7047 ms |
| Repaired fixture, clamp restored | PASSED | 0 | 2 passed | 7241 ms |

Each recorded environment reported Docker execution, no runtime network, and
`privileged: false`. The executor used its normal read-only filesystem, memory,
CPU, PID, capability, and no-new-privileges restrictions. Temporary test images
and workspaces were removed after execution.

This proves real sandbox execution and differential behavior. It is a controlled
local fixture experiment with a manually supplied test and repaired source, not
a model-generated test, a real public PR run, or a `FIX_VERIFIED` model repair.

## Automated validation

The complete `make test` matrix passed again after the deployment work:

- Backend: 42 tests; 86.74% coverage.
- Frontend: 17 tests; 96.8% statement coverage; type check and build passed.
- GPU worker: 6 tests.
- Demo repository: 1 test.
- Browser workflows: 3 tests.
- npm audit: zero reported vulnerabilities.

Total: 69 tests, plus the live image, deployed-browser, and sandbox checks above.

## Nebius status and remaining requirements

The key authenticates to `/v1/models`, and the catalog includes the exact,
case-sensitive ID `nvidia/Nemotron-3-Ultra-550b-a55b`. The server environment
and Compose default now use that ID. A small chat completion returned:

```text
HTTP 402
Payment Required: You have exhausted your budget. Please add funds to continue using the API.
```

A support request has been sent asking Nebius to fix billing availability and
enable hackathon credits without a payment card. No additional paid inference
requests are necessary until the credit state changes.

Remaining release gates are a successful live model request, a real public-PR
workflow with evidence and repair verification, a public judging-accessible
application, public website sharing, and the final demonstration video. The
hackathon submission must distinguish the verified local CUDA/sandbox work from
the still-blocked Nebius inference path.
