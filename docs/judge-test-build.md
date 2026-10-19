# Credential-free local judging build

This build runs the real Next.js interface, FastAPI evidence API, SQLite persistence and Docker executor on fixed Python and Node coupon fixtures. It needs no provider account, paid tokens or NVIDIA GPU. It is separate from the [public browser experiment](https://hari-aditya-003.github.io/AegisPR/demo/) and from live PR verification.

**Scope:** the hypothesis, boundary test and manual repair are prewritten. The build creates actual local Git commits, executes checks through Docker, and saves actual commands, logs, exit codes and durations. It does not call Nemotron, analyze a live GitHub PR, rank context on CUDA or generate an AI repair. The report prominently labels this provenance. A successful fixture does not prove general correctness, security, model quality or hackathon eligibility.

The [October 19 acceptance receipt](judge-build-evidence-2026-10-19.md) records successful real Python and Node Docker runs on the Dell, separately from mocked unit/browser tests.

## Requirements and start

- Linux, Git, Bash, OpenSSL and a running Docker Engine with Docker Compose. The acceptance target is the Linux Dell; Docker Desktop compatibility is not yet independently verified.
- Permission to use the Docker socket. This is a trusted-operator build: socket access is host-equivalent authority, not a safe public multi-user execution boundary.
- Internet access for container images and pinned test dependencies, plus free loopback ports `3300` and `18080`. It does not require an API key or `.env` file.

```bash
git clone https://github.com/Hari-Aditya-003/AegisPR.git
cd AegisPR
bash scripts/judge-test-build.sh start
```

The command builds only the judge backend/frontend, waits for their health checks and executes both fixtures. It prints one report URL per language, for example `http://127.0.0.1:3300/verifications/<run-id>`. A nonzero command exit means setup or a required acceptance check failed; do not treat that run as verified.

Open a printed URL. Expand **Private deployment access** and save the locally generated code from `artifacts/judge/access-code`. This file is permission-restricted and ignored by Git. It is a local application session code, not a provider key. Never publish it, put it in a URL or include it in screenshots/artifacts. Saving the code retries evidence loading. The frontend uses `http://127.0.0.1:18080` for its authenticated API.

## Inspect the evidence

Each report should show:

1. **Controlled fixture — not a live pull request review** and zero model calls.
2. The full, real local base/head commit IDs.
3. The same boundary test passing on base and failing on the intentionally broken head.
4. A prewritten manual repair and separate existing-test/generated-test results; Node also requires its configured build. Unconfigured checks are skipped, not claimed as passing.
5. `FIX_VERIFIED` only when every required repair check passes. Expand branch and repair evidence to read the exact executed commands and captured output. No model-repair action is offered for fixture reports.

```bash
bash scripts/judge-test-build.sh status
bash scripts/judge-test-build.sh verify   # new Python and Node receipts
bash scripts/judge-test-build.sh export   # only receipt JSON files
bash scripts/judge-test-build.sh stop
```

`export` copies only `/app/data/judge-evidence/*.json` into `artifacts/judge/evidence/`, not the access code or private database. Inspect JSON before sharing. `stop` removes only the `aegispr-judge` services/network and preserves the judge data volume and private code. Restarting preserves earlier records. No volume deletion or global Docker prune is needed.

## Isolation and spending

The standalone `docker-compose.judge.yml` must not be merged with production Compose. It uses project `aegispr-judge`, its own data volume, separate loopback ports and explicitly empty provider/GitHub credentials. The launcher removes inherited production credentials from its child environment. Its persistent inference admission budget is zero. No GPU worker or production `.env` is passed into these containers. The production app retains its separate $20 / $0.25 / five-attempt protections.

Repository checks use the production sandbox policy: no runtime network or host bind mounts, unprivileged UID, dropped capabilities, read-only root and bounded resources/output. Image builds still need dependency-download network access. See [security boundaries](security.md#remaining-boundaries).

## Troubleshooting and CI

- Docker unavailable: start your Docker Engine; do not automatically install/reconfigure unrelated host services.
- Socket permission denied: confirm the operator's Docker access and socket group. The launcher detects the socket GID for the backend container; do not make the socket world-writable.
- Port occupied: stop your own conflicting test service or use a separate host. Never stop unrelated services automatically.
- Missing dependencies, timeout or image-build failure: inspect the terminal output and execution receipts; these are environment errors, not a confirmed regression.
- Remote machine: forward both loopback ports through an authenticated SSH connection. A private Tailscale hostname is not a public judge URL. Do not expose this Docker-socket-backed API as an arbitrary-code service.

The CI `judge-test-build` job runs this launcher on Linux and uploads the exported `controlled-fixture-evidence` JSON artifact. Unit tests mock subprocesses and cannot replace this real Docker acceptance job. A source checkout and these instructions make the controlled test build reproducible; they do not satisfy the still-unverified live NVIDIA/Nebius inference requirement.

After starting the stack and exporting evidence, run the separate four-check browser suite:

```bash
cd frontend
npm ci
npx playwright install --with-deps chromium
npm run e2e:judge
```

It reads the actual exported Python/Node records, checks API authentication and zero recorded inference usage, loads their real UI reports without API mocks and inspects full execution receipts at desktop/mobile widths. It uses only the fixed local ports above, not production endpoints. Traces, video and screenshots are disabled for this authenticated suite. CI uploads only receipt JSON, not private session state or browser failure diagnostics; keep local failure artifacts private too. The normal seven mocked-API journeys remain under `npm run e2e`.
