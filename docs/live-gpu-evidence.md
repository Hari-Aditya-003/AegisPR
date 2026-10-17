# Live Dell GPU Verification Evidence

Verification date: October 17, 2026  
Host: `hari-Dell-G15-5510` over the configured Tailscale SSH connection

## Host preflight

| Check | Observed result |
| --- | --- |
| Operating system | Ubuntu Linux, kernel `7.0.0-34-generic` |
| GPU | NVIDIA GeForce RTX 3050 Ti Laptop GPU |
| Driver | `595.91.07` |
| GPU memory | 4096 MiB |
| Docker | `29.1.3` |
| Docker Compose | `2.40.3` |
| Docker socket GID | `125` |

## Container runtime proof

The project smoke test ran `nvidia-smi` inside `nvidia/cuda:12.8.1-base-ubuntu24.04` with `--gpus all` and observed:

```text
NVIDIA GeForce RTX 3050 Ti Laptop GPU, 595.91.07, 4096 MiB
```

## Application workload proof

The production `gpu-worker` image was built and started with the Compose security controls, including a read-only root filesystem and writable `/tmp` tmpfs. Its health endpoint returned:

```json
{
  "status": "ok",
  "accelerator": "cuda",
  "device": "NVIDIA GeForce RTX 3050 Ti Laptop GPU",
  "workload": "hashed term-document cosine ranking"
}
```

An authenticated `/rank` request executed the actual CuPy hashed-vector and cosine-ranking path. It returned:

```json
{
  "documents": [
    {
      "path": "cart.py",
      "content": "coupon discount cart total",
      "changed": true,
      "score": 1.2500000298023224
    }
  ],
  "accelerator": "cuda",
  "device": "NVIDIA GeForce RTX 3050 Ti Laptop GPU"
}
```

This proves that the AegisPR application workload—not only a generic CUDA sample—executed on the Dell NVIDIA GPU.

## Production issues found and repaired

Physical-GPU validation exposed two constraints that CPU CI could not reproduce:

1. CuPy attempted to write its compiled-kernel cache beneath the non-root user's home directory, which is unavailable under the read-only root filesystem. `CUPY_CACHE_DIR` now targets the existing `/tmp` tmpfs.
2. CuPy JIT compilation requires CUDA headers such as `cuda_fp16.h`. The worker now uses the matching `nvidia/cuda:12.8.1-devel-ubuntu24.04` image.

Both fixes were implemented with RED/GREEN container-contract tests. The worker test suite now contains six passing tests.

## Remaining live-stack dependency

The remote source, production images, secure worker token, correct Docker socket group, and CUDA worker are prepared. The complete backend/frontend stack still requires a real `NEBIUS_API_KEY` in `/home/hari/aegispr/.env`. No key was available locally, in the remote shell, in the target directory, or in an existing AegisPR container, so no placeholder was persisted and no model-success claim has been made.

