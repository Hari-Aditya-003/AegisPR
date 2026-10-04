# AegisPR Architecture

## Runtime components

The Next.js frontend accepts a public GitHub pull request URL and renders live run state. It never receives provider keys.

The FastAPI service owns orchestration, GitHub access, repository inspection, prompt construction, model calls, sandbox policy, differential classification, and persistence. Specialized “agents” are stages inside one process, not independently privileged services.

Nebius Token Factory serves the NVIDIA Nemotron model through an OpenAI-compatible API. The model receives a bounded repository profile, diff, and GPU-ranked context. Repository data is explicitly separated as untrusted content.

The Dell GPU worker creates deterministic hashed vectors and performs cosine ranking with CuPy on CUDA. The response records the accelerator and device. The backend falls back to the same algorithm on CPU when the worker cannot be reached.

Docker sandboxes build separate base and head images, inject the identical generated test, and execute without runtime network access. The comparison engine—not the model—assigns the result classification.

## Data flow

```text
Pull request URL
  → validate canonical GitHub URL
  → fetch PR metadata
  → clone and fetch exact commits
  → detect repository/test profile
  → compute diff and changed files
  → build impact graph
  → rank context on CUDA
  → ask Nemotron for structured hypotheses and tests
  → validate generated path and command policy
  → execute base sandbox
  → execute head sandbox
  → classify result matrix
  → persist evidence
  → render proof card and findings
```

## Failure semantics

Missing model credentials produce `ANALYSIS_ONLY` behavior through the heuristic fallback. Missing or unsupported test commands produce skipped execution evidence. GitHub, install, build, or executor failures become `ENVIRONMENT_ERROR`. No stage silently upgrades incomplete evidence to a verified status.
