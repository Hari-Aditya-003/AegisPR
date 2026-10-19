# Hackathon Submission Kit

This is a draft kit for the Nebius × NVIDIA Global AI Hackathon submission. Finalize the claims and bracketed fields only after successful live Nemotron inference, actual PR acceptance, judge access and the final recording are verified. Capturing a Dell GPU run alone does not satisfy those gates.

## Submission profile

- **Project:** AegisPR
- **Tagline:** Don't trust a PR. Prove it.
- **Track:** Coding and Agentic Engineering
- **Source:** <https://github.com/Hari-Aditya-003/AegisPR>
- **Project website:** <https://hari-aditya-003.github.io/AegisPR/>
- **License:** MIT
- **Public test build:** <https://hari-aditya-003.github.io/AegisPR/demo/>
- **Video:** `[ADD PUBLIC YOUTUBE URL, STRICTLY UNDER 3:00]`

The website and interactive browser test build are published on GitHub Pages.
The test build executes a deterministic coupon fixture in JavaScript; it is not
a public GPU/Nemotron service. Full-stack inference remains blocked by HTTP 402.
The [credential-free full local judging build](judge-test-build.md) also runs the
real interface/API/Docker executor with prewritten Python and Node fixtures.
It requires Docker, not paid tokens; it is not live model/PR evidence.

A [captioned capability-preview workflow](demo-recording.md) is also available. Its draft footage must not be substituted for the missing real model/PR demonstration or presented as a completed submission video.

## Short description

AegisPR is an autonomous pull request verification agent that turns AI review claims into executable experiments. It analyzes a public GitHub pull request, maps the affected code, asks NVIDIA Nemotron on Nebius Token Factory for concrete risk hypotheses and adversarial tests, and executes the same generated test against the base and pull request commits. A test that passes before the change and fails afterward becomes reproducible evidence of a regression. For confirmed regressions, AegisPR can propose a minimal patch and mark it `FIX_VERIFIED` only after the existing suite, generated test, build, and lint checks pass in an isolated workspace.

## What makes it different

Most AI code review ends with “this might break.” AegisPR continues through a deterministic evidence chain:

```text
CLAIM → HYPOTHESIS → TEST → BASE + PR EXECUTION → EVIDENCE → REPAIR → RE-VERIFICATION
```

The model proposes experiments, but it does not decide whether they passed. Exit codes and branch-by-branch observations drive the final classification.

## NVIDIA and Nebius usage

**Verified status (October 17):** All three services are healthy on the Dell.
CUDA ranking and real Docker sandbox differential execution have been tested.
The Nebius key authenticates and the exact Nemotron ID is in the model catalog,
but inference returns HTTP 402 (no usable budget). The model descriptions and
recording script below describe the implemented integration and intended final
demonstration; they are not evidence of a completed live model run. Do not submit
model quality ratings or claim a working Nebius demo until inference succeeds.
See [live-stack-evidence.md](live-stack-evidence.md).

- **NVIDIA Nemotron** is integrated through Nebius Token Factory for risk hypotheses, test synthesis, evidence summaries, and minimal repair proposals. The current default is `nvidia/Nemotron-3_5-Lightning` as an economical evaluation candidate; Ultra remains an explicit comparison option. No successful live model use or quality score is claimed until credits work.
- **Dell RTX 3050 Ti** runs the GPU worker. CuPy performs hashed term-document vector construction, cosine similarity scoring, and repository-context ranking before Nemotron receives a bounded prompt.
- **CUDA telemetry** records the selected device and whether each ranking used CUDA or the visible CPU fallback.
- **Docker sandboxes** execute untrusted repository checks with no runtime network, dropped Linux capabilities, process limits, and resource limits.

**October 19 update:** the host driver recovered to matching `595.99.02`; normal GPU Compose, CuPy and authenticated CUDA ranking have been reverified in the [new GPU receipt](gpu-recovery-2026-10-19.md). The October 18 fallback was temporary. Spending/authentication/security/UI improvements and the remaining gates are recorded in [hardening evidence](hardening-evidence.md). Do not copy this kit into a final submission until live inference, actual PR evidence and the recording are checked.

