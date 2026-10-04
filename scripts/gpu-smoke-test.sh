#!/usr/bin/env bash
set -euo pipefail

remote_host="${AEGIS_REMOTE_HOST:-dell-ts}"

ssh "$remote_host" 'docker run --rm --gpus all nvidia/cuda:12.8.1-base-ubuntu24.04 nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader'
