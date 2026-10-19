# Contributing to AegisPR

## Development prerequisites

- Git
- Python 3.12
- Node.js 22 and npm
- Docker with Compose
- Chromium dependencies for Playwright
- NVIDIA driver and Container Toolkit only for physical CUDA validation

## Setup

```bash
git clone https://github.com/Hari-Aditya-003/AegisPR.git
cd AegisPR
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
cd frontend && npm ci && cd ..
```

Copy `.env.example` to `.env` only when running Compose. Never commit the resulting file.

For a separate fixed-fixture acceptance build that cannot spend provider tokens, follow the [credential-free judging instructions](judge-test-build.md). It uses its own Compose project, data volume and loopback ports, and must not receive the production `.env`.

## Commands

<!-- AUTO-GENERATED: derived from Makefile and frontend/package.json -->

| Command | Description |
| --- | --- |
| `make test` | Run the complete local quality matrix. |
| `make test-backend` | Run backend pytest tests. |
| `make test-frontend` | Run frontend coverage, typecheck, build, and audit. |
| `make test-e2e` | Run Playwright journeys. |
| `make test-gpu` | Run GPU-worker tests with CPU fallback. |
| `make test-demo` | Run the demo repository test. |
| `make build` | Build all Compose images. |
| `make up` | Start the stack. |
| `make down` | Stop the stack. |
| `make gpu-check` | Verify CuPy sees the NVIDIA device in the worker. |
| `cd frontend && npm run dev` | Start frontend development mode. |
| `cd frontend && npm run typecheck` | Run TypeScript validation. |

<!-- END AUTO-GENERATED -->

## Test expectations

- Add or update tests for every behavioral change.
- Keep deterministic comparison logic free of model-dependent assertions.
- Mock GitHub, Nebius, Docker, and GPU boundaries in unit tests.
- Add a Playwright journey when user-visible behavior changes.
- Preserve explicit tests for negative paths: invalid URLs, unsafe commands, path traversal, provider failure, timeouts, and skipped checks.
- Run `make test` before opening a pull request.

## Code and security conventions

- Treat repository content and model output as untrusted.
- Do not pass model-generated shell text directly to a shell.
- Keep provider credentials server-side.
- Bound logs, diffs, source context, and model output.
- Use typed schemas at every external boundary.
- Preserve evidence-bounded language such as `VERIFIED_WITHIN_SCOPE`.
- Never replace the deterministic result matrix with model confidence.
- Keep repair patches isolated until executable checks pass.

## Pull request checklist

- [ ] The change has a focused purpose.
- [ ] New behavior has tests.
- [ ] `make test` passes.
- [ ] No secret, `.env`, token, private key, or credential is committed.
- [ ] Security boundaries remain explicit.
- [ ] Documentation matches changed routes, environment variables, scripts, or statuses.
- [ ] User-facing claims remain within observed evidence.

