"""HTTP adapter for explainable risk assessment.

This service returns a risk signal only. It does not authorize, reject, reverse,
refund, settle, or otherwise move money. Tenant history must be scoped by the
trusted caller; this endpoint intentionally accepts only an explicit history
window and does not query a database itself.
"""
from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from .engine import MODEL_VERSION, assess_transaction

app = FastAPI(title="TELIXO Risk Scoring", version="0.1.0", docs_url=None, redoc_url=None)


class AssessRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    transaction: dict[str, Any]
    history: list[dict[str, Any]] = Field(default_factory=list, max_length=500)
    tenant_baseline: dict[str, Any] | None = None
    amount_threshold: float = Field(default=150_000.0, ge=0, allow_inf_nan=False)
    velocity_limit: float = Field(default=5.0, gt=0, allow_inf_nan=False)


@app.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "ok", "service": "risk-scoring"}


@app.get("/health/ready")
def ready() -> dict[str, str]:
    # No external dependency is required for the stateless scoring engine.
    return {"status": "ready", "model_version": MODEL_VERSION}


@app.post("/v1/risk/assess")
def assess(request: AssessRequest) -> dict[str, Any]:
    if not request.transaction:
        raise HTTPException(status_code=422, detail="transaction must not be empty")
    try:
        decision = assess_transaction(
            request.transaction,
            request.history,
            request.tenant_baseline,
            amount_threshold=request.amount_threshold,
            velocity_limit=request.velocity_limit,
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "decision": decision.as_dict(),
        "disclaimer": "Risk signal only; no payment or ledger action was executed.",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("risk_scoring.app:app", host="0.0.0.0", port=int(os.getenv("PORT", "8300")))
