# AegisPR

Don't trust a PR. Prove it.

AegisPR is an evidence-backed pull request verification agent powered by NVIDIA Nemotron on Nebius Token Factory. It analyzes a code change, proposes targeted tests, executes the same test against the base and pull request commits, and reports what the resulting evidence supports—including when the answer is inconclusive.

## Hackathon submission and judging

**Track:** Best Apps and Agents. **Source:** this public repository. **License:** [MIT](LICENSE). The [official rules](https://nebiusglobalaihackathon.devpost.com/rules) require a working project using an NVIDIA open model through Nebius Token Factory or Nebius AI Cloud, public licensed source with setup instructions, a working demo/hosted app/test build, a project description, a public YouTube demonstration shorter than three minutes, and free judge access through the judging period. The project uses **Token Factory**, not Nebius AI Cloud. The published submission deadline is **October 30, 2026, 10:00 a.m. PDT**; the judging period ends **December 15, 2026**. This README and the [submission kit](docs/hackathon-submission.md) distinguish completed evidence from submission items still owned by the entrant.

| What to inspect | Access and evidence | Limit |
| --- | --- | --- |
| Project website and usage guide | [AegisPR website](https://hari-aditya-003.github.io/AegisPR/) | Explains the product and hands a validated PR URL to the private app; the static page does not execute a review. |
| Immediate working test build | [Interactive coupon experiment](https://hari-aditya-003.github.io/AegisPR/demo/) | Free, no account or tokens; fixed JavaScript example, not arbitrary PR or model inference. |
| Actual controlled-PR evidence | [Read-only public evidence summary](https://hari-aditya-003.github.io/AegisPR/evidence/) and [latest live-run receipt](docs/live-pr-super-comparison-2026-10-26.md) | Two runs on one deliberately seeded public PR; the October 26 Super-model run confirmed a stable output change but remained `INCONCLUSIVE` on intent. The full authenticated report remains private. |
| Reproducible full local interface/API/executor | [Linux/Docker judging build](docs/judge-test-build.md) | Real Docker execution of **prewritten** Python/Node tests and manual repairs, with zero model calls, no GPU and no provider credentials. Run only on a trusted machine with Docker-socket access. |
| Full live PR workflow | [Private deployment instructions below](#quick-start) | Requires a server-side Nebius key, usable credits, Docker and an authenticated deployment. The Dell production instance is not a public judge URL. |

The final public YouTube demonstration is **not yet linked here**; the entrant is preparing it. A private [94.64-second real-time controlled-PR recording and 34.12-second read-only evidence walkthrough](docs/live-pr-super-comparison-2026-10-26.md) now exist, but they are not the final uploaded submission video. Before submitting, the entrant must verify that the video shows the working project truthfully, is publicly viewable on YouTube and shorter than three minutes; keep the free test build accessible through the judging period. Devpost also requires honest platform/model feedback, personal eligibility and ownership declarations, permission for third-party material, English-language materials or translations, and an explanation of significant updates if the project predates the submission period. No prize, track eligibility or judging outcome is guaranteed.

New here? Follow the [How to use guide](https://hari-aditya-003.github.io/AegisPR/#how-to-use) for the browser experiment, token-free local Docker build, or live PR setup. See the [website design and validation notes](docs/website-design.md).

To review a PR from the website, open [Verify a PR](https://hari-aditya-003.github.io/AegisPR/#verify-pr), paste a public GitHub `/pull/NUMBER` URL (or select the controlled example), and choose **Open private verifier**. The Dell-hosted app opens with that URL prefilled. Connect to the owner's Tailscale network and enter the separate application access code; only then choose **Verify PR**, which can spend provider credits. The **Agent timeline** appears on the resulting report page. This handoff is for authorized operators, not public judge access. The SQLite PR #883 recording is a separate token-free Docker replay of the PR author's existing test, not an AegisPR model-generated report.

An October 23 bounded Nemotron connectivity request succeeded after credits were added; it was not a full PR review. See the [dated receipt](docs/live-nebius-check.md).

The Dell's CUDA ranking worked in [dated October 19](docs/gpu-recovery-2026-10-19.md) and [October 24](docs/gpu-recovery-2026-10-24.md) checks. An intervening October 23 health check found missing NVIDIA userspace libraries. The [October 26 controlled-PR run](docs/live-pr-super-comparison-2026-10-26.md) used Nemotron 3 Super to generate a fresh test that called the changed function on both commits in Docker; two confirmation reruns per side reproduced a behavior change. Three fresh intent votes called it unintended, but their votes are advisory and the product result remained `INCONCLUSIVE`. [Inspect the dated public evidence summaries](https://hari-aditya-003.github.io/AegisPR/evidence/). Neither run is an independent benchmark or confirmed regression.

For a credential-free full local test build, use a trusted Linux machine with Git, Bash, OpenSSL and Docker Engine + Compose:

```bash
git clone https://github.com/Hari-Aditya-003/AegisPR.git
cd AegisPR
bash scripts/judge-test-build.sh start
```

The command prints local report URLs and creates a private access code at `artifacts/judge/access-code`. Enter that code in the report page's **Private deployment access** panel; never publish it. This separate build launches the real interface/API and records actual Docker checks for fixed Python and Node fixtures. When finished, run `bash scripts/judge-test-build.sh stop`. Read the [judging build instructions and explicit limitations](docs/judge-test-build.md): tests and manual repairs are prewritten, not generated by Nemotron. The judging build uses no Nebius key, provider credits or GPU.

A [rehearsed capability-recording workflow](docs/demo-recording.md) can produce a captioned draft without model calls. It clearly separates the browser illustration, saved Docker evidence and current local GPU health; it is not the final live-model submission demonstration.

## Why AegisPR

AI review usually returns an opinion. AegisPR turns a claim into an experiment:

For example, a reviewer of an AI-written pricing change can run the same coupon inputs on the base and proposed versions before merging. If the outputs differ, the report shows the exact commits, test command and values so a person can decide whether the change matches the intended contract. This is useful even when the tool cannot safely call the difference a regression.

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

The newer output-example path compares labeled JSON observations instead of guessed assertions. A stable difference is rerun twice per commit, then may receive a three-vote **advisory** intent review; it is not automatically called a regression. The controlled October 25 PR run exercised those comparison and voting paths with live Nemotron intent calls. A bounded Python changed-line mutant can measure whether a test detects one deliberate fault; that mutation path is locally tested but was not exercised in this run. Other implemented but separately scoped checks include pre-push CLI verification, opt-in time/memory screening, heuristic security/API-signature signals and bounded caller-supplied CUDA-output comparison. They are not claims of comprehensive vulnerability or kernel verification. See the [research workflow and evidence limits](docs/workflow-research-implementation.md).

The [research-feature audit](docs/FEATURE_AUDIT.md) lists what is implemented and what remains. A [12-case seeded evaluation dataset](evals/seeded-prs/README.md) provides executable synthetic base/head examples with hand labels; it is **not** a real-PR benchmark or a measured model accuracy result.

For coding agents and developers, the token-free `aegispr verify` CLI reviews committed changes before push. Its opt-in Docker mode reruns an existing test suite on both revisions and screens time/memory; `aegispr compare-gpu` compares bounded, caller-supplied CUDA output files. Neither command proves correctness or consumes Nemotron credits. Read the [local verification guide and limits](docs/pre-push-verification.md).

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
- Minimal Nemotron repair generation with isolated patch application and re-verification
- Live verification timeline, findings, proof card, and bounded status language
- Persistent local run history and API/SSE access

## Architecture

```text
Browser / Next.js
        │
        ▼
FastAPI orchestrator ─── GitHub API + git
        │
        ├── Nebius Token Factory ── NVIDIA Nemotron (budgeted)
        │
        ├── Dell RTX 3050 Ti ───── CUDA context ranking
        │
        └── Docker sandboxes ───── Base + PR test execution
                         │
                         ▼
                 Evidence report
```

Nemotron is served remotely; the default is the economical Lightning candidate, not a claimed quality winner. The Dell RTX 3050 Ti performs a real, bounded CUDA workload: hashed term-document vector construction, cosine scoring, and context prioritization. If the worker is unavailable, AegisPR records a CPU fallback rather than hiding the loss of acceleration.

Start with the [complete project documentation](docs/PROJECT_DOCUMENTATION.md). Focused references cover [architecture](docs/architecture.md), [agent stages](docs/agents.md), [verification semantics](docs/verification.md), [security](docs/security.md), [live Dell GPU evidence](docs/live-gpu-evidence.md), [live deployment and sandbox evidence](docs/live-stack-evidence.md), [operations](docs/RUNBOOK.md), [contributing](docs/CONTRIBUTING.md), and the [hackathon submission kit](docs/hackathon-submission.md).

## Quick start

Requirements for the **live private deployment** (the public browser experiment and keyless judging build above have different requirements):

- Docker 29+ with Compose
- NVIDIA driver and NVIDIA Container Toolkit on the GPU host
- Nebius Token Factory API key
- Optional GitHub token for higher public API rate limits

```bash
cp .env.example .env
# Add NEBIUS_API_KEY and replace GPU_WORKER_TOKEN and API_ACCESS_TOKEN
# with different random secrets. Example generator: openssl rand -hex 32
# For a local browser, set PUBLIC_API_URL=http://localhost:8000 and
# ALLOWED_ORIGINS=http://localhost:3000 in .env before building.
# On Linux, set DOCKER_GID to the group ID of /var/run/docker.sock.
docker compose up --build -d
docker compose ps
curl http://localhost:8000/health
```

The checked-in `.env.example` contains the existing Dell Tailscale frontend/API origins and a sample Docker-socket group ID; copying it unchanged does **not** configure a fresh local host. Use the local values noted above or your own trusted HTTPS origin, and verify your Docker-socket group ID. Open `http://localhost:3000`, save the private deployment access code (your `API_ACCESS_TOKEN`, never the provider key), paste a public GitHub pull request URL, and select **Verify PR**. The code is kept only in that tab's session storage. Use HTTPS for any internet-accessible deployment; private Tailscale transport is encrypted but not a public judge URL. Docker-socket access is host-equivalent authority: do not expose this PR execution service to arbitrary public users.

The Compose default is `nvidia/Nemotron-3_5-Lightning` through the OpenAI-compatible endpoint `https://api.tokenfactory.nebius.com/v1/`. This lowers estimated token cost versus Ultra. A single [controlled trial with Nemotron 3 Super](docs/live-pr-super-comparison-2026-10-26.md) produced better executable evidence than the preceding Lightning attempts, but is not a controlled multi-PR quality benchmark. The public and authenticated catalogs list both model IDs. A successful model-list request does not confirm inference credits; an actual completion must also succeed. Read the [model and $25 budget policy](docs/model-budget.md) before enabling paid calls.

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
python3.12 -m venv .venv
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
# From the repository root after installing backend and frontend dependencies;
# install Playwright Chromium for browser checks.
make test
```

The [CI workflow](.github/workflows/ci.yml) also runs backend, frontend, GPU-worker fallback, security, CLI Docker acceptance and a keyless full-stack judging build. The [October 26 run](https://github.com/Hari-Aditya-003/AegisPR/actions/runs/40225985200) passed all six jobs; the corresponding local backend suite passed 243 tests at 88.96% coverage. The public website's 25 tests passed in its [deployment workflow](https://github.com/Hari-Aditya-003/AegisPR/actions/runs/40173554839). These checks include mocks and fixed fixtures where labeled; CI does not replay the dated paid inference call or prove GPU CUDA availability on every host.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/verifications` | Start verification for a public pull request URL |
| `GET` | `/api/verifications/{id}` | Read complete run state |
| `GET` | `/api/verifications/{id}/events` | Stream run updates with SSE |
| `GET` | `/api/verifications/{id}/findings` | Read differential findings |
| `GET` | `/api/verifications/{id}/impact` | Read impact nodes and edges |
| `POST` | `/api/verifications/{id}/repair` | Generate an isolated minimal patch and verify it against recorded evidence |
| `GET` | `/health` | Inspect Nebius, GPU worker, and sandbox configuration |
| `GET` | `/api/budget` | Authenticated app-side usage/reservation estimate, not provider balance |

Repair requests are accepted only for a confirmed differential regression. A patch remains inside a temporary checkout, and `FIX_VERIFIED` is emitted only when the existing suite, generated regression test, and every configured build or lint check pass.

## Environment variables

| Name | Required | Description |
| --- | --- | --- |
| `NEBIUS_API_KEY` | Production | Server-side Token Factory key |
| `NEBIUS_BASE_URL` | No | OpenAI-compatible endpoint |
| `NEBIUS_MODEL` | No | NVIDIA model ID |
| `INTENT_REVIEW_MODELS` | No | Optional four distinct, priced NVIDIA Nemotron IDs for one advisory vote each; defaults to three votes from `NEBIUS_MODEL` |
| `API_ACCESS_TOKEN` | Production | Separate private deployment code; all `/api/*` routes require Bearer authentication |
| `INFERENCE_BUDGET_USD` | No | Persistent total admission estimate, default $20 |
| `INFERENCE_RUN_BUDGET_USD` | No | Per-run admission estimate, default $0.25 |
| `INFERENCE_MAX_CALLS_PER_RUN` | No | Provider attempts per verification including repairs, default 5 |
| `GITHUB_TOKEN` | No | Higher GitHub API rate limits |
| `GPU_WORKER_TOKEN` | Production | Shared token for the internal GPU worker |
| `PUBLIC_API_URL` | Production | Browser-visible FastAPI URL used at frontend build time |
| `ALLOWED_ORIGINS` | Production | Exact comma-separated frontend origins |
| `DOCKER_GID` | Dell host | Group ID allowed to access the Docker socket |
| `BACKEND_PORT` | No | Host port for FastAPI, default `8000` |

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

## NVIDIA model, Nebius service and hackathon fit

AegisPR makes runtime requests to Nebius Token Factory's OpenAI-compatible inference API using NVIDIA open models. The repository defaults to **`nvidia/Nemotron-3_5-Lightning`** for lower estimated cost; the [latest controlled acceptance run](docs/live-pr-super-comparison-2026-10-26.md) used **`nvidia/nemotron-3-super-120b-a12b`** for a quality trial. The model proposes bounded risk/test plans, generated usage examples, advisory intent reviews and optional repairs; deterministic Git/Docker execution supplies the actual branch results. Token Factory lets this workflow call a hosted model without deploying a large model on the 4 GB Dell GPU. Exact-response caching and app-side admission estimates conserve credits. This is an **engineering workflow benefit, not a measured speedup or proof of the best model**.

The [October 26 Super-model run](docs/live-pr-super-comparison-2026-10-26.md) generated one changed-function test, executed it on both commits, reproduced the stable output difference with four confirmation executions, and recorded three unanimous advisory `unintended` votes. The finding was `BEHAVIOR_CHANGE`; overall status stayed `INCONCLUSIVE` because model votes alone do not confirm a regression. Its four calls cost **$0.001450 app-estimated**, and the persistent ledger showed **$0.007568 app-estimated lifetime use** afterward; neither is a provider invoice or verified account balance. Earlier Lightning attempts did not generate valid fresh branch evidence, but prompts also changed, so independent real-PR accuracy, controlled comparative model accuracy and speedup remain unmeasured. See the [budget policy](docs/model-budget.md) and [public evidence summaries](https://hari-aditya-003.github.io/AegisPR/evidence/).

For broader **advisory** intent review, set `INTENT_REVIEW_MODELS=nvidia/Nemotron-3_5-Lightning,nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B,nvidia/nemotron-3-super-120b-a12b,nvidia/Nemotron-3-Ultra-550b-a55b` in the private server environment. This uses four distinct models and four calls, so it runs only when at most one of the five allowed provider attempts has already been used. It records each model's vote in the report and treats disagreement or an incomplete review as unclear. It does **not** approve a PR or prove the author's intent: even unanimous votes leave an observed behavior change `INCONCLUSIVE` until the author or maintainer confirms the requirement. The four-model path is locally tested; the October 26 evidence above used one model for all three votes, not this ensemble.

The Dell RTX 3050 Ti independently runs the verified CuPy/CUDA context-ranking workload. Real Docker fixture testing produced baseline PASS, changed code FAIL, and manually repaired code PASS. The Dell is **local infrastructure**, not a Nebius AI Cloud GPU instance or a Token Factory Sandbox. No Nebius AI Cloud service, Tavily runtime integration or cloud GPU benchmark is claimed. See [live deployment evidence](docs/live-stack-evidence.md).

## Free public hosting

GitHub Pages publishes `website/dist` using [the website workflow](.github/workflows/pages.yml). It hosts the project website and browser test build without server credentials or Tailscale. It cannot host the FastAPI backend or CUDA worker. Full-stack setup instructions above describe running those services on a Linux NVIDIA GPU host.

Run the public test build locally with:

```bash
node --test website/tests/boundary.test.mjs
python3 -m http.server 3112 --directory website/dist
# Open http://localhost:3112/demo/
```

## License

[MIT License](LICENSE)
