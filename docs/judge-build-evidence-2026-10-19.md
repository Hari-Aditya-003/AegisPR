# October 19 full-stack controlled acceptance

Observed on the Linux Dell on October 19, 2026 (Asia/Kolkata), using the standalone `aegispr-judge` Compose project. Backend and frontend both reported healthy on loopback ports `18080` and `3300`. Production services, credentials and volumes were not reused.

This is actual Docker execution of **prewritten controlled fixtures**, not successful NVIDIA/Nebius inference, a real GitHub PR review, model-generated tests or an AI-generated repair. The local Git commits were created by the fixture runner. The persisted reports explicitly record `evidence_mode: controlled_fixture`, `model_used: controlled-fixture-no-model`, zero model calls/tokens and no context acceleration.

## Actual receipts

| Language | Report ID | Base | Deliberately broken head | Manual repair |
| --- | --- | --- | --- | --- |
| Python / pytest | `8fbe82b9-ba35-488d-9bcc-54b89fb2ea1c` | PASS | FAIL | Existing and boundary tests PASS; build/lint unconfigured and SKIPPED |
| JavaScript / Vitest | `caac6c13-5643-4847-8ea3-81889b921529` | PASS | FAIL | Existing tests, boundary test and configured build PASS; lint unconfigured and SKIPPED |

Both records reached `FIX_VERIFIED` after their required repair checks passed. The same oversized-discount assertion, `coupon(10,20) == 0`, was executed against each fixture's actual base and head.

Python commits:

```text
base b0f23bc003f8147fcc1a880d4621c387eef4c033
head 63475b43c00ba63af1d0950de8f73b10d91c5de4
```

The targeted command was `python -m pytest -q -- test_generated.py`; the manually repaired existing suite used `pytest -q`.

JavaScript commits:

```text
base f26d3ce83439b577b363e946b829dd89fc5656c2
head afc1c482594fb9ebc81f4ece9405a3124f554720
```

The targeted command was `./node_modules/.bin/vitest run --maxWorkers=1 --passWithNoTests=false generated.test.js`. Manual repair also required `npm test -- --run` and `npm run build`.

Fresh reruns intentionally produce new report IDs and may produce different local Git SHAs. Use the records printed by your run, not these historical IDs, when opening your local app.

## Access, budget and startup observation

The actual judge API returned 401 without authentication and 200 for the authenticated budget request. Its persistent ledger reported `limit_usd: 0`, `calls: 0`, zero tokens and zero estimated dollars. Credentials are not included in this receipt or the exported JSON artifact.

The first real startup caught a permissions issue not established by subprocess mocks: source extracted with restrictive permissions was copied as root, so the non-root runtime user could not import `/app/app/__init__.py`. A regression test was added before changing the Dockerfile to copy application source with `--chown=aegis:aegis`. The rebuilt container started successfully without widening source permissions, and both acceptance fixtures then completed.

The standard local quality matrix passed **203 tests**: 149 backend, 32 frontend, seven mocked-API Chromium journeys, eight website, six CPU-worker and one seeded repository test. Backend line coverage was 90.71%; frontend statement coverage was 95.54%. Type checking, production build and npm audit passed. Separate no-mock browser inspection and CI results must be read from the current release evidence, not inferred from that mocked browser matrix.

## Reproduce and inspect

Follow [the judging build guide](judge-test-build.md). `bash scripts/judge-test-build.sh export` copies only receipt JSON files. The CI job additionally uploads `controlled-fixture-evidence` for its own run. No access code, provider key or private database is intended for those artifacts.

Real CUDA recovery is a separate [GPU receipt](gpu-recovery-2026-10-19.md). Live Nebius inference, actual public PR acceptance, measured model feedback and the final submission video remain open gates.
