# Hackathon Submission Kit

This file is the source of truth for the Nebius × NVIDIA Global AI Hackathon submission. Replace only the bracketed recording and deployment fields after the live Dell GPU run is captured.

## Submission profile

- **Project:** AegisPR
- **Tagline:** Don't trust a PR. Prove it.
- **Track:** Coding and Agentic Engineering
- **Source:** <https://github.com/Hari-Aditya-003/AegisPR>
- **Project website:** <https://aegispr.mr-adityahari.chatgpt.site>
- **License:** MIT
- **Demo application:** `[ADD PUBLIC GPU-HOSTED APPLICATION URL]`
- **Video:** `[ADD PUBLIC YOUTUBE URL, 3:00 OR SHORTER]`

The project website currently requires owner sign-in. Make it public only when the owner is ready to share the submission.

## Short description

AegisPR is an autonomous pull request verification agent that turns AI review claims into executable experiments. It analyzes a public GitHub pull request, maps the affected code, asks NVIDIA Nemotron on Nebius Token Factory for concrete risk hypotheses and adversarial tests, and executes the same generated test against the base and pull request commits. A test that passes before the change and fails afterward becomes reproducible evidence of a regression. For confirmed regressions, AegisPR can propose a minimal patch and mark it `FIX_VERIFIED` only after the existing suite, generated test, build, and lint checks pass in an isolated workspace.

## What makes it different

Most AI code review ends with “this might break.” AegisPR continues through a deterministic evidence chain:

```text
CLAIM → HYPOTHESIS → TEST → BASE + PR EXECUTION → EVIDENCE → REPAIR → RE-VERIFICATION
```

The model proposes experiments, but it does not decide whether they passed. Exit codes and branch-by-branch observations drive the final classification.

## NVIDIA and Nebius usage

- **NVIDIA Nemotron 3 Ultra** is called through the OpenAI-compatible Nebius Token Factory API for risk hypotheses, test synthesis, evidence summaries, and minimal repair proposals.
- **Dell RTX 3050 Ti** runs the GPU worker. CuPy performs hashed term-document vector construction, cosine similarity scoring, and repository-context ranking before Nemotron receives a bounded prompt.
- **CUDA telemetry** records the selected device and whether each ranking used CUDA or the visible CPU fallback.
- **Docker sandboxes** execute untrusted repository checks with no runtime network, dropped Linux capabilities, process limits, and resource limits.

## Three-minute demo script

### 0:00–0:20 — The problem

> Existing tests can pass while a pull request introduces a new edge-case regression. AI reviewers can suggest risks, but suggestions are not proof. AegisPR turns AI reasoning into executable verification.

### 0:20–0:35 — Start a run

1. Show the public GitHub pull request.
2. Paste its URL into AegisPR.
3. Select **Verify PR**.

### 0:35–1:05 — Agent reasoning and GPU context

1. Show repository profiling, changed files, and the impact graph.
2. Show the GPU worker reporting the Dell NVIDIA device and `used_gpu: true`.
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
- [ ] Nebius API key is present only in the server-side `.env`.
- [ ] `/v1/models` confirms the configured Nemotron model is available.
- [ ] Health endpoint reports Nebius configured and the GPU worker reachable.
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
- [ ] Public project website audience enabled by the owner
- [ ] Public YouTube demonstration, three minutes or shorter
- [x] Live Dell CUDA application-workload evidence captured
- [ ] Live Nebius evidence captured after the owner supplies the server credential

