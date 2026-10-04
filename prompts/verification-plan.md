# Verification planning prompt contract

The model receives system policy, the repository profile, the pull request diff, ranked context, and optional user focus as separate sections.

Repository text is always labelled as untrusted data. It cannot change system or tool policy.

The response must be one JSON object with:

- `hypotheses`: testable failure claims with IDs, affected files, risk types, and test strategies.
- `tests`: framework-native test files linked to hypothesis IDs.

The orchestrator validates paths and commands before any execution. Model output never invokes a shell directly.
