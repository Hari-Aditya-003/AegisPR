# Hackathon Submission Kit

This is a draft kit for the Nebius × NVIDIA Global AI Hackathon submission. Finalize the claims and bracketed fields only after judge access and the final recording are verified. A bounded model-only completion succeeded October 23. The [October 26 live controlled-PR run](live-pr-super-comparison-2026-10-26.md) generated a fresh Nemotron 3 Super usage test, executed it in Docker on both commits, confirmed changed outputs with two reruns per side, and recorded three fresh paid intent votes. All three voted `unintended`; the product status remained `INCONCLUSIVE` because advisory votes are not confirmed regression proof. The owner will create and upload the final YouTube video themselves.

## Submission profile

- **Project:** AegisPR
- **Tagline:** Don't trust a PR. Prove it.
- **Track:** Best Apps and Agents (owner-selected October 24; organizer eligibility remains authoritative)
- **Source:** <https://github.com/Hari-Aditya-003/AegisPR>
- **Project website:** <https://hari-aditya-003.github.io/AegisPR/>
- **License:** MIT
- **Public test build:** <https://hari-aditya-003.github.io/AegisPR/demo/>
- **Controlled-PR evidence viewer:** <https://hari-aditya-003.github.io/AegisPR/evidence/>
- **Video:** `[OWNER TO ADD PUBLIC YOUTUBE URL, STRICTLY UNDER 3:00]`

The website and interactive browser test build are published on GitHub Pages.
The test build executes a deterministic coupon fixture in JavaScript; it is not
a public GPU/Nemotron service. A model-only connectivity check succeeded October 23. The [October 26 run](live-pr-super-comparison-2026-10-26.md) records one fresh Super-generated test and three intent calls after Docker comparison of the controlled public PR. That is **not** an independent benchmark or confirmed unintended-regression verdict; final status was `INCONCLUSIVE`. The public evidence viewer shows an older saved example, not the October 26 private backend report.
The [credential-free full local judging build](judge-test-build.md) also runs the
real interface/API/Docker executor with prewritten Python and Node fixtures.
It requires Docker, not paid tokens; it is not live model/PR evidence.

A [captioned capability-preview workflow](demo-recording.md) and two [private October 26 recordings](live-pr-super-comparison-2026-10-26.md) are available as source material. None is the final public submission video. The owner has explicitly taken responsibility for preparing and uploading the final YouTube video.

## Short description

AegisPR is an autonomous pull request verification agent that turns AI review claims into executable experiments. It analyzes a public GitHub pull request, maps the affected code, asks NVIDIA Nemotron on Nebius Token Factory for concrete risk hypotheses and adversarial tests, and executes the same generated test against the base and pull request commits. A test that passes before the change and fails afterward becomes reproducible evidence of a regression. For confirmed regressions, AegisPR can propose a minimal patch and mark it `FIX_VERIFIED` only after the existing suite, generated test, build, and lint checks pass in an isolated workspace.

## What makes it different

Most AI code review ends with “this might break.” AegisPR continues through a deterministic evidence chain:

```text
CLAIM → HYPOTHESIS → TEST → BASE + PR EXECUTION → EVIDENCE → REPAIR → RE-VERIFICATION
```

The model proposes experiments, but it does not decide whether they passed. Exit codes and branch-by-branch observations drive the final classification.

## NVIDIA and Nebius usage

**Dated evidence:** October 17 and 19 Dell receipts show real CUDA ranking and Docker sandbox differential execution. On October 23 the model completed one bounded connectivity request after credits were added, while the Dell GPU health check was degraded by missing NVIDIA userspace libraries. The [October 24 recovery receipt](gpu-recovery-2026-10-24.md) confirms local CUDA ranking again. The [October 26 Super trial](live-pr-super-comparison-2026-10-26.md) records a fresh generated test, real Docker branch comparisons and three intent calls. It found stable `BEHAVIOR_CHANGE`, but the overall status remained `INCONCLUSIVE`. These observations do not establish a confirmed unintended regression, Nebius GPU hosting, comparative model accuracy or a public full-stack service. See [live-stack evidence](live-stack-evidence.md) and the [model-only receipt](live-nebius-check.md).

