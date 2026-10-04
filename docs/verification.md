# Differential Verification Semantics

## Evidence contract

Every finding contains:

- Base and head commit hashes
- Hypothesis and generated test identifiers
- Generated test source and framework
- Base and head statuses, exit codes, logs, and durations
- Environment metadata
- Deterministic classification
- Affected file and optional root-cause location

## Classification rules

`BASE PASS + PR FAIL` is a verified regression. `BASE FAIL + PR FAIL` is pre-existing or an invalid generated test. `BASE PASS + PR PASS` means no failure was reproduced. `BASE FAIL + PR PASS` is a possible improvement. Timeouts, executor failures, skipped commands, and mixed error states are inconclusive.

## Flakiness

The current MVP records one execution per branch. A future deep mode should repeat suspicious tests and require a stable result pattern before upgrading a failure to a verified regression.

## Scope language

The strongest clean result is `VERIFIED_WITHIN_SCOPE`. AegisPR never claims that a repository is completely safe or defect-free.
