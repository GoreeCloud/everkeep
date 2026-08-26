#!/usr/bin/env python3
"""Deployment-oriented Everkeep runtime helpers.

No provider is considered available merely because its URL is configured.
Callers must successfully verify provider health/auth before sensitive work.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable


REQUIRED_ENDPOINTS = {
    "identity": "EVERKEEP_IDENTITY_URL",
    "privacy": "EVERKEEP_PRIVACY_URL",
    "wardveil": "EVERKEEP_WARDVEIL_URL",
    "mesh": "EVERKEEP_MESH_URL",
}


@dataclass(frozen=True)
class RuntimeConfig:
    environment: str
    database_url: str
    endpoints: dict[str, str]
    token_file: str | None

    @classmethod
    def from_env(cls) -> "RuntimeConfig":
        missing = ["EVERKEEP_DATABASE_URL"] + [env for env in REQUIRED_ENDPOINTS.values() if not os.getenv(env)]
        missing = [name for name in missing if not os.getenv(name)]
        if missing:
            raise RuntimeError("missing required runtime configuration: " + ", ".join(sorted(missing)))
        return cls(
            environment=os.getenv("EVERKEEP_ENVIRONMENT", "development"),
            database_url=os.environ["EVERKEEP_DATABASE_URL"],
            endpoints={name: os.environ[env] for name, env in REQUIRED_ENDPOINTS.items()},
            token_file=os.getenv("EVERKEEP_SERVICE_TOKEN_FILE"),
        )

    def service_token(self) -> str | None:
        if not self.token_file:
            return None
        with open(self.token_file, "r", encoding="utf-8") as handle:
            token = handle.read().strip()
        if not token:
            raise RuntimeError("service token file is empty")
        return token


class PlatformHTTPClient:
    def __init__(self, base_url: str, token_supplier: Callable[[], str | None], timeout: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.token_supplier = token_supplier
        self.timeout = timeout

    def request(self, path: str, method: str = "GET", payload: dict[str, Any] | None = None) -> dict[str, Any]:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {"Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        token = self.token_supplier()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(self.base_url + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8") or "{}")
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"platform request failed: {path}") from exc

    def health(self) -> bool:
        try:
            result = self.request("/health")
        except RuntimeError:
            return False
        return result.get("status") in {"ok", "healthy", "ready"}


class MeshOutboxWorker:
    """Publishes durable outbox entries using injected claim/ack functions."""

    def __init__(self, mesh: PlatformHTTPClient, claim: Callable[[int], list[dict]], ack: Callable[[int], None]):
        self.mesh = mesh
        self.claim = claim
        self.ack = ack

    def run_once(self, limit: int = 50) -> dict[str, int]:
        published = failed = 0
        for event in self.claim(max(1, min(limit, 500))):
            try:
                self.mesh.request("/v1/events", "POST", {
                    "eventType": event["event_type"],
                    "aggregateId": event.get("aggregate_id"),
                    "payload": event["payload"],
                })
                self.ack(int(event["outbox_id"]))
                published += 1
            except RuntimeError:
                failed += 1
        return {"published": published, "failed": failed}


class RuntimeMetrics:
    def __init__(self):
        self.started = time.monotonic()
        self.counters: dict[str, int] = {}

    def increment(self, name: str, amount: int = 1) -> None:
        self.counters[name] = self.counters.get(name, 0) + amount

    def snapshot(self) -> dict[str, Any]:
        return {"uptimeSeconds": int(time.monotonic() - self.started), "counters": dict(sorted(self.counters.items()))}
