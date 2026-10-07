# AegisPR

Don't trust a PR. Prove it.

AegisPR is an autonomous evidence-backed pull request verification agent powered by NVIDIA Nemotron on Nebius Token Factory. It analyzes a code change, names concrete risks, generates targeted adversarial tests, executes the same test against the base and pull request commits, and reports whether the change introduced a reproducible regression.

Project website: [aegispr.mr-adityahari.chatgpt.site](https://aegispr.mr-adityahari.chatgpt.site) (owner-private until sharing is enabled).

## Why AegisPR

AI review usually returns an opinion. AegisPR turns a claim into an experiment:

```text
CLAIM → HYPOTHESIS → TEST → BASE + PR EXECUTION → EVIDENCE → CONCLUSION
```

The core result matrix is deterministic:

| Base | Pull request | Classification |
| --- | --- | --- |
| Pass | Fail | Regression introduced by the PR |
| Fail | Fail | Pre-existing failure or invalid test |
| Pass | Pass | No failure reproduced |
| Fail | Pass | Possible improvement |

## Features

- Public GitHub pull request ingestion and commit discovery
- Repository, framework, package manager, and test-command detection
- Change impact graph and dependency-neighborhood context selection
- NVIDIA Nemotron risk hypotheses through Nebius Token Factory
- CUDA-accelerated context ranking on the Dell RTX GPU worker
- Framework-native adversarial test generation
- Isolated Docker execution with no runtime network, dropped capabilities, process limits, CPU and memory limits
- Base-versus-PR differential verification
- Evidence records containing commits, commands, logs, exit codes, and durations
- Live verification timeline, findings, proof card, and bounded status language
- Persistent local run history and API/SSE access

## Architecture

```text
Browser / Next.js
        │
        ▼
FastAPI orchestrator ─── GitHub API + git
        │
        ├── Nebius Token Factory ── NVIDIA Nemotron 3 Ultra
        │
        ├── Dell RTX 3050 Ti ───── CUDA context ranking
        │
        └── Docker sandboxes ───── Base + PR test execution
                         │
                         ▼
                 Evidence report
```

Nemotron 3 Ultra is served remotely because it is a 550B-class mixture-of-experts model. The Dell RTX 3050 Ti performs a real, bounded CUDA workload: hashed term-document vector construction, cosine scoring, and context prioritization. If the worker is unavailable, AegisPR records a CPU fallback rather than hiding the loss of acceleration.

See [architecture](docs/architecture.md), [agent stages](docs/agents.md), [verification semantics](docs/verification.md), and [security model](docs/security.md).

## Quick start

Requirements:

- Docker 29+ with Compose
- NVIDIA driver and NVIDIA Container Toolkit on the GPU host
- Nebius Token Factory API key
- Optional GitHub token for higher public API rate limits

```bash
cp .env.example .env
# Add NEBIUS_API_KEY and replace GPU_WORKER_TOKEN.
docker compose up --build -d
docker compose ps
curl http://localhost:8000/health
```

Open `http://localhost:3000`, paste a public GitHub pull request URL, and select **Verify PR**.

The default model is `nvidia/nemotron-3-ultra-550b-a55b` through the OpenAI-compatible Nebius endpoint at `https://api.tokenfactory.nebius.com/v1/`. Always confirm the model is available to the API key by querying `/v1/models` before a demo.

## Dell GPU deployment

The included deployment script targets the existing Tailscale SSH alias `dell-ts` and `/home/hari/aegispr`:

```bash
chmod +x scripts/*.sh
./scripts/gpu-smoke-test.sh
./scripts/deploy-dell.sh
```

The `.env` file must already exist at `/home/hari/aegispr/.env` on the Dell host. The script never copies local secrets.

Verify the worker:

```bash
ssh dell-ts 'cd /home/hari/aegispr && docker compose exec gpu-worker python3 -c "import cupy as cp; print(cp.cuda.runtime.getDeviceProperties(0)[\"name\"]); print(cp.arange(1000000).sum())"'
```

## Local development

Backend:

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm ci
npm run dev
```

Tests:

```bash
make test
```

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/verifications` | Start verification for a public pull request URL |
| `GET` | `/api/verifications/{id}` | Read complete run state |
| `GET` | `/api/verifications/{id}/events` | Stream run updates with SSE |
| `GET` | `/api/verifications/{id}/findings` | Read differential findings |
| `GET` | `/api/verifications/{id}/impact` | Read impact nodes and edges |
| `GET` | `/health` | Inspect Nebius, GPU worker, and sandbox configuration |

## Environment variables

| Name | Required | Description |
| --- | --- | --- |
| `NEBIUS_API_KEY` | Production | Server-side Token Factory key |
| `NEBIUS_BASE_URL` | No | OpenAI-compatible endpoint |
| `NEBIUS_MODEL` | No | NVIDIA model ID |
| `GITHUB_TOKEN` | No | Higher GitHub API rate limits |
| `GPU_WORKER_TOKEN` | Production | Shared token for the internal GPU worker |
| `PUBLIC_API_URL` | Production | Browser-visible FastAPI URL used at frontend build time |
| `ALLOWED_ORIGINS` | Production | Exact comma-separated frontend origins |
| `DOCKER_GID` | Dell host | Group ID allowed to access the Docker socket |

## Verification statuses

- `VERIFIED_WITHIN_SCOPE`: selected checks passed.
- `REGRESSION_FOUND`: at least one generated test passed on base and failed on the PR.
- `FIX_VERIFIED`: a proposed repair passed the selected existing and generated checks.
- `PRE_EXISTING_FAILURE`: the failure occurred on both commits.
- `INCONCLUSIVE`: evidence was insufficient.
- `ENVIRONMENT_ERROR`: the repository could not be executed correctly.
- `ANALYSIS_ONLY`: reasoning completed but runtime verification did not.

## Security disclaimer

A successful AegisPR verification does not prove that software contains no defects or security vulnerabilities. It reports the evidence produced by the specific analyses and tests executed during that verification run.

## Hackathon fit

AegisPR uses NVIDIA Nemotron for repository reasoning, risk planning, test generation, and evidence synthesis through Nebius Token Factory. It uses the Dell NVIDIA GPU for accelerated repository context ranking and isolated compute telemetry. These are core workflow components, not decorative integrations.

## License

[MIT License](LICENSE)
