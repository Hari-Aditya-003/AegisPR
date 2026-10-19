# AegisPR Operations Runbook

## Service inventory

| Service | Port | Health check | Persistent data |
| --- | --- | --- | --- |
| Frontend | `3000` | `GET /` | none |
| Backend | `8000` | `GET /health` | `aegis-data` SQLite volume |
| GPU worker | host loopback `8091` | `GET /health` | none |

The backend also uses `aegis-runs` for temporary repository workspaces. Successful and failed orchestrations remove their per-run directories.

## Start and stop

```bash
docker compose up --build -d
docker compose ps
docker compose down
```

Avoid `docker compose down -v` during routine operations because it removes persisted run history.

It also removes the inference budget ledger and response cache. Back up both `aegispr.sqlite3` and `inference-budget.sqlite3`; never delete the latter as a way to bypass spending limits. Generate separate random `API_ACCESS_TOKEN` and `GPU_WORKER_TOKEN` values in the protected remote `.env` before deploying. Enter only the API access code in the frontend private deployment control, never the Nebius key. All `/api/*` endpoints require `Authorization: Bearer <API_ACCESS_TOKEN>` in production. Health remains accessible without a code and proves configuration, not successful inference.

Default paid admission estimates are $20 total, $0.25 per run including repairs, and five attempts per run. `/api/budget` returns authenticated estimates, not a provider balance. See [credit controls](model-budget.md) and reconcile Nebius billing before changing limits. Set `INFERENCE_BUDGET_USD=0` to block new paid calls while preserving cache use and recorded evidence.

## Health verification

```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8091/health
curl -fsS http://127.0.0.1:3000/
```

Expected production backend checks:

```json
{
  "status": "ok",
  "checks": {
    "nebius": "configured",
    "gpu_worker": "ok",
    "sandbox": "enabled"
  }
}
```

Expected GPU field for the live hackathon demo:

```json
{
  "accelerator": "cuda"
}
```

## Logs

```bash
docker compose logs --tail=200 backend
docker compose logs --tail=200 gpu-worker
docker compose logs --tail=200 frontend
docker compose logs -f backend gpu-worker
```

Do not paste logs publicly until they have been checked for repository content, PR data, URLs, and infrastructure details.

## Dell deployment

```bash
./scripts/gpu-smoke-test.sh
./scripts/deploy-dell.sh
```

Overrides:

```bash
AEGIS_REMOTE_HOST=user@host AEGIS_REMOTE_PATH=/srv/aegispr ./scripts/deploy-dell.sh
```

The remote `.env` is intentionally preserved and must be managed separately.

If port 8000 is occupied, set `BACKEND_PORT=8080` and change `PUBLIC_API_URL`
to the Dell's reachable URL on port 8080. Rebuild the frontend because its API
URL is embedded at build time. Container-to-container traffic still uses port
8000. The current Dell installation uses this port-8080 configuration.

## Nebius preflight

From a trusted environment with the API key loaded, query the Token Factory model catalog and confirm the configured `NEBIUS_MODEL` is present. Do not print or record the key. Restart the backend after changing model configuration.

Model IDs are case-sensitive. The live catalog returned
`nvidia/Nemotron-3_5-Lightning` and `nvidia/Nemotron-3-Ultra-550b-a55b`. Lightning is now the economical default, pending quality evaluation. A model-list success proves authentication,
not inference readiness. HTTP 402 from a completion means usable credits are
unavailable; ask Token Factory support to check the project billing/credit
status. Backend health reports credential presence only and must not be used
as proof of a successful live model call.

## CUDA preflight

If `nvidia-smi` reports NVML driver/library mismatch, do not claim GPU readiness or unload modules/reboot automatically. Check `/proc/driver/nvidia/version` against installed NVIDIA library versions. On October 18, loaded `595.91.07` differed from installed `595.99.02`; the app was temporarily restored with `docker compose -f docker-compose.yml -f docker-compose.cpu.yml up -d`. On October 19, host recovery was detected, matching driver `595.99.02` was checked, normal GPU Compose restored and authenticated CUDA ranking reverified. See the [dated receipt](gpu-recovery-2026-10-19.md). For any recurrence, an administrator must arrange safe host recovery after saving other work. Only once host `nvidia-smi` works should normal GPU Compose be restored; rerun the smoke test and require `gpu_accelerator: cuda` before recording.

