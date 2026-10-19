# October 19 CUDA recovery receipt

Observed October 19, 2026 (Asia/Kolkata). This supersedes the current-state GPU blocker in the October 18 hardening receipt; it does not replace that historical incident record.

## Host and application checks

The existing Dell was reachable through Tailscale. Its MagicDNS hostname did not resolve from the development machine, so the connection used the verified peer address while retaining the existing SSH host-key alias and strict host-key checking. No global DNS changes or host-key bypass were used.

Host `nvidia-smi` now succeeds:

```text
NVIDIA GeForce RTX 3050 Ti Laptop GPU, 595.99.02, 4096 MiB
```

The loaded kernel module and installed driver now agree at `595.99.02`. No reboot, driver replacement, or module unload was initiated by this continuation. After the read-only preflight succeeded, the normal GPU Compose configuration was restored for the AegisPR services only:

```bash
cd /home/hari/aegispr
docker compose config --quiet
docker compose up -d gpu-worker backend frontend
docker compose ps
```

All three services reported healthy. Unrelated host services were not changed. CuPy inside the GPU worker reported the RTX 3050 Ti and evaluated `cp.arange(1000000).sum()` as `499999500000`.

An authenticated call from the backend to the internal worker's `/rank` endpoint returned `accelerator: cuda` and the RTX device. For a coupon-boundary query, `coupon.py` ranked first with score `1.8333333`; the unrelated README scored zero. The worker token was consumed from the existing server environment, not printed or exported into this document.

Backend `/health` returned:

```json
{"status":"ok","checks":{"nebius":"configured","gpu_worker":"ok","gpu_accelerator":"cuda","sandbox":"enabled"}}
```

## What this proves, and what it does not

This is current physical CUDA and authenticated application-ranking evidence on the local Dell, not a Nebius cloud GPU instance or a measured ranking speedup. Health's `nebius: configured` means credential presence, not working inference or a confirmed provider balance.

The authenticated application budget ledger still reported zero calls, zero tokens and zero estimated dollars, with the existing $20 total / $0.25 per-run admission estimates. No paid inference was attempted. Usable Nebius credits, a successful real model response, an actual PR acceptance run and the submission recording remain unverified completion gates.

If the host driver fails again, follow the [runbook](RUNBOOK.md#cuda-preflight); never present these dated observations as a guarantee of future readiness.
