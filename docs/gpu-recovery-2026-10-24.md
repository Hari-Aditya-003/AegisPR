# October 24, 2026 — Dell CUDA recovery receipt

This is a dated observation of the Dell Linux host and AegisPR production stack. It is **local NVIDIA GPU** evidence, not a Nebius GPU instance, a model-generated PR review, or a measured speedup.

The host had a loaded NVIDIA `595.99.02` open kernel module, but on the initial October 24 check `/usr/bin/nvidia-smi` and `libnvidia-ml.so.1` were absent. An unprivileged Ubuntu package simulation showed that installing the exact-match `libnvidia-compute-595` and `nvidia-utils-595` version `595.99.02-0ubuntu0.26.04.1` would add two packages, with no removals or upgrades. The owner was given the administrator command to run locally; no password was used in automation. A subsequent read-only package query confirmed both packages installed at that version. No reboot or kernel-module unload was performed by AegisPR work.

Fresh checks then recorded:

| Check | Observed result |
| --- | --- |
| Host `nvidia-smi` | `NVIDIA GeForce RTX 3050 Ti Laptop GPU, 595.99.02` |
| AegisPR `gpu-worker` | Restored with `docker compose up -d --no-deps --no-build gpu-worker`; healthy, loopback port `8091` |
| In-container CuPy | Detected the RTX 3050 Ti; `cp.arange(1000000).sum()` returned `499999500000` |
| Authenticated backend-to-worker `/rank` | Returned `accelerator: cuda`, RTX 3050 Ti device, and ranked `coupon.py` before unrelated `README.md` |
| Production backend `/health` | `status: ok`; `gpu_worker: ok`; `gpu_accelerator: cuda`; `sandbox: enabled`; `nebius: configured` |

The `/rank` call used the existing token inside the backend container without printing it. It exercised AegisPR's actual CuPy ranking path; it made **no Token Factory inference request**. Backend health reports configured credential presence, not provider balance or inference success. The separate [October 23 model-only completion](live-nebius-check.md) and this CUDA receipt remain distinct; neither establishes a completed model-generated PR acceptance run.

Current readiness can change with the host. Repeat host, worker and authenticated-ranking checks before filming or claiming live CUDA in a submission.