- **NVIDIA Nemotron** is integrated through Nebius Token Factory for risk hypotheses, test synthesis, evidence summaries, and minimal repair proposals. The repository default is `nvidia/Nemotron-3_5-Lightning` as an economical candidate; the October 26 controlled PR run used `nvidia/nemotron-3-super-120b-a12b` after Lightning plans repeatedly failed validation. One usable trial does not establish a comparative PR task-quality score or confirmed regression.
- **Dell RTX 3050 Ti** runs the GPU worker. CuPy performs hashed term-document vector construction, cosine similarity scoring, and repository-context ranking before Nemotron receives a bounded prompt.
- **CUDA telemetry** records the selected device and whether each ranking used CUDA or the visible CPU fallback.
- **Docker sandboxes** execute untrusted repository checks with no runtime network, dropped Linux capabilities, process limits, and resource limits.

**October 24 update:** after the October 23 missing-library incident, matching NVIDIA userspace packages, normal GPU Compose, CuPy and authenticated CUDA ranking were reverified in the [new GPU receipt](gpu-recovery-2026-10-24.md). Spending/authentication/security/UI improvements and the remaining gates are recorded in [hardening evidence](hardening-evidence.md). Do not copy this kit into a final submission until current GPU health, actual PR evidence and the recording are checked.

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

For the recorded October 26 run, show the actual generated output example and its result:

```text
BASE COMMIT          PASS · discount exceeds total → 0
PULL REQUEST COMMIT  PASS · same input → -5
FINDING              BEHAVIOR_CHANGE
OVERALL              INCONCLUSIVE · human intent review needed
```

Narration:

> The same model-generated example ran on both exact commits. Both executions passed, but the output changed from zero to negative five. Two reruns per side confirmed the difference. Three model votes considered it unintended; AegisPR leaves intent to a human reviewer.

Do **not** use a `REGRESSION_FOUND` card or claim a confirmed regression for either the October 25 or October 26 controlled run. Both ended `INCONCLUSIVE` despite stable output differences and 3/3 advisory `unintended` votes.

### 1:40–2:15 — Inspect evidence and limits

The October 26 behavior-change finding does not authorize a generated repair. Use this time to inspect the exact commit IDs, generated test, stdout and confirmation count. A separate fixed-fixture repair may be shown only if explicitly labeled **prewritten/manual**, not as a live Nemotron repair. End on `FIX_VERIFIED` only for a separately recorded, real generated repair that passed every required check.

Narration:

> The report preserves what ran and what changed. A human can decide whether the coupon contract should remain nonnegative before asking for a repair.

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
- [ ] `nvidia-smi` succeeds on the host at final recording time (October 23 check was degraded).
- [ ] NVIDIA Container Toolkit exposes the GPU inside `gpu-worker` at final recording time.
- [x] Nebius API key is present only in the server-side `.env`.
- [x] `/v1/models` confirms the configured Nemotron model is available.
- [ ] Health endpoint reports Nebius configured and the GPU worker reachable at final recording time.
- [x] A bounded model-only inference completed October 23; a fresh controlled-PR test and intent review completed October 26, with `INCONCLUSIVE` overall status.
- [ ] GPU worker health and authenticated ranking record `accelerator: cuda` and RTX 3050 Ti metadata at final recording time (dated October 19 receipt exists).
- [x] A controlled public PR reaches fresh Super-generated test execution in Docker on both commits, two confirmation reruns per side, and three fresh Nemotron intent reviews; the resulting product status was `INCONCLUSIVE`.
- [ ] A human-confirmed unintended regression or independently labeled real-PR benchmark exists; advisory intent votes do not satisfy this.
- [ ] The proof card shows exact commits, commands, logs, exit codes, and durations.
- [ ] Repair verification reaches `FIX_VERIFIED` with all required checks passing.
- [x] Sampled private October 26 recordings do not show the API key or shared worker token; check the owner's final edited upload separately.
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
- [x] Public interactive browser test-build URL and read-only controlled-PR evidence URL (not an unrestricted full live application)
- [x] Public project website on GitHub Pages
- [ ] Public YouTube demonstration, three minutes or shorter
- [x] Live Dell CUDA application-workload evidence captured
- [x] Bounded model-only Nebius inference, fresh Super-generated controlled-PR testing and three fresh intent calls captured after credits became usable; confirmed unintended-regression verdict remains open

