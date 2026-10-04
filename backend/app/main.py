from __future__ import annotations

import asyncio

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.agents.orchestrator import Orchestrator
from app.config import get_settings
from app.github.parser import parse_pull_request_url
from app.schemas.verification import CreateVerificationRequest, VerificationStatus
from app.services.store import VerificationStore


settings = get_settings()
store = VerificationStore(settings.data_path)
orchestrator = Orchestrator(settings, store)
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="AegisPR API",
    version="0.1.0",
    description="Evidence-backed differential pull request verification",
    docs_url="/docs" if settings.app_env != "production" else None,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.get("/health")
async def health() -> dict:
    gpu_status = "not_configured"
    if settings.gpu_worker_url:
        headers = (
            {"Authorization": f"Bearer {settings.gpu_worker_token}"}
            if settings.gpu_worker_token
            else {}
        )
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(
                    f"{settings.gpu_worker_url.rstrip('/')}/health", headers=headers
                )
                gpu_status = "ok" if response.is_success else "error"
        except httpx.HTTPError:
            gpu_status = "error"
    checks = {
        "nebius": "configured" if settings.nebius_api_key else "not_configured",
        "gpu_worker": gpu_status,
        "sandbox": "enabled" if settings.enable_sandbox else "disabled",
    }
    degraded = checks["nebius"] != "configured" or (
        settings.gpu_worker_url is not None and gpu_status != "ok"
    )
    return {"status": "degraded" if degraded else "ok", "checks": checks}


@app.post("/api/verifications", status_code=202)
@limiter.limit("5/minute")
async def create_verification(
    request: Request, payload: CreateVerificationRequest, background_tasks: BackgroundTasks
):
    try:
        parse_pull_request_url(payload.pull_request_url)
        run = orchestrator.create(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    background_tasks.add_task(orchestrator.verify, run.id, payload)
    return run


@app.get("/api/verifications")
async def list_verifications(limit: int = 20):
    return store.list(max(1, min(limit, 100)))


@app.get("/api/verifications/{run_id}")
async def get_verification(run_id: str):
    run = store.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Verification run not found")
    return run


@app.get("/api/verifications/{run_id}/findings")
async def get_findings(run_id: str):
    run = store.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Verification run not found")
    return run.findings


@app.get("/api/verifications/{run_id}/impact")
async def get_impact(run_id: str):
    run = store.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Verification run not found")
    return {"nodes": run.impact_nodes, "edges": run.impact_edges}


@app.get("/api/verifications/{run_id}/events")
async def stream_events(run_id: str):
    if not store.get(run_id):
        raise HTTPException(status_code=404, detail="Verification run not found")

    async def events():
        last_payload = ""
        for _ in range(360):
            run = store.get(run_id)
            if not run:
                break
            payload = run.model_dump_json()
            if payload != last_payload:
                yield f"event: verification\ndata: {payload}\n\n"
                last_payload = payload
            if run.status not in {VerificationStatus.QUEUED, VerificationStatus.RUNNING}:
                break
            await asyncio.sleep(1)

    return StreamingResponse(events(), media_type="text/event-stream")

