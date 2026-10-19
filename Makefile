.PHONY: test test-backend test-frontend test-e2e test-gpu test-demo test-website build up down gpu-check

PYTEST ?= backend/.venv/bin/pytest

test: test-backend test-frontend test-gpu test-demo test-e2e test-website

test-backend:
	cd backend && $(abspath $(PYTEST))

test-frontend:
	cd frontend && npm run test:coverage && npm run demo:test && npm run typecheck && npm run build && npm audit --audit-level=high

test-e2e:
	cd frontend && npm run e2e

test-gpu:
	PYTHONPATH=gpu-worker $(PYTEST) --no-cov -q gpu-worker/tests

test-demo:
	cd demo-repositories/demo-store && PYTHONPATH=. $(abspath $(PYTEST)) --no-cov -q

test-website:
	node --test website/tests/*.test.mjs

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

gpu-check:
	docker compose exec gpu-worker python3 -c "import cupy as cp; print(cp.cuda.runtime.getDeviceProperties(0)['name']); print(cp.arange(1000000).sum())"
