.PHONY: test test-backend test-frontend test-e2e test-gpu test-demo build up down gpu-check

test: test-backend test-frontend test-gpu test-demo test-e2e

test-backend:
	cd backend && .venv/bin/pytest

test-frontend:
	cd frontend && npm run test:coverage && npm run typecheck && npm run build && npm audit --audit-level=high

test-e2e:
	cd frontend && npm run e2e

test-gpu:
	PYTHONPATH=gpu-worker backend/.venv/bin/pytest -q gpu-worker/tests

test-demo:
	cd demo-repositories/demo-store && PYTHONPATH=. ../../backend/.venv/bin/pytest -q

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

gpu-check:
	docker compose exec gpu-worker python3 -c "import cupy as cp; print(cp.cuda.runtime.getDeviceProperties(0)['name']); print(cp.arange(1000000).sum())"
