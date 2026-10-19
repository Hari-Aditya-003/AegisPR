# AegisPR Complete Project Documentation

**Project:** AegisPR  
**Version:** 0.1.0  
**Tagline:** Don't trust a PR. Prove it.  
**Track:** Coding and Agentic Engineering  
**Repository:** <https://github.com/Hari-Aditya-003/AegisPR>  
**Project website:** <https://hari-aditya-003.github.io/AegisPR/>
**License:** MIT

## Table of contents

1. [Executive summary](#1-executive-summary)
2. [Problem and product thesis](#2-problem-and-product-thesis)
3. [Implemented capabilities](#3-implemented-capabilities)
4. [System architecture](#4-system-architecture)
5. [End-to-end verification workflow](#5-end-to-end-verification-workflow)
6. [Agent stages](#6-agent-stages)
7. [Differential verification semantics](#7-differential-verification-semantics)
8. [Repair verification](#8-repair-verification)
9. [NVIDIA GPU integration](#9-nvidia-gpu-integration)
10. [Nebius and Nemotron integration](#10-nebius-and-nemotron-integration)
11. [Repository intelligence and supported projects](#11-repository-intelligence-and-supported-projects)
12. [Sandbox and security model](#12-sandbox-and-security-model)
13. [Data model and persistence](#13-data-model-and-persistence)
14. [API reference](#14-api-reference)
15. [Frontend experience](#15-frontend-experience)
16. [Configuration reference](#16-configuration-reference)
17. [Local setup](#17-local-setup)
18. [Dell GPU deployment](#18-dell-gpu-deployment)
19. [Testing and quality assurance](#19-testing-and-quality-assurance)
20. [CI/CD](#20-cicd)
21. [Operations and troubleshooting](#21-operations-and-troubleshooting)
22. [Hackathon demonstration](#22-hackathon-demonstration)
23. [Current project status](#23-current-project-status)
24. [Limitations and roadmap](#24-limitations-and-roadmap)
25. [Related documentation](#25-related-documentation)

## 1. Executive summary

AegisPR is an autonomous, evidence-backed pull request verification system. It accepts a public GitHub pull request URL, inspects the exact base and head commits, identifies affected code, asks NVIDIA Nemotron on Nebius Token Factory for testable risk hypotheses and framework-native adversarial tests, and executes the same generated test against both revisions in isolated Docker sandboxes.

The comparison is deterministic. If a generated test passes on the base commit and fails on the pull request commit, AegisPR records a reproducible regression. The model does not decide whether the test passed. Process exit codes, execution status, logs, and commit identities determine the classification.

For a confirmed regression, AegisPR can ask Nemotron for a minimal unified diff, apply it only in an ephemeral checkout, and re-run the existing tests, generated regression test, build, and lint checks. A repair receives `FIX_VERIFIED` only when all required and configured executable checks pass.

## 2. Problem and product thesis

Traditional review tools provide one or more of the following:

- human opinions;
- static analysis findings;
- existing test results;
- probabilistic AI suggestions;
- CI status for checks that developers already wrote.

These mechanisms are useful, but they may miss new edge cases introduced by a change. AegisPR adds an experimental verification layer:

```text
CLAIM
  ↓
HYPOTHESIS
  ↓
GENERATED TEST
  ↓
BASE EXECUTION + PULL REQUEST EXECUTION
  ↓
OBSERVED DIFFERENCE
  ↓
EVIDENCE-BOUNDED CONCLUSION
  ↓
OPTIONAL REPAIR + RE-VERIFICATION
```

The core technical thesis is:

> LLM reasoning becomes more useful for software engineering when its hypotheses are converted into executable experiments whose results can be independently observed.

## 3. Implemented capabilities

- Canonical public GitHub pull request URL validation.
- GitHub metadata, base commit, head commit, and clone URL discovery.
- Exact commit fetch and detached worktree creation.
- Python, JavaScript, TypeScript, Next.js, npm, pytest, Vitest, Jest, and Mocha profile detection.
- Bounded diff, changed-file, context-document, and reference-based impact analysis.
- CUDA-accelerated hashed-vector context ranking with an explicit CPU fallback.
- NVIDIA Nemotron structured hypothesis and test generation through Nebius Token Factory.
- Safe generated-test path and command validation.
- Base-versus-head Docker execution with resource and network restrictions.
- Deterministic result classification.
- Persistent verification records in SQLite.
- Live run state, findings, hypotheses, metrics, and proof-card UI.
- Structured minimal repair generation.
- Repair patch size, binary-content, scope, traversal, and `git apply --check` validation.
- Isolated repair verification across existing tests, generated tests, build, and lint.
- REST and Server-Sent Events interfaces.
- Automated backend, frontend, E2E, GPU-worker, demo-repository, dependency, and secret checks.

## 4. System architecture

```text
┌──────────────────────────────┐
│ Browser / Next.js frontend   │
│ PR input, timeline, evidence │
└──────────────┬───────────────┘
               │ HTTP / JSON
               ▼
┌────────────────────────────────────────────────────────────┐
│ FastAPI orchestrator                                       │
│ URL validation · GitHub · Git · profiles · state · SQLite │
└─────────┬──────────────────┬─────────────────────┬──────────┘
          │                  │                     │
          ▼                  ▼                     ▼
┌─────────────────┐  ┌──────────────────┐  ┌─────────────────┐
│ Nebius Token    │  │ Dell GPU worker  │  │ Docker daemon   │
│ Factory         │  │ RTX 3050 Ti      │  │ isolated builds │
│ NVIDIA Nemotron │  │ CuPy / CUDA      │  │ and test runs   │
└─────────────────┘  └──────────────────┘  └─────────────────┘
          │                  │                     │
          └──────────────────┴─────────────────────┘
                             ▼
                 Evidence-backed run record
```

### 4.1 Frontend

The Next.js application accepts a PR URL, starts a verification, polls run state, and renders:

- run status;
- agent-stage timeline;
- findings and base/head comparison;
- likely root cause when available;
- risk hypotheses;
- repair action and repair evidence;
- metrics, proof card, and scope disclaimer.

Provider credentials never enter browser code.

### 4.2 FastAPI orchestrator

The backend owns every privileged operation:

- GitHub API requests;
- repository cloning and inspection;
- prompt construction;
- Nebius model calls;
- GPU worker calls;
- Docker sandbox policy;
- differential classification;
- repair validation;
- SQLite persistence.

The named agents are bounded stages in one orchestrated process. They are not separate independently privileged services.

### 4.3 GPU worker

The internal FastAPI worker exposes `/health` and authenticated `/rank`. It selects CuPy/CUDA when a device is available and NumPy/CPU otherwise. The backend records the returned accelerator.

### 4.4 Execution sandboxes

The backend builds a distinct container image for each generated test and commit. Dependency installation occurs at image-build time. The actual test command runs without network access and with a read-only root filesystem, limited memory, limited CPU, a process limit, dropped capabilities, and `no-new-privileges`.

## 5. End-to-end verification workflow

1. The user submits `https://github.com/{owner}/{repository}/pull/{number}`.
2. The backend rejects noncanonical, credential-bearing, non-HTTPS, wrong-host, port-bearing, or malformed URLs.
3. The GitHub API supplies public PR metadata and exact base/head SHAs.
4. Git clones the repository without checkout and fetches both commits.
5. A repository profile detects languages, package manager, framework, install command, test command, build command, and lint command.
6. A bounded diff and changed-file list are produced.
7. Candidate source documents are collected and ranked on the Dell CUDA worker when available.
8. A reference-based impact graph connects changed files to potentially affected files.
9. Nemotron returns strict JSON containing up to two hypotheses and one generated test per hypothesis; duplicate, unsafe, orphaned, or oversized plans are rejected.
10. AegisPR validates each generated path and command against repository-derived policy.
11. The generated test is written into a detached base checkout and executed in Docker.
12. The identical generated test is written into a detached head checkout and executed in Docker.
13. A pure comparison function classifies the observed status pair.
14. For regressions, a second bounded Nemotron call may summarize a likely root cause.
15. The complete run is stored and displayed with a scope disclaimer.
16. A confirmed regression may enter the optional repair-verification flow.

## 6. Agent stages

| Key | Display label | Responsibility |
| --- | --- | --- |
| `ingest` | Repository loaded | Validate the PR, fetch metadata, clone, and fetch commits. |
| `analyze` | Pull request analyzed | Detect repository profile, changed files, diff, and context candidates. |
| `impact` | Impact graph generated | Rank context and explain changed/related files. |
| `hypotheses` | Risk hypotheses generated | Ask Nemotron for testable change risks. |
| `tests` | Adversarial tests generated | Record the generated framework-native experiments. |
| `base` | Base branch executed | Execute each generated test against the base SHA. |
| `head` | Pull request branch executed | Execute the same test against the head SHA. |
| `compare` | Differential results compared | Apply the deterministic result matrix. |
| `report` | Evidence report completed | Persist and expose auditable evidence. |
| `repair` | Minimal repair generated | Generate and validate a scoped unified diff. |
| `repair_verify` | Repair checks executed | Run required and configured checks in the repaired checkout. |

Stage states are `pending`, `active`, `complete`, or `error`.

## 7. Differential verification semantics

### 7.1 Execution statuses

- `PASSED`: command exited with code 0.
- `FAILED`: command ran and exited nonzero.
- `ERROR`: the environment or image build failed.
- `TIMEOUT`: the configured execution deadline was exceeded.
- `SKIPPED`: the test, command, path, or runtime did not satisfy execution policy.

### 7.2 Result matrix

| Base | Pull request | Classification | Meaning |
| --- | --- | --- | --- |
| Pass | Fail | `REGRESSION` | The PR reproducibly introduced the observed failure. |
| Fail | Fail | `PRE_EXISTING_FAILURE` | The failure already existed or the generated test is invalid. |
| Pass | Pass | `NO_FAILURE_REPRODUCED` | The selected experiment did not reproduce a failure. |
| Fail | Pass | `POSSIBLE_IMPROVEMENT` | The PR may improve the tested behavior. |
| Any error, timeout, or skip | Any | `INCONCLUSIVE` | Evidence is insufficient for a behavioral conclusion. |

### 7.3 Run statuses

| Status | Meaning |
| --- | --- |
| `QUEUED` | The run was accepted but has not started. |
| `RUNNING` | One or more stages are active. |
| `VERIFIED_WITHIN_SCOPE` | Selected executable checks passed; no broader safety claim is made. |
| `REGRESSION_FOUND` | At least one test passed on base and failed on head. |
| `FIX_VERIFIED` | A proposed repair passed required and configured checks. |
| `PRE_EXISTING_FAILURE` | Observed failures occurred on both commits. |
| `INCONCLUSIVE` | Outcomes cannot support a strong classification. |
| `ENVIRONMENT_ERROR` | GitHub, Git, build, install, or execution infrastructure failed. |
| `ANALYSIS_ONLY` | Reasoning completed without executable generated tests or an enabled sandbox. |

Every successful report retains this boundary: verification applies only to the analyses and tests executed during that run.

## 8. Repair verification

Repair requests are accepted only when:

- the run status is `REGRESSION_FOUND`;
- sandbox execution is enabled;
- Nebius credentials are configured;
- the target finding is a differential regression.

### 8.1 Repair generation

Nemotron receives bounded regression evidence, the PR diff, affected source, and optional user instructions. It must return strict JSON containing:

- a concise summary;
- a git unified diff beginning with `diff --git`.

### 8.2 Patch safety policy

AegisPR rejects patches that:

- exceed 50,000 characters;
- contain NUL bytes;
- contain a Git binary patch;
- do not contain valid `a/` and `b/` file headers;
- use absolute paths, traversal, backslashes, `.git`, or `.aegispr` paths;
- modify files outside the PR's changed-file set and affected-file scope;
- fail `git apply --check`.

The patch is applied only to an ephemeral detached checkout. It is never pushed to GitHub and never changes the user's source repository.

### 8.3 Repair checks

Checks are stored separately:

1. `existing_tests` — the repository-detected test command before inserting the generated regression test;
2. `generated_tests` — the same test command after inserting the generated test;
3. `build` — the detected build command when configured;
4. `lint` — the detected lint command when configured.

`FIX_VERIFIED` requires both existing and generated tests to pass, plus every configured build or lint command. A failed, skipped, timed-out, or errored required check leaves the run at `REGRESSION_FOUND` and records the repair as failed.

## 9. NVIDIA GPU integration

The Dell Linux system is intended to provide an NVIDIA GeForce RTX 3050 Ti through Docker and the NVIDIA Container Toolkit.

### 9.1 Workload

The GPU worker performs a real deterministic compute task:

1. tokenize the query, source content, and paths;
2. hash tokens with BLAKE2b into 4,096-dimensional float vectors;
3. stack repository document vectors into a matrix;
4. compute vector norms and cosine similarity;
5. add a deterministic changed-file bonus;
6. sort and return the bounded context set.

CuPy performs matrix and vector operations when CUDA is available. Device data is copied back only for final scores.

### 9.2 Transparent fallback

If CuPy import, device discovery, or the worker request fails, the system uses NumPy or the backend's deterministic CPU ranker. The run records `context_accelerator` as `cuda` or `cpu`; it does not hide fallback behavior.

### 9.3 Worker endpoints

- `GET /health` returns status, accelerator, device, and workload.
- `POST /rank` accepts a query, at most 200 documents, and a result limit from 1 to 100.
- `/rank` uses constant-time bearer-token comparison when `GPU_WORKER_TOKEN` is configured.

The Compose stack binds the worker to `127.0.0.1:8091` on the host and accesses it internally as `http://gpu-worker:8091`.

## 10. Nebius and Nemotron integration

The backend uses the OpenAI Python client against:

```text
https://api.tokenfactory.nebius.com/v1/
```

The default model is:

```text
nvidia/Nemotron-3_5-Lightning
```

The configured model must be confirmed against `/v1/models` before a live demonstration. Lightning is a lower-cost evaluation candidate, not a measured quality winner. Ultra is an explicit alternative, not an automatic escalation. No successful live inference or measured model comparison is claimed while credits return HTTP 402.

### 10.1 Model calls

- **Verification planning:** repository profile, bounded PR diff, optional focus, and excerpts from at most eight ranked context documents produce strict JSON hypotheses and tests.
- **Root-cause analysis:** bounded logs and finding evidence produce one uncertainty-aware root-cause string.
- **Repair generation:** regression evidence, bounded source, PR diff, and optional instructions produce a minimal unified diff and summary.

### 10.2 Prompt-injection boundary

Every model prompt states that repository content, diffs, evidence, and user-provided fields are untrusted data rather than instructions. Model output is parsed into typed schemas and validated again before it can reach Git or Docker.

### 10.3 Missing credentials

Without a Nebius key, planning returns an explicit heuristic hypothesis with no executable generated test. The run therefore remains analysis-only instead of presenting heuristic output as verified model evidence. Repair generation is unavailable without credentials.

### 10.4 Credit protection

Persistent atomic admission estimates default to $20 total, $0.25 per verification including repairs, and five provider attempts per verification. Requests have bounded UTF-8 input, stage-specific output limits, no SDK automatic retries, and exact-response caching. Provider usage and conservative uncertain reservations are recorded in `inference-budget.sqlite3`. An optional explanation error does not erase independently executed regression evidence. These controls are app-side estimates, not provider balance or a guaranteed billing cap. See [model and credit policy](model-budget.md).

## 11. Repository intelligence and supported projects

### 11.1 Detected JavaScript/TypeScript projects

- `package.json` identifies npm projects.
- `package-lock.json` selects `npm ci`; otherwise installation uses `npm install --ignore-scripts`.
- Next.js is detected from dependencies.
- Vitest, Jest, and Mocha are detected from dependencies.
- Test, build, and lint commands are derived only from declared package scripts.

### 11.2 Detected Python projects

- `pyproject.toml` or `requirements.txt` identifies a Python project.
- `requirements.txt` selects `pip install -r requirements.txt`; otherwise installation uses `pip install .`.
- The default test command is `pytest -q`.

### 11.3 Current MVP boundaries

- Public GitHub repositories only.
- Python, JavaScript, and TypeScript runtime profiles.
- One execution per generated test and branch; no automatic flake repetition yet.
- Diff input is capped at 120,000 characters by default.
- At most 100 changed files and 100 context candidates are considered by default.
- Source documents are capped at 20,000 characters each.

## 12. Sandbox and security model

Repository code, PR text, generated tests, model output, logs, and repair proposals are untrusted.

### 12.1 URL and GitHub controls

- HTTPS only.
- Exact `github.com` hostname.
- No embedded username or password.
- No explicit port.
- Exact `/owner/repository/pull/number` shape.
- Public base repository required.
- Git terminal prompting is disabled.
- Git subprocess errors are bounded before storage.

### 12.2 Generated-test controls

- The model-provided command must exactly equal the repository-detected test command.
- Command prefixes are limited to npm tests/scripts, Vitest, Jest, pytest, or `python -m pytest`.
- Shell separators, pipes, substitutions, redirects, and line breaks are rejected.
- Generated paths must be repository-relative test/spec files with approved source extensions.
- Existing files cannot be overwritten by generated tests.

### 12.3 Container controls

- `--network=none` during test execution;
- read-only root filesystem;
- temporary `/tmp` with `noexec` and `nosuid`;
- configurable memory and CPU limits;
- process limit of 256;
- all Linux capabilities dropped;
- `no-new-privileges`;
- non-root UID 10001 inside generated execution images;
- unique image tags and image removal after execution.

### 12.4 API and browser controls

- Verification creation rate limit: 5 per minute per remote address.
- Repair creation rate limit: 2 per minute per remote address.
- Exact CORS allowlist; credentials disabled.
- Backend sets `nosniff`, frame denial, and no-referrer headers.
- Frontend adds CSP, permissions policy, frame denial, and other security headers.
- FastAPI interactive docs are disabled in production.

### 12.5 Secret controls

- Nebius, GitHub, and worker tokens are server-side environment variables.
- `.env` is excluded from Git and deployment synchronization.
- Secrets are not included in prompts, sandbox environments, frontend bundles, or API responses.
- CI rejects obvious committed token assignments and audits npm dependencies.

### 12.6 Docker socket warning

The backend mounts `/var/run/docker.sock` so it can create execution sandboxes. Access to the Docker socket is effectively host-level privilege. The socket is available only to the trusted orchestrator container, never to repository test containers. A production-scale design should replace this boundary with a remote ephemeral executor or managed sandbox service.

## 13. Data model and persistence

SQLite stores each complete `VerificationRun` as JSON in `verification_runs`.

### 13.1 Main record

A run contains:

- run ID, PR URL, status, start and completion timestamps;
- model name and PR summary;
- repository profile;
- stage timeline;
- changed files and impact graph;
- hypotheses and generated tests;
- findings and repair result;
- metrics, error, and disclaimer.

### 13.2 Finding evidence

Every finding links:

- hypothesis ID;
- generated test ID;
- deterministic classification;
- severity and summary;
- affected file and optional root-cause detail;
- base execution;
- head execution.

Each execution stores branch role, commit SHA, status, exit code, bounded stdout/stderr, duration, and environment metadata.

### 13.3 Storage behavior

- Writes use an upsert keyed by run ID.
- SQLite parameters are bound rather than interpolated.
- Reads and writes are protected by a re-entrant process lock.
- List results are ordered by the latest update timestamp.
- Compose persists `/app/data/aegispr.sqlite3` in the `aegis-data` volume.

## 14. API reference

Base development URL: `http://localhost:8000`

### 14.1 Health

```http
GET /health
```

Example:

```json
{
  "status": "ok",
  "checks": {
    "nebius": "configured",
    "gpu_worker": "ok",
    "sandbox": "enabled"
  }
}
```

`status` becomes `degraded` when Nebius is unconfigured or a configured GPU worker is unhealthy.

### 14.2 Create verification

```http
POST /api/verifications
Content-Type: application/json

{
  "pull_request_url": "https://github.com/owner/repository/pull/42",
  "focus": "Optional review focus, maximum 500 characters",
  "test_command": null
}
```

Returns `202 Accepted` and the queued run. Invalid PR URLs return `422`.

`test_command` is reserved in the request schema; the current orchestrator does not use it to override execution. Commands are always derived from the repository profile and checked against the sandbox allowlist.

### 14.3 List verifications

```http
GET /api/verifications?limit=20
```

The limit is clamped from 1 to 100.

### 14.4 Read verification

```http
GET /api/verifications/{run_id}
```

Returns the complete run or `404`.

### 14.5 Stream run events

```http
GET /api/verifications/{run_id}/events
Accept: text/event-stream
```

The server emits `verification` events whenever the serialized run changes, checks once per second, and stops at a terminal status or after 360 iterations.

### 14.6 Read findings

```http
GET /api/verifications/{run_id}/findings
```

### 14.7 Read impact graph

```http
GET /api/verifications/{run_id}/impact
```

Returns:

```json
{
  "nodes": [],
  "edges": []
}
```

### 14.8 Generate and verify repair

```http
POST /api/verifications/{run_id}/repair
Content-Type: application/json

{
  "finding_id": "finding-uuid",
  "instructions": "Optional bounded repair instruction"
}
```

Returns `202` when accepted, `404` for an unknown run, or `409` when the run is not eligible.

## 15. Frontend experience

### 15.1 Landing page

- explains evidence-backed verification;
- validates a canonical GitHub PR URL in the browser;
- submits to the FastAPI backend;
- navigates to `/verifications/{id}`.

### 15.2 Verification page

The page polls every 1.5 seconds until a terminal run status and displays:

- repository and PR identity;
- status badge;
- agent timeline;
- finding classifications and base/head outcomes;
- root-cause detail;
- risk hypotheses;
- proof-card metrics;
- repair controls for confirmed regressions;
- repair checks and isolated patch;
- environment errors and scope disclaimer.

### 15.3 Project website

The separate static project website explains the six-stage story:

1. map the change;
2. form hypotheses;
3. generate tests;
4. execute twice;
5. publish evidence;
6. repair and re-prove.

The project website and deterministic browser test build are published on GitHub Pages. The browser build at `/AegisPR/demo/` executes a coupon boundary fixture locally; it does not call Nebius, analyze arbitrary pull requests, or run GPU workloads. The full stack runs separately on the Dell.

## 16. Configuration reference

<!-- AUTO-GENERATED: environment variables derived from .env.example, docker-compose.yml, and backend/app/config.py -->

| Variable | Required | Default/example | Purpose |
| --- | --- | --- | --- |
| `NEBIUS_API_KEY` | Production | none | Server-side Token Factory credential. |
| `NEBIUS_BASE_URL` | No | `https://api.tokenfactory.nebius.com/v1/` | OpenAI-compatible API base URL. |
| `NEBIUS_MODEL` | No | `nvidia/Nemotron-3_5-Lightning` | Economical candidate pending a measured quality comparison. |
| `API_ACCESS_TOKEN` | Production | unique random secret, at least 16 characters | Private deployment code; required Bearer authentication on all `/api/*` routes. |
| `INFERENCE_BUDGET_USD` | No | `20` | Persistent total app-side admission estimate in USD. |
| `INFERENCE_RUN_BUDGET_USD` | No | `0.25` | Per-verification estimate including repairs. |
| `INFERENCE_MAX_CALLS_PER_RUN` | No | `5` | Provider-attempt cap including rejected attempts. |
| `BACKEND_PORT` | No | `8000`; current Dell uses `8080` | Host-published Compose backend port; update `PUBLIC_API_URL` and rebuild the frontend when changed. |
| `GITHUB_TOKEN` | No | empty | Raises GitHub public API rate limits. |
| `GPU_WORKER_TOKEN` | Production | random secret | Internal bearer token shared by backend and worker. |
| `PUBLIC_API_URL` | Production | Dell/Tailscale backend URL | Browser-visible backend URL embedded at frontend build time. |
| `ALLOWED_ORIGINS` | Production | `http://localhost:3000` | Exact comma-separated frontend origins. |
| `DOCKER_GID` | Dell host | `999` | Docker group ID added to the backend container. |
| `APP_ENV` | No | `development`; Compose uses `production` | Disables FastAPI docs in production. |
| `API_HOST` | No | `0.0.0.0` | Backend bind host setting. |
| `API_PORT` | No | `8000` | Backend port setting. |
| `GPU_WORKER_URL` | No | unset; Compose uses `http://gpu-worker:8091` | Internal ranking service URL. |
| `ENABLE_SANDBOX` | Required for execution | `false`; Compose uses `true` | Enables Docker differential and repair execution. |
| `SANDBOX_TIMEOUT_SECONDS` | No | `300` | Build/run timeout for a sandbox operation. |
| `SANDBOX_MEMORY` | No | `2g` | Docker memory limit for test runs. |
| `SANDBOX_CPUS` | No | `2.0` | Docker CPU limit for test runs. |
| `MAX_CHANGED_FILES` | No | `100` | Maximum changed files included in analysis. |
| `MAX_DIFF_CHARACTERS` | No | `120000` | Maximum PR diff characters passed onward. |
| `WORKSPACE_ROOT` | No | `/tmp/aegispr-runs` | Temporary clone and checkout root. |
| `DATA_PATH` | No | `data/aegispr.sqlite3` | SQLite database path. |
| `AEGIS_REMOTE_HOST` | Deployment only | `dell-ts` | SSH target used by deployment scripts. |
| `AEGIS_REMOTE_PATH` | Deployment only | `/home/hari/aegispr` | Remote application directory. |

<!-- END AUTO-GENERATED -->

Generate a worker token with a password manager or a cryptographically secure command. Never reuse an API key as the worker token.

## 17. Local setup

### 17.1 Prerequisites

- Git;
- Docker 29 or newer with Compose;
- Node.js 22 for direct frontend development;
- Python 3.12 for direct backend development;
- NVIDIA driver and Container Toolkit only when exercising CUDA locally;
- Nebius Token Factory API key for real model planning and repair.

### 17.2 Full Compose stack

```bash
git clone https://github.com/Hari-Aditya-003/AegisPR.git
cd AegisPR
cp .env.example .env
# Set NEBIUS_API_KEY and replace GPU_WORKER_TOKEN.
docker compose up --build -d
docker compose ps
curl http://localhost:8000/health
```

Open `http://localhost:3000`.

### 17.3 Backend development

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload
```

Without `ENABLE_SANDBOX=true`, local backend runs are analysis-only.

### 17.4 Frontend development

```bash
cd frontend
npm ci
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

### 17.5 GPU worker development

CPU fallback tests do not require CUDA:

```bash
PYTHONPATH=gpu-worker backend/.venv/bin/pytest -q gpu-worker/tests
```

The production worker image uses the CUDA 12.8.1 development image and `cupy-cuda12x`. CuPy JIT compilation needs the CUDA headers, and its compiled-kernel cache is directed to the writable `/tmp` tmpfs so the container root filesystem can remain read-only.

## 18. Dell GPU deployment

### 18.1 Host requirements

- Linux on the Dell system;
- working Tailscale connectivity and SSH alias `dell-ts` or `AEGIS_REMOTE_HOST` override;
- NVIDIA driver compatible with CUDA 12.8 containers;
- NVIDIA Container Toolkit;
- Docker Compose;
- `/home/hari/aegispr/.env` populated on the host.

The deployment script deliberately excludes `.env`; credentials must already exist on the server.

### 18.2 GPU smoke test

```bash
chmod +x scripts/*.sh
./scripts/gpu-smoke-test.sh
```

This runs `nvidia-smi` inside `nvidia/cuda:12.8.1-base-ubuntu24.04` with `--gpus all`.

### 18.3 Deploy

```bash
./scripts/deploy-dell.sh
```

The script:

1. synchronizes source with `rsync --delete` while excluding Git data, `.env`, dependencies, virtual environments, and builds;
2. runs `docker compose build` remotely;
3. runs `docker compose up -d`;
4. prints `docker compose ps`.

### 18.4 Post-deployment verification

```bash
ssh dell-ts 'cd /home/hari/aegispr && docker compose ps'
ssh dell-ts 'curl -fsS http://127.0.0.1:8000/health'
ssh dell-ts 'curl -fsS http://127.0.0.1:8091/health'
ssh dell-ts 'cd /home/hari/aegispr && docker compose exec gpu-worker python3 -c "import cupy as cp; print(cp.cuda.runtime.getDeviceProperties(0)[\"name\"]); print(cp.arange(1000000).sum())"'
```

The worker health response must show `"accelerator": "cuda"` before presenting the live GPU claim.

## 19. Testing and quality assurance

<!-- AUTO-GENERATED: commands derived from Makefile and frontend/package.json -->

| Command | Purpose |
| --- | --- |
| `make test` | Run backend, frontend coverage/type/build/audit, GPU-worker, demo-repository, and E2E suites. |
| `make test-backend` | Run backend pytest suite. |
| `make test-frontend` | Run frontend coverage, TypeScript checks, production build, and npm audit. |
| `make test-e2e` | Run the Playwright browser suite. |
| `make test-gpu` | Run GPU-worker API and ranking tests with CPU fallback. |
| `make test-demo` | Run the seeded demo repository tests. |
| `make test-website` | Run deterministic public fixture and website interaction contract tests. |
| `make build` | Build the Compose images. |
| `make up` | Start the Compose services. |
| `make down` | Stop the Compose services. |
| `make gpu-check` | Run a CuPy device and computation check inside the worker. |
| `npm run dev` | Start the frontend development server. |
| `npm run build` | Build the standalone Next.js production application. |
| `npm run start` | Start the built frontend. |
| `npm test` | Run the frontend Vitest suite. |
| `npm run test:coverage` | Run frontend tests with V8 coverage. |
| `npm run typecheck` | Run TypeScript without emitting files. |
| `npm run e2e` | Build and run Playwright tests. |

<!-- END AUTO-GENERATED -->

### 19.1 Covered behaviors

Backend tests cover:

- canonical URL validation;
- public/private GitHub metadata handling;
- CPU context ranking;
- deterministic comparison;
- repository profiling, diff, context, impact, and patch safety;
- Nebius structured output, fallbacks, root-cause, and repair behavior;
- sandbox command/path/runtime policy;
- orchestration success, analysis-only, regression, repair, and environment errors;
- SQLite persistence;
- API health, JSON body parsing, validation, and repair errors.

Frontend tests cover:

- landing content and validation;
- API requests and error behavior;
- timeline and proof card;
- verification report rendering;
- repair request and repair evidence;
- production browser journeys with Playwright.

GPU tests cover:

- worker health;
- bearer authorization;
- deterministic relevance ranking;
- result limits.

### 19.2 Latest verified evidence

The October 19 local quality matrix verified 149 backend tests (90.71% line coverage), 32 frontend tests (95.54% statement coverage), seven Chromium E2E tests with intercepted API responses, eight website tests, six GPU-worker CPU-fallback tests, and one seeded repository test: 203 automated tests total. Type checking, production build and npm audit passed. See the [October 18 hardening receipt](hardening-evidence.md) for the earlier security/dependency scan and its explicit limitations; those observations are dated, not a certification of every image, OS package or attack surface.

Physical CUDA is restored and reverified on driver `595.99.02`; see the [October 19 GPU receipt](gpu-recovery-2026-10-19.md). The [credential-free local judging build](judge-test-build.md) also executed real Python and Node Docker fixtures through the API/UI stack, producing base PASS, deliberately broken head FAIL, and manually repaired checks PASS. Its persistent records contain actual local Git SHAs and execution receipts, prominently marked `evidence_mode: controlled_fixture`; no model, live GitHub PR or GPU ranking is involved in that mode. These results do not replace the still-unverified live Nebius inference/PR acceptance and submission recording.

## 20. CI/CD

GitHub Actions runs on pushes and pull requests targeting `main`.

| Job | Checks |
| --- | --- |
| `backend` | Python 3.12, install backend requirements, run pytest. |
| `frontend` | Node 22, `npm ci`, coverage, typecheck, build, install Chromium, Playwright. |
| `gpu-worker` | Python 3.12, install CPU-test dependencies, run worker tests. |
| `security` | Resolved Python dependency `pip-audit`, `npm audit --audit-level=high` and committed-secret pattern rejection. |
| `judge-test-build` | Separate keyless Compose stack, real Python/Node Docker fixtures, no-mock Chromium report checks and exported JSON evidence artifact. |

CI is deliberately CPU-compatible. Physical CUDA proof belongs to the Dell smoke test and live deployment checklist.

## 21. Operations and troubleshooting

### 21.1 Health is degraded

- `nebius: not_configured`: set `NEBIUS_API_KEY` on the server and recreate the backend.
- `gpu_worker: error`: inspect worker logs, token agreement, service health, and NVIDIA runtime.
- `sandbox: disabled`: start through the production Compose configuration or set `ENABLE_SANDBOX=true` only where the backend can safely access Docker.

### 21.2 Dell hostname cannot resolve

1. Confirm the Dell is powered on and connected to Tailscale.
2. Confirm this machine is on the same tailnet.
3. Confirm MagicDNS or the `dell-ts` SSH alias resolves to the current host.
4. Run `ssh -o BatchMode=yes -o ConnectTimeout=8 dell-ts hostname`.
5. Override `AEGIS_REMOTE_HOST` if the alias changed.

### 21.3 GPU worker reports CPU

1. Run `./scripts/gpu-smoke-test.sh`.
2. Run `nvidia-smi` on the host.
3. Verify `docker info` recognizes the NVIDIA runtime.
4. Check driver/container CUDA compatibility.
5. Rebuild the worker without cached layers.
6. Inspect `docker compose logs gpu-worker`.

### 21.4 Sandbox builds fail

- Confirm the host Docker socket is mounted and `DOCKER_GID` matches the host socket group.
- Confirm outbound package access is available during image build.
- Confirm the detected runtime is Python or JavaScript/TypeScript.
- Read the bounded build stdout/stderr in the finding.

### 21.5 Run becomes analysis-only

- Check `ENABLE_SANDBOX`.
- Check that Nemotron produced a nonempty test path and source.
- Check that the repository exposes a supported test command.
- Check that the generated command exactly matches the detected command.

### 21.6 Repair is rejected

- Confirm the original run is `REGRESSION_FOUND`.
- Confirm Nebius and sandbox execution are enabled.
- Check that the selected finding is a `REGRESSION`.
- Review the repair error for unsafe paths, out-of-scope files, invalid diff format, failed checks, or timeouts.

For deployment, rollback, backup, and log commands, use [RUNBOOK.md](RUNBOOK.md).

## 22. Hackathon demonstration

The intended three-minute story is:

1. paste a real public GitHub PR;
2. show repository analysis and CUDA-ranked context;
3. show Nemotron hypotheses and the generated adversarial test;
4. show base pass and PR fail;
5. show `REGRESSION_FOUND` with exact evidence;
6. generate a minimal repair;
7. show existing tests, generated test, build, and lint results;
8. finish on `FIX_VERIFIED` only when every required check passes.

Use [hackathon-submission.md](hackathon-submission.md) for the exact voice-over, recording safety checklist, Devpost text, and final submission checklist.

## 23. Current project status

As of October 17, 2026:

- core product workflow is implemented;
- optional repair and repair verification are implemented;
- repository is public and MIT-licensed;
- README, architecture, security, user journeys, verification semantics, runbook, contribution guide, and submission kit are present;
- the project website and browser test build are publicly hosted on GitHub Pages;
- GitHub Actions is green on `main`;
- the latest complete local matrix passed 69 tests;
- the five-hour continuation heartbeat remains enabled;
- the Dell Tailscale connection, NVIDIA container runtime, and real CuPy CUDA ranking workload are verified on the RTX 3050 Ti;
- all three production services are healthy on the Dell, with the backend on port 8080;
- the backend production image now includes the Git and Docker tools needed by repository analysis and sandbox execution;
- live Docker sandbox testing produced baseline PASS, seeded regression FAIL, and manually repaired fixture PASS;
- the Nebius key authenticates and the configured model is in the catalog, but actual inference is blocked by HTTP 402 (no usable budget);
- a public full-stack application URL and final YouTube upload remain outstanding;

The captured worker health and authenticated ranking evidence report `accelerator: cuda`; see [live-gpu-evidence.md](live-gpu-evidence.md). Deployment and deterministic sandbox results are in [live-stack-evidence.md](live-stack-evidence.md). The latter is a manual fixture experiment, not a model-generated public PR review. No documentation or UI should claim a successful live Nemotron run until inference succeeds.

## 24. Limitations and roadmap

### Current limitations

- public GitHub pull requests only;
- one execution per branch, so flaky tests are not automatically repeated;
- Python and JavaScript/TypeScript execution profiles only;
- model-generated tests depend on the detected repository test command;
- dependency installation has network access during image build;
- Docker socket access is a trusted-host boundary;
- SQLite and in-process background tasks are appropriate for the hackathon MVP, not horizontal scale;
- no GitHub App, webhook, check-run, comment, or automatic repair PR creation;
- no authentication or multi-tenant authorization in the application API;
- no public cloud deployment has been completed yet.

### Recommended next steps

1. Resolve Nebius billing/credits with support and confirm a real inference succeeds.
2. Complete a real public-PR end-to-end run and capture evidence.
3. Publish the live application behind HTTPS with authentication or bounded hackathon access.
4. Keep the GitHub Pages project website and test build in sync with releases.
5. Record and publish the three-minute demonstration.
6. Add stable-result repetition for flaky-test resistance.
7. Replace the Docker socket with an isolated executor service.
8. Add a queue and managed database for concurrent production runs.
9. Build a GitHub App and check-run integration.

## 25. Related documentation

- [README](../README.md)
- [Architecture](architecture.md)
- [Agent stages](agents.md)
- [Security model](security.md)
- [Model and credit policy](model-budget.md)
- [Submission readiness audit](submission-readiness.md)
- [Hardening evidence](hardening-evidence.md)
- [Verification semantics](verification.md)
- [User journeys](user-journeys.md)
- [Hackathon submission kit](hackathon-submission.md)
- [Live Dell GPU evidence](live-gpu-evidence.md)
- [Contributor guide](CONTRIBUTING.md)
- [Operations runbook](RUNBOOK.md)
- [Original extracted project specification](../work/AegisPR-spec.md)

