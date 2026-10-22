from __future__ import annotations

import json
import sqlite3
from contextvars import ContextVar
from decimal import Decimal, InvalidOperation, ROUND_CEILING
from pathlib import Path
from uuid import uuid4


current_run: ContextVar[str] = ContextVar("inference_run", default="manual")

# USD per million tokens, verified against Nebius's public models_info catalog.
# Prices are estimates for app-side admission control, not a provider billing cap.
MODEL_PRICES = {
    "nvidia/Nemotron-3_5-Lightning": ("0.06", "0.24"),
    "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B": ("0.06", "0.24"),
    "nvidia/nemotron-3-super-120b-a12b": ("0.30", "0.90"),
    "nvidia/Nemotron-3.5-Super-VL": ("0.30", "0.90"),
    "nvidia/Nemotron-3-Ultra-550b-a55b": ("1.00", "3.00"),
}


class BudgetExceeded(ValueError):
    pass


class InferenceBudget:
    def __init__(
        self, path: Path, limit_usd: str = "20", per_run_usd: str = "0.25",
        max_calls_per_run: int = 5,
    ) -> None:
        self.path = path
        self.limit = self._micros(limit_usd)
        self.per_run = self._micros(per_run_usd)
        if self.limit < 0 or self.per_run < 0 or max_calls_per_run < 1:
            raise ValueError("Budget limits must be non-negative and call limit positive")
        self.max_calls = max_calls_per_run
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("""CREATE TABLE IF NOT EXISTS inference_costs (
                id TEXT PRIMARY KEY, run_id TEXT NOT NULL, stage TEXT NOT NULL,
                model TEXT NOT NULL, charge INTEGER NOT NULL, state TEXT NOT NULL,
                input_tokens INTEGER NOT NULL DEFAULT 0, output_tokens INTEGER NOT NULL DEFAULT 0,
                fingerprint TEXT, response TEXT
            )""")

    @staticmethod
    def _micros(value: str) -> int:
        try:
            number = Decimal(value)
        except InvalidOperation:
            raise ValueError("Budget must be a non-negative finite number") from None
        if not number.is_finite() or number < 0:
            raise ValueError("Budget must be a non-negative finite number")
        return int((number * 1_000_000).to_integral_value(rounding=ROUND_CEILING))

    @staticmethod
    def _charge(model: str, inputs: int, outputs: int) -> int:
        if model not in MODEL_PRICES:
            raise ValueError("No verified price is configured for this model")
        if inputs < 0 or outputs < 0:
            raise ValueError("Token counts cannot be negative")
        input_rate, output_rate = map(Decimal, MODEL_PRICES[model])
        # Per-million rates become micro-dollars directly when multiplied by tokens.
        return int((inputs * input_rate + outputs * output_rate).to_integral_value(rounding=ROUND_CEILING))

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=10)

    def reserve(self, run_id: str, stage: str, model: str, inputs: int, outputs: int) -> str:
        charge = self._charge(model, inputs, outputs)
        ticket = uuid4().hex
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            total, run_total, calls = connection.execute(
                "SELECT COALESCE(SUM(charge),0), COALESCE(SUM(CASE WHEN run_id=? THEN charge ELSE 0 END),0), "
                "COALESCE(SUM(CASE WHEN run_id=? AND state!='cache' THEN 1 ELSE 0 END),0) FROM inference_costs",
                (run_id, run_id),
            ).fetchone()
            if total + charge > self.limit or run_total + charge > self.per_run or calls >= self.max_calls:
                raise BudgetExceeded("Inference spending or call limit reached; no provider request was sent")
            connection.execute(
                "INSERT INTO inference_costs(id,run_id,stage,model,charge,state) VALUES(?,?,?,?,?,'reserved')",
                (ticket, run_id, stage, model, charge),
            )
        return ticket

    def complete(self, ticket: str, inputs: int | None, outputs: int | None, fingerprint: str, payload: dict) -> None:
        with self._connect() as connection:
            row = connection.execute("SELECT model,charge FROM inference_costs WHERE id=?", (ticket,)).fetchone()
            valid = type(inputs) is int and type(outputs) is int and inputs >= 0 and outputs >= 0
            charge = self._charge(row[0], inputs, outputs) if valid else row[1]
            connection.execute(
                "UPDATE inference_costs SET charge=?,state=?,input_tokens=?,output_tokens=?,fingerprint=?,response=? WHERE id=?",
                (charge, "complete" if valid else "uncertain", inputs if valid else 0,
                 outputs if valid else 0, fingerprint, json.dumps(payload), ticket),
            )

    def fail(self, ticket: str, definitely_unbilled: bool = False) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE inference_costs SET charge=CASE WHEN ? THEN 0 ELSE charge END,state=? WHERE id=?",
                (definitely_unbilled, "rejected" if definitely_unbilled else "uncertain", ticket),
            )

    def cached(self, fingerprint: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT response FROM inference_costs WHERE fingerprint=? AND response IS NOT NULL ORDER BY rowid DESC LIMIT 1",
                (fingerprint,),
            ).fetchone()
        return json.loads(row[0]) if row else None

    def record_cache_hit(self, run_id: str, stage: str, model: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO inference_costs(id,run_id,stage,model,charge,state) VALUES(?,?,?,?,0,'cache')",
                (uuid4().hex, run_id, stage, model),
            )

    def summary(self, run_id: str | None = None) -> dict:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COALESCE(SUM(charge),0),COALESCE(SUM(input_tokens),0),COALESCE(SUM(output_tokens),0),"
                "COALESCE(SUM(CASE WHEN state='cache' THEN 1 ELSE 0 END),0),"
                "COALESCE(SUM(CASE WHEN state!='cache' THEN 1 ELSE 0 END),0) "
                "FROM inference_costs WHERE (? IS NULL OR run_id=?)", (run_id, run_id),
            ).fetchone()
        return dict(accounted_cost_usd=row[0] / 1_000_000, input_tokens=row[1], output_tokens=row[2], cache_hits=row[3], calls=row[4])
