# Security Model

Repository code, pull request text, generated tests, and model output are untrusted.

## Controls

- Only canonical HTTPS GitHub pull request URLs are accepted.
- The clone host is derived from the validated owner and repository.
- Secrets remain server-side environment variables and are never copied into sandboxes or prompts.
- Generated paths reject absolute paths and traversal.
- Test commands must match a narrow allowlist derived from detected project commands.
- Runtime sandboxes use no network, no added capabilities, no new privileges, resource limits, process limits, and a read-only root filesystem.
- API responses do not return provider credentials or internal stack traces.
- The public create endpoint is rate-limited.
- Frontend and backend set defensive browser headers and exact CORS origins.
- CI scans dependencies and rejects obvious committed secret assignments.

## Docker socket boundary

The deployed orchestrator talks to the host Docker daemon to create nested execution sandboxes. Docker socket access is effectively host-level privilege and must remain limited to the orchestrator container and trusted administrators. Generated repository code never receives the socket. For production isolation, replace this with a remote ephemeral executor or Nebius sandbox service.

## Network policy

Dependency installation happens during image build and therefore has outbound access. Actual test execution uses `--network=none`. Production deployments should add an allowlisted package mirror and image-signature verification.
