#!/usr/bin/env bash
set -euo pipefail
umask 077

# This separate, loopback-only stack never receives production credentials.
unset NEBIUS_API_KEY GITHUB_TOKEN GPU_WORKER_TOKEN API_ACCESS_TOKEN
judge_action="${1:-start}"
case "$judge_action" in
  start|verify|status|stop) ;;
  *) echo "Usage: bash scripts/judge-test-build.sh [start|verify|status|stop]" >&2; exit 2 ;;
esac
judge_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
judge_state="$judge_root/artifacts/judge"
judge_code="$judge_state/access-code"
if [[ -L "$judge_root/artifacts" || -L "$judge_state" || -L "$judge_code" ]]; then
  echo "Refusing a symlinked private judge state/code path." >&2
  exit 1
fi
if [[ "$judge_action" == start ]]; then
  command -v docker >/dev/null || { echo "Docker is required." >&2; exit 1; }
  command -v openssl >/dev/null || { echo "OpenSSL is required to generate a private local code." >&2; exit 1; }
  docker info --format '{{.ServerVersion}}' >/dev/null
  mkdir -p "$judge_state"
  if [[ ! -f "$judge_code" ]]; then
    (set -o noclobber; openssl rand -hex 32 > "$judge_code")
  fi
fi
if [[ ! -f "$judge_code" ]]; then
  echo "Judge build is not initialized. Run start first." >&2
  exit 1
fi
IFS= read -r JUDGE_ACCESS_TOKEN < "$judge_code"
if [[ ! "$JUDGE_ACCESS_TOKEN" =~ ^[a-f0-9]{64}$ ]]; then
  echo "The local judge access code is invalid; preserve the file and inspect it privately." >&2
  exit 1
fi
chmod 600 "$judge_code"
export JUDGE_ACCESS_TOKEN
if [[ -S /var/run/docker.sock ]]; then
  JUDGE_DOCKER_GID="$(stat -c '%g' /var/run/docker.sock 2>/dev/null || stat -f '%g' /var/run/docker.sock)"
else
  JUDGE_DOCKER_GID=0
fi
export JUDGE_DOCKER_GID
judge_compose=(docker compose -p aegispr-judge -f "$judge_root/docker-compose.judge.yml")
cd "$judge_root"
case "$judge_action" in
  start)
    "${judge_compose[@]}" config --quiet
    "${judge_compose[@]}" build
    "${judge_compose[@]}" up -d --wait --wait-timeout 120
    "${judge_compose[@]}" exec -T backend python -m app.services.fixture_acceptance --language all
    ;;
  verify)
    "${judge_compose[@]}" exec -T backend python -m app.services.fixture_acceptance --language all
    ;;
  status) "${judge_compose[@]}" ps ;;
  stop) "${judge_compose[@]}" down ;;
esac
if [[ "$judge_action" == start || "$judge_action" == verify ]]; then
  echo "Controlled fixture build: no model calls or live GitHub PR analysis."
  echo "Open the report URLs above, then save the code from this private local file in the app:"
  echo "$judge_code"
  echo "No provider key or GPU is required. Docker image/dependency downloads require internet."
fi
