# Seeded PR evaluation dataset

The source dataset is [`cases.json`](cases.json). It contains **12 hand-authored, synthetic PR-like code pairs**: eight unintended behavior changes, three changes intentionally described by their PR text, and one behavior-preserving refactor. Python and JavaScript cases cover off-by-one, boundary, null-handling, rounding and deterministic lost-update scenarios. Each row includes base/head source, input arguments, expected observations, a title, description and a human-provided intent label.

These are **fixture ground-truth labels**, not Nemotron predictions or AegisPR detection results. No real merged PRs, provider calls, tokens, cloud costs, detection rate or false-positive rate are represented by this dataset.

From the repository root, validate the expected outputs without a provider key:

```bash
PYTHONPATH=backend backend/.venv/bin/python -m app.evaluation.seeded_dataset validate
```

To make 12 local, two-commit Git repositories for later PR-style evaluation, choose a **new** output directory:

```bash
PYTHONPATH=backend backend/.venv/bin/python -m app.evaluation.seeded_dataset materialize --output /tmp/aegispr-seeded-prs
```

The command refuses to overwrite an existing directory. It writes `/tmp/aegispr-seeded-prs/index.json` with each base/head SHA and hand label; each sibling directory named after a case is an independent local Git repository with no remote. Labels are outside those repositories so a model reading a case checkout does not see the answer. Git commit dates are fixed for reproducible fixtures. This command **does not** publish repositories or create GitHub pull requests.

The validator executes only the reviewed fixture source committed here in a temporary local directory. It is **not** the hardened Docker sandbox for untrusted model-generated code. Do not pass unreviewed case files to it. A future live benchmark must separately record exact public PR URLs and SHAs, human adjudication, provider receipts, wall-clock timing, model version and every failed/inconclusive run. Do not derive a model score from the fixture labels alone.