For no-credit acceptance without touching production services, use the separate [credential-free judging build](judge-test-build.md), not a production `.env` or a public Docker-socket API.

```bash
nvidia-smi
docker run --rm --gpus all nvidia/cuda:12.8.1-base-ubuntu24.04 nvidia-smi
docker compose exec gpu-worker python3 -c "import cupy as cp; print(cp.cuda.runtime.getDeviceProperties(0)['name']); print(cp.arange(1000000).sum())"
```

## Release procedure

1. Confirm the worktree contains only intended changes.
2. Run `make test`.
3. Run `git diff --check`.
4. Review configuration and documentation changes.
5. Commit and push to `main` through the normal repository workflow.
6. Wait for all GitHub Actions jobs to pass.
7. Run the Dell GPU smoke test.
8. Deploy with `scripts/deploy-dell.sh`.
9. Verify all three services and confirm CUDA in worker health.
10. Run one real public PR and inspect its complete evidence.

## Rollback

1. Identify the last known-good Git commit.
2. Check out that commit in a separate safe release worktree or deploy its archived source.
3. Synchronize it to the Dell without replacing `.env`.
4. Rebuild and restart Compose.
5. Verify health endpoints and one known PR workflow.

Do not use destructive Git resets on a working directory containing uncommitted work.

## SQLite backup

Create a consistent backup through SQLite inside the backend container:

```bash
docker compose exec backend python -c "import sqlite3; source=sqlite3.connect('/app/data/aegispr.sqlite3'); target=sqlite3.connect('/app/data/aegispr-backup.sqlite3'); source.backup(target); target.close(); source.close()"
```

Copy the backup from the named volume only through an administrator-approved process. Verification records may contain repository snippets and logs; protect them accordingly.

## Incident triage

### Backend unavailable

1. `docker compose ps`
2. `docker compose logs --tail=200 backend`
3. Verify the `.env` requirements and Docker socket group.
4. Verify the SQLite volume is writable.
5. Recreate only the backend after correcting configuration.

### GPU worker unavailable or CPU-only

1. Run host `nvidia-smi`.
2. Run the CUDA container smoke test.
3. Inspect `gpu-worker` logs.
4. Confirm backend and worker use the same `GPU_WORKER_TOKEN`.
5. Rebuild the worker image.
6. Do not describe a run as GPU-accelerated when the response reports CPU.

### Nebius errors

1. Confirm server-side key presence without printing it.
2. Confirm model availability from `/v1/models`.
3. Confirm outbound HTTPS and system time.
4. Check bounded backend logs for provider status.
5. Allow the run to remain `ANALYSIS_ONLY` or `ENVIRONMENT_ERROR`; do not alter evidence manually.

### Docker sandbox errors

1. Check Docker daemon availability.
2. Confirm `DOCKER_GID` matches `/var/run/docker.sock` group ownership.
3. Inspect bounded build/test logs in the finding.
4. Confirm the repository uses a supported runtime and test command.
5. Confirm package registries were reachable during image build.

### Tailscale/SSH unavailable

1. Power on and unlock the Dell if needed.
2. Confirm both devices are connected to the same tailnet.
3. Verify MagicDNS or SSH configuration.
4. Test `ssh -o BatchMode=yes -o ConnectTimeout=8 dell-ts hostname`.
5. Use `AEGIS_REMOTE_HOST` only after confirming the intended host identity.

## Security escalation

Stop new verifications and rotate affected credentials if:

- an API key or worker token appears in Git, logs, screenshots, or video;
- a sandbox obtains network or Docker socket access;
- a generated patch changes out-of-scope files;
- the public API is being abused;
- persisted evidence is exposed to an unauthorized party.

After containment, preserve relevant logs, document the incident, and verify the corrected boundary with an automated regression test.

