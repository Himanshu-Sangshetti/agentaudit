"""Thin Clocked API client with an on-disk response cache and credit accounting.

Every call is cached by (endpoint, payload) so re-running a benchmark or the demo
never spends credits twice. Usage is read from the X-Clocked-* response headers.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import httpx
from dotenv import load_dotenv

BASE_URL = "https://clocked.rezolve.ai/clocked"
ENDPOINTS = {
    "decide", "extract", "fill", "pii", "injection", "script",
    "grounding", "compare", "rerank", "pipeline",
}
CACHE_DIR = Path(os.environ.get("AGENTAUDIT_CACHE", ".cache/clocked"))


class ClockedError(RuntimeError):
    def __init__(self, status: int, body: str):
        super().__init__(f"Clocked HTTP {status}: {body[:500]}")
        self.status = status
        self.body = body


@dataclass
class Call:
    endpoint: str
    result: dict
    round_trip_ms: float
    model_ms: float | None
    credits: float | None
    cost_usd: float | None
    cached: bool


@dataclass
class Usage:
    calls: int = 0
    cached: int = 0
    credits: float = 0.0
    cost_usd: float = 0.0
    by_endpoint: dict = field(default_factory=dict)

    def add(self, call: Call) -> None:
        self.calls += 1
        if call.cached:
            self.cached += 1
            return
        self.credits += call.credits or 0
        self.cost_usd += call.cost_usd or 0
        self.by_endpoint[call.endpoint] = self.by_endpoint.get(call.endpoint, 0) + (call.credits or 0)


def _float(v: str | None) -> float | None:
    try:
        return float(v) if v is not None else None
    except ValueError:
        return None


class Clocked:
    def __init__(self, api_key: str | None = None, cache: bool = True, timeout: float = 120.0,
                 max_retries: int = 4, credit_ceiling: float | None = None):
        load_dotenv()
        self.api_key = api_key or os.environ.get("CLOCKED_API_KEY")
        if not self.api_key:
            raise RuntimeError("CLOCKED_API_KEY is not set (put it in .env)")
        self.cache = cache
        self.max_retries = max_retries
        # Hard stop so a runaway loop can't drain the account.
        self.credit_ceiling = credit_ceiling or _float(os.environ.get("AGENTAUDIT_CREDIT_CEILING"))
        self.usage = Usage()
        self._http = httpx.Client(timeout=timeout)

    def close(self) -> None:
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def _cache_path(self, endpoint: str, payload: dict) -> Path:
        key = hashlib.sha256(json.dumps([endpoint, payload], sort_keys=True).encode()).hexdigest()
        return CACHE_DIR / endpoint / f"{key}.json"

    def call(self, endpoint: str, payload: dict) -> Call:
        if endpoint not in ENDPOINTS:
            raise ValueError(f"unknown endpoint {endpoint}")
        path = self._cache_path(endpoint, payload)
        if self.cache and path.exists():
            rec = json.loads(path.read_text())
            call = Call(endpoint, rec["result"], rec["round_trip_ms"], rec.get("model_ms"),
                        rec.get("credits"), rec.get("cost_usd"), cached=True)
            self.usage.add(call)
            return call
        if self.credit_ceiling is not None and self.usage.credits >= self.credit_ceiling:
            raise RuntimeError(f"credit ceiling {self.credit_ceiling} reached")

        # One idempotency key per logical request, reused across retries (per the docs).
        idem = str(uuid.uuid4())
        headers = {"Authorization": f"Bearer {self.api_key}", "Idempotency-Key": idem}
        delay = 1.0
        for attempt in range(self.max_retries + 1):
            t0 = time.perf_counter()
            try:
                resp = self._http.post(f"{BASE_URL}/{endpoint}", json=payload, headers=headers)
            except httpx.TransportError:
                if attempt == self.max_retries:
                    raise
                time.sleep(delay)
                delay *= 2
                continue
            rtt = (time.perf_counter() - t0) * 1000
            if resp.status_code in (409, 429) or resp.status_code >= 500:
                if attempt == self.max_retries:
                    raise ClockedError(resp.status_code, resp.text)
                retry_after = _float(resp.headers.get("Retry-After"))
                time.sleep(retry_after or delay)
                delay *= 2
                continue
            if resp.status_code >= 400:
                raise ClockedError(resp.status_code, resp.text)
            call = Call(endpoint, resp.json(), rtt, _float(resp.headers.get("X-Clocked-Model-Ms")),
                        _float(resp.headers.get("X-Clocked-Credits")),
                        _float(resp.headers.get("X-Clocked-Cost-Usd")), cached=False)
            self.usage.add(call)
            if self.cache:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps({
                    "result": call.result, "round_trip_ms": rtt, "model_ms": call.model_ms,
                    "credits": call.credits, "cost_usd": call.cost_usd, "payload": payload,
                }))
            return call
        raise AssertionError("unreachable")

    # Convenience wrappers, one per endpoint.
    def decide(self, **p): return self.call("decide", p)
    def extract(self, **p): return self.call("extract", p)
    def fill(self, **p): return self.call("fill", p)
    def pii(self, **p): return self.call("pii", p)
    def injection(self, **p): return self.call("injection", p)
    def script(self, **p): return self.call("script", p)
    def grounding(self, **p): return self.call("grounding", p)
    def compare(self, **p): return self.call("compare", p)
    def rerank(self, **p): return self.call("rerank", p)
    def pipeline(self, **p): return self.call("pipeline", p)
