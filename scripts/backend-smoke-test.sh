#!/usr/bin/env bash
set -euo pipefail

# Run from the project root on the deployment host. This verifies the actual
# production image and Docker socket permissions, without printing secrets.
docker compose run --rm --no-deps -T backend sh -ec '
  git --version
  docker version --format "client={{.Client.Version}} server={{.Server.Version}}"
'
