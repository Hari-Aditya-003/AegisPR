# Security Model

Repository code, pull request text, generated tests, and model output are untrusted.

## Controls

- Only canonical HTTPS GitHub pull request URLs are accepted.
- The clone host is derived from the validated owner and repository.
- Secrets remain server-side environment variables and are never copied into sandboxes or prompts.
- Generated paths reject absolute paths and traversal.
- Descriptor-relative, no-follow writes reject symlinked parents and refuse to overwrite existing generated-test files. Trusted Dockerfiles and repair patches live outside repository-controlled paths.
- Git subprocesses have a small environment allowlist, no inherited application credentials/global config, HTTPS-only transport, disabled hooks and no recursive submodules. Full commit SHAs and canonical remotes are required.
- Repairs cannot rename, copy, change file modes, modify Git metadata, or expand scope through model-provided affected-file suggestions.
- Test commands must match a narrow allowlist derived from detected project commands.
- Runtime sandboxes use no network, no added capabilities, no new privileges, resource limits, process limits, and a read-only root filesystem.
- A bounded 512 MiB ephemeral tmpfs worktree allows build output without writable host mounts; setup/capacity errors are executor errors, not test failures. Unsupported or ignored generated targets are skipped/inconclusive. `.dockerignore` projects are currently unsupported for generated verification.
- Generated checks directly target pytest/Jest/Vitest instead of trusting arbitrary npm scripts to collect the generated test. Unknown runners are skipped.
- Docker build/run CLI output is drained with a 1 MiB combined limit and a retained tail; timeouts clean up named runtime containers and attempted images. Resource cleanup failures are logged.
- API responses do not return provider credentials or internal stack traces.
- Production `/api/*` requires a separate constant-time-compared private deployment token and fails closed if it is missing. Create and repair routes are rate-limited. Browser storage contains only a tab-session access code, never the provider key.
- Inference admission has a durable estimate/call ledger, bounded context/output, exact caching and zero automatic SDK retries. This is not a provider billing guarantee; see [credit controls](model-budget.md).
- Frontend and backend set defensive browser headers and exact CORS origins.
- CI scans dependencies and rejects obvious committed secret assignments.

## Dependency maintenance — October 21, 2026

The UI refresh CI audit flagged the existing Vite 8.3.2 development dependency for launch-editor advisories ([upstream advisory](https://github.com/advisories/GHSA-r825-w8mm-5pxw)). The exact pin is now 8.3.5 with its regenerated lockfile. No application dependencies or audit thresholds were weakened. After the update, `npm audit --audit-level=high` reported zero vulnerabilities; all 32 frontend unit tests, TypeScript checking and the production build passed locally. The local Node 25 runtime emitted Vitest's unsupported-engine warning; CI uses supported Node 22 and must be checked separately. This dependency audit is not proof that the application has no security vulnerabilities.

On October 23 a new local audit identified critical [Next.js image-processing](https://github.com/advisories/GHSA-2464-fhr4-w9xw) and [`use cache` typed-array](https://github.com/advisories/GHSA-673q-mjm6-r5xr) advisories, plus a high-severity [Server Actions DoS](https://github.com/advisories/GHSA-p3m5-59mp-jv5r) advisory, affecting the prior Next.js 16.3.8 pin. The exact pin and lockfile were moved to 16.4.2, beyond the advisory-patched 16.4.1 release. A fresh local `npm ci`, full `npm audit --audit-level=high`, 33 frontend tests, TypeScript check and production build passed with zero reported npm vulnerabilities. CI uses Node 22; the local Node 25 Vitest engine warning is unrelated to the audited advisory and is not a CI result. GitHub Dependabot alerts were disabled at the time of this audit, so that service did not provide an independent alert list.

## Docker socket boundary

The deployed orchestrator talks to the host Docker daemon to create nested execution sandboxes. Docker socket access is effectively host-level privilege and must remain limited to the orchestrator container and trusted administrators. Generated repository code never receives the socket. For production isolation, replace this with a remote ephemeral executor or Nebius sandbox service.

## Network policy

Dependency installation happens during image build and therefore has outbound access. Actual test execution uses `--network=none`. Production deployments should add an allowlisted package mirror and image-signature verification.

## Remaining boundaries

This MVP is a private, trusted-operator deployment, not a hardened public arbitrary-code service. Docker socket access remains host-level privilege; build-time dependencies can execute untrusted code (npm lifecycle scripts are disabled, but Python package builds can execute). Runtime resource limits do not enforce build daemon quotas, repository disk quotas, or Git output bounds. Malicious repository configuration/test plugins may manipulate their own test runner and therefore the meaning of an exit code. Output differences now receive two reruns per commit, but assertion-based failures do not yet receive that flakiness filter. Before a public multi-user executor, use a remote ephemeral executor, bounded Git/repository admission, build/disk quotas, a job queue/concurrency limits, and a trusted collection harness. No audit proves the absence of all vulnerabilities.
