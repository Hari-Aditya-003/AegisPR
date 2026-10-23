# Local verification for coding agents and developers

`aegispr verify` is a token-free, pre-push review of **committed** changes. It is a separate entry point from the hosted pull-request workflow. It does not claim to prove a change correct. The default static mode reads Git objects without running repository code; it reports selected public API signature changes and removed auth/validation guard patterns for human review.

Install with Python 3.12 or newer:

```bash
python3.12 -m pip install -e backend
aegispr verify --repo /path/to/project --base origin/main --json
```

For a Git pre-push hook, place the following in that repository's `.git/hooks/pre-push` and make it executable. This is **opt-in**; AegisPR never installs hooks automatically. Set the base ref to the branch your team actually reviews against. A missing base, uncommitted changes or untracked files stop the check with exit code 2.

```sh
#!/bin/sh
aegispr verify --repo "$(git rev-parse --show-toplevel)" --base origin/main
```

The exit code is `0` when no selected issue is observed, `1` when review is needed, and `2` when verification could not produce reliable evidence. Coding agents can call the same CLI before opening a PR and inspect the JSON. The scanner recognizes top-level/public Python functions and methods plus simple named `export function` JavaScript/TypeScript declarations. It is not a complete language parser or compatibility checker. A warning is a lead for review, not a confirmed vulnerability or breaking change; silence is not a clean bill of health.

## Optional existing-test comparison

```bash
aegispr verify --repo /path/to/project --base origin/main --docker-tests --json
```

This builds separate Docker images for base and head, runs the same detected allowlisted existing test suite three times on each commit, and compares exit statuses. Only three base passes followed by three head failures become `reproducible_regression`. Mixed outcomes are inconclusive. When both pass, median wall time and cgroup peak memory can flag a **possible** 30% regression if samples are stable. Timing includes container startup; three samples are only a screening signal, not a controlled benchmark. Build-time dependency installation has network access and can execute untrusted Python package build code; runtime tests have no network and use the project's existing sandbox limits. Use only on repositories you are authorized to execute.

This mode makes **zero** model calls. It does not generate new tests or add package dependencies. Hypothesis and fast-check are requested in the hosted planner only if the repository already declares them; that conditional prompt has not yet been validated against live generated plans.

## GPU numerical comparison

`aegispr compare-gpu` compares **caller-supplied** JSON captured by the same kernel harness at the base and head revisions:

```bash
aegispr compare-gpu --base base-gpu.json --head head-gpu.json --json
```

Each file has this bounded shape (one to 100 cases, up to 10,000 finite output values per case, three to five positive latency samples):

```json
{
  "device": {"backend": "cuda", "name": "NVIDIA example GPU"},
  "outputs": {"vector_add": [1.0, 2.0]},
  "latency_ms": {"vector_add": [1.1, 1.0, 1.1]}
}
```

The command requires identical device metadata and case names, compares numerical results using `1e-5` absolute and `1e-4` relative tolerance, and screens latency with the same repeated-median rule. A value difference or possible slowdown returns exit code 1. Invalid/incomparable artifacts return 2. It does not execute kernels, attest the device, provision Nebius infrastructure, or prove the JSON came from a GPU. Record exact commits, harness, driver, device, and raw run logs separately. The Dell's dated CUDA ranking evidence is not a Nebius GPU-kernel verification run.

## Current limits

- No MCP server is exposed. Agents use the CLI/JSON interface; an MCP adapter is a future integration.
- Security checks are narrow heuristics. They do not replace a security review or adversarial tests.
- The optional Docker mode requires a running daemon. It was unit-tested with a fake executor on the local Mac because Docker was unavailable during this change; CI has a separate real Docker fixture build, not a real run of this new CLI.
- No automated Nebius GPU base/head runner or public real-PR benchmark has been verified. Do not describe the GPU JSON comparator as either one.
