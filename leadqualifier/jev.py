"""Thin HTTP client for TypeSafe System One (`POST /v1/systemone`).

One request carries every question we have about a lead; answers come back typed. The
client only adds retries, timing and cost accounting. The key is read from the environment
and never logged. Any object with `.system_one(state, questions) -> JevResponse` can stand
in for tests (see tests/conftest.py).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from . import config
from .constants import BASE_URL, MODEL, PRICE_PER_M_INPUT_TOKENS


class JevError(RuntimeError):
    def __init__(self, message: str, status: int | None = None, body: Any = None):
        super().__init__(message)
        self.status = status
        self.body = body


@dataclass
class JevResponse:
    answers: dict[str, dict]
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    request_id: str | None = None
    n_questions: int = 0
    raw: dict = field(default_factory=dict, repr=False)

    @property
    def cost_usd(self) -> float:
        return self.input_tokens * PRICE_PER_M_INPUT_TOKENS / 1_000_000

    def meta(self) -> dict:
        return {
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "latency_ms": self.latency_ms,
            "cost_usd": round(self.cost_usd, 7),
            "request_id": self.request_id,
            "n_questions": self.n_questions,
        }


class JevClient:
    def __init__(self, api_key: str | None = None, base_url: str = BASE_URL, model: str = MODEL,
                 timeout: float = 30.0, max_retries: int = 4):
        self.api_key = api_key or config.typesafe_api_key()
        if not self.api_key:
            raise JevError("TYPESAFE_API_KEY (or JEV_API_KEY) is not set")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self._http = httpx.Client(timeout=timeout, headers={"Authorization": f"Bearer {self.api_key}",
                                                            "Content-Type": "application/json"})

    def close(self) -> None:
        self._http.close()

    def system_one(self, state: Any, questions: dict[str, dict]) -> JevResponse:
        if not questions:
            raise JevError("questions must not be empty")
        body = {"state": state, "model": self.model, "questions": questions}
        delay = 0.6
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            t0 = time.perf_counter()
            try:
                r = self._http.post(f"{self.base_url}/v1/systemone", json=body)
            except httpx.HTTPError as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise JevError(f"connection error: {exc}") from exc
            latency = int((time.perf_counter() - t0) * 1000)
            if r.status_code in (408, 429, 500, 502, 503, 504, 529) and attempt < self.max_retries:
                retry_after_ms = r.headers.get("retry-after-ms")
                wait = int(retry_after_ms) / 1000 if retry_after_ms else float(r.headers.get("retry-after", delay))
                time.sleep(min(wait, 12))
                delay *= 2
                continue
            if r.status_code >= 400:
                try:
                    detail = r.json()
                except ValueError:
                    detail = r.text
                raise JevError(f"Jev returned HTTP {r.status_code}: {detail}", status=r.status_code, body=detail)
            data = r.json()
            usage = data.get("usage") or {}
            return JevResponse(
                answers=data.get("answers", {}),
                model=data.get("model", self.model),
                input_tokens=int(usage.get("input_tokens") or 0),
                output_tokens=int(usage.get("output_tokens") or 0),
                latency_ms=latency,
                request_id=r.headers.get("x-typesafe-request-id"),
                n_questions=len(questions),
                raw=data,
            )
        raise JevError(f"Jev request failed after retries: {last_exc}")

    def ping(self) -> dict:
        resp = self.system_one({"message": "Hi, do you build reporting automations for agencies? Could we talk this week?"},
                               {"asks_for_meeting": {"type": "noul", "instructions": "Does `message` ask for a call or meeting?"}})
        return {"ok": True, **resp.meta(), "asks_for_meeting": resp.answers["asks_for_meeting"].get("noul")}