## Three-minute demo script

### 0:00–0:20 — The problem

> Existing tests can pass while a pull request introduces a new edge-case regression. AI reviewers can suggest risks, but suggestions are not proof. AegisPR turns AI reasoning into executable verification.

### 0:20–0:35 — Start a run

1. Show the public GitHub pull request.
2. Paste its URL into AegisPR.
3. Select **Verify PR**.

### 0:35–1:05 — Agent reasoning and GPU context

1. Show repository profiling, changed files, and the impact graph.
2. Show the GPU worker's actual `accelerator: cuda` result and Dell NVIDIA device metadata; a visible CPU fallback is not CUDA evidence.
3. Show Nemotron's bounded risk hypotheses and generated adversarial test.

Narration:

> Nemotron plans the experiment on Nebius. The Dell RTX GPU ranks the most relevant repository context before that request, so both compute paths are part of the verification workflow.

### 1:05–1:40 — Differential proof

Show one generated test with:

```text
BASE COMMIT          PASS
PULL REQUEST COMMIT  FAIL
CLASSIFICATION       REGRESSION_FOUND
```

Narration:

> The same generated test passes before the change and fails after it. That branch difference—not model confidence—is why AegisPR reports a regression.

### 1:40–2:15 — Repair and re-verification

1. Select **Generate and verify repair**.
2. Show the minimal unified diff.
3. Show the separate existing-test, generated-test, build, and lint results.
4. End on `FIX_VERIFIED` only if every required check passed.

Narration:

> The proposed patch stays in an ephemeral checkout. AegisPR never edits the source repository and never trusts the repair until the recorded checks pass.

### 2:15–2:40 — Architecture

```text
GitHub PR → FastAPI orchestrator → Nemotron on Nebius
                         ├──────→ Dell RTX CUDA context ranker
                         └──────→ isolated base / PR / repair sandboxes
```

### 2:40–3:00 — Closing

> AegisPR doesn't ask developers to trust another AI reviewer. It gives them executable evidence before they merge. Don't trust a PR. Prove it.

## Nebius and NVIDIA feedback

The OpenAI-compatible Token Factory interface made it straightforward to place Nemotron behind a typed, provider-isolated client. Structured JSON output is especially useful for agent stages that must feed deterministic tools. For future developer experience improvements, model discovery could expose clearer structured-output capability metadata, stable model aliases, and per-model context and rate-limit information in one machine-readable response. On the local NVIDIA path, CuPy made a bounded CUDA workload easy to demonstrate while retaining a transparent CPU fallback; production deployment still benefits from careful NVIDIA Container Toolkit and driver compatibility checks.

## Recording checklist

- [x] Dell host is reachable over Tailscale.
- [x] `nvidia-smi` succeeds on the host.
- [x] NVIDIA Container Toolkit exposes the GPU inside `gpu-worker`.
- [x] Nebius API key is present only in the server-side `.env`.
- [x] `/v1/models` confirms the configured Nemotron model is available.
- [x] Health endpoint reports Nebius configured and the GPU worker reachable (credential presence only).
- [ ] A real inference completes successfully (currently HTTP 402).
- [x] GPU worker health and authenticated ranking record `accelerator: cuda` and RTX 3050 Ti device metadata.
- [ ] A real public PR completes base and PR execution.
- [ ] The proof card shows exact commits, commands, logs, exit codes, and durations.
- [ ] Repair verification reaches `FIX_VERIFIED` with all required checks passing.
- [ ] No API key, shared worker token, or private host detail appears in the recording.
- [ ] Video duration is no longer than three minutes.

## Final submission checklist

- [x] Public source repository
- [x] Open-source license
- [x] README and setup instructions
- [x] Project description
- [x] NVIDIA open-source model integration
- [x] Nebius Token Factory integration
- [x] Real CUDA workload and explicit fallback reporting
- [x] Automated test and security verification
- [ ] Public working demo application URL
- [x] Public project website on GitHub Pages
- [ ] Public YouTube demonstration, three minutes or shorter
- [x] Live Dell CUDA application-workload evidence captured
- [ ] Live Nebius inference evidence captured after billing credits become usable

