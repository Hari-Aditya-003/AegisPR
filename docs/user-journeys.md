# AegisPR User Journeys

## Verify a pull request

As a developer, I want to paste a public GitHub pull request URL so that AegisPR can analyze the change, generate targeted tests, run them against the base and pull request commits, and return evidence showing whether the pull request introduced a regression.

Acceptance criteria:

- Only public `https://github.com/{owner}/{repository}/pull/{number}` URLs are accepted.
- The run exposes live stage progress and never labels an unexecuted claim as verified.
- A test that passes on base and fails on the pull request is classified as a regression.
- A test that fails on both branches is classified as pre-existing or invalid, not as a new regression.
- Environment failures remain visible and downgrade the final status.

## Understand the evidence

As a reviewer, I want a proof card, impact graph, generated test, branch-by-branch logs, and root-cause location so that I can audit the conclusion without trusting the model blindly.

Acceptance criteria:

- Every finding references commits, a hypothesis, a generated test, and both execution results.
- The UI uses `VERIFIED_WITHIN_SCOPE`, `REGRESSION_FOUND`, `FIX_VERIFIED`, `PRE_EXISTING_FAILURE`, `INCONCLUSIVE`, `ENVIRONMENT_ERROR`, or `ANALYSIS_ONLY`.
- The product never displays “100% safe.”

## Verify a repair

As a developer, I want AegisPR to propose a minimal patch and re-run existing and generated tests so that a repair is marked verified only when executable checks pass.

Acceptance criteria:

- Generated patches remain in an isolated workspace until explicitly copied.
- Existing tests, generated tests, build, and type or lint checks are recorded separately.
- Failed repair checks do not produce `FIX_VERIFIED`.

## Use GPU-assisted context selection

As a hackathon judge, I want to see a real NVIDIA GPU workload so that the project demonstrates GPU acceleration beyond a decorative badge.

Acceptance criteria:

- The Dell RTX GPU worker ranks repository context for the Nemotron planning request.
- The worker reports CUDA device metadata and whether each ranking used GPU or CPU fallback.
- Nemotron inference uses Nebius Token Factory with an NVIDIA model; GPU worker failure degrades gracefully to deterministic CPU ranking.

