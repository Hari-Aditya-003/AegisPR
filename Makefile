.PHONY: test test-backend test-frontend build up down gpu-check

test: test-backend test-frontend

test-backend:
	cd backend && .venv/bin/pytest

test-frontend:
	cd frontend && npm run test:coverage && npm run typecheck

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

gpu-check:
	docker compose exec gpu-worker python3 -c "import cupy as cp; print(cp.cuda.runtime.getDeviceProperties(0)['name']); print(cp.arange(1000000).sum())"
