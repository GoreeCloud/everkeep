#!/usr/bin/env python3
"""Everkeep Phase 1 runtime integration reference layer.

This module wires the validated service facade to platform decision providers,
a Mesh publisher, and adapter executors without claiming production deployment.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from service_api import EverkeepService, Principal, AuthorizationError


class IdentityProvider(Protocol):
    def resolve_principal(self, bearer_token: str, *, require_recent_reauth: bool = False) -> Principal: ...


class PrivacyShieldProvider(Protocol):
    def authorize(self, action: str, resource: dict[str, Any] | None, context: dict[str, Any]) -> dict[str, Any]: ...


class WardveilProvider(Protocol):
    def authorize(self, action: str, resource: dict[str, Any] | None, context: dict[str, Any]) -> dict[str, Any]: ...


class MeshPublisher(Protocol):
    def publish(self, event_type: str, aggregate_id: str | None, payload: dict[str, Any]) -> str: ...


class AdapterExecutor(Protocol):
    adapter_id: str
    def collect(self, cursor: str | None = None) -> dict[str, Any]: ...


class PlatformDecisionDenied(PermissionError):
    pass


@dataclass
class RuntimeContext:
    identity: IdentityProvider
    privacy: PrivacyShieldProvider
    wardveil: WardveilProvider
    mesh: MeshPublisher


class EverkeepRuntime:
    def __init__(self, service: EverkeepService, context: RuntimeContext):
        self.service = service
        self.context = context

    def principal(self, bearer_token: str, *, recent_reauth: bool = False) -> Principal:
        principal = self.context.identity.resolve_principal(bearer_token, require_recent_reauth=recent_reauth)
        if not principal.authenticated:
            raise AuthorizationError("identity provider returned unauthenticated principal")
        return principal

    def gate(self, action: str, resource: dict[str, Any] | None, context: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx = context or {}
        privacy = self.context.privacy.authorize(action, resource, ctx)
        wardveil = self.context.wardveil.authorize(action, resource, ctx)
        if privacy.get("decision") != "allow":
            raise PlatformDecisionDenied(f"Privacy Shield denied {action}: {privacy.get('reason', 'unspecified')}")
        if wardveil.get("decision") != "allow":
            raise PlatformDecisionDenied(f"Wardveil denied {action}: {wardveil.get('reason', 'unspecified')}")
        return {"privacyShield": privacy, "wardveil": wardveil}

    def register_resource(self, bearer_token: str, resource: dict[str, Any], idempotency_key: str | None = None):
        principal = self.principal(bearer_token)
        self.gate("everkeep.resource.register", resource, {"subject": principal.subject})
        return self.service.register_resource(principal, resource, idempotency_key)

    def save_policy(self, bearer_token: str, policy: dict[str, Any], if_match: str | None = None):
        principal = self.principal(bearer_token, recent_reauth=True)
        self.gate("everkeep.policy.write", None, {"subject": principal.subject, "policyId": policy.get("policyId")})
        return self.service.save_policy(principal, policy, if_match)

    def ingest_recovery_point(self, bearer_token: str, point: dict[str, Any], idempotency_key: str | None = None):
        principal = self.principal(bearer_token)
        self.gate("everkeep.recovery-point.ingest", point, {"subject": principal.subject})
        return self.service.ingest_recovery_point(principal, point, idempotency_key)

    def transition_recovery_point(self, bearer_token: str, recovery_point_id: str, new_state: str):
        principal = self.principal(bearer_token, recent_reauth=new_state in {"blocked", "expired"})
        projection = self.service.store.db.execute(
            "SELECT payload FROM recovery_points WHERE recovery_point_id=?", (recovery_point_id,)
        ).fetchone()
        resource = None if projection is None else __import__("json").loads(projection["payload"])
        self.gate("everkeep.recovery-point.transition", resource, {"subject": principal.subject, "newState": new_state})
        return self.service.transition_recovery_point(principal, recovery_point_id, new_state)

    def publish_outbox(self, limit: int = 100) -> dict[str, int]:
        published = failed = 0
        for item in self.service.pending_outbox(limit=limit):
            try:
                self.context.mesh.publish(item["event_type"], item["aggregate_id"], item["payload"])
                self.service.mark_outbox_published(item["outbox_id"])
                published += 1
            except Exception:
                self.service.store.db.execute(
                    "UPDATE service_outbox SET attempts=attempts+1 WHERE outbox_id=?", (item["outbox_id"],)
                )
                self.service.store.db.commit()
                failed += 1
        return {"published": published, "failed": failed}

    def run_adapter(self, executor: AdapterExecutor) -> dict[str, Any]:
        row = self.service.store.db.execute(
            "SELECT cursor FROM adapter_state WHERE adapter_id=?", (executor.adapter_id,)
        ).fetchone()
        cursor = row["cursor"] if row else None
        batch = executor.collect(cursor)
        resources = batch.get("resources", [])
        points = batch.get("recoveryPoints", [])
        next_cursor = batch.get("nextCursor")
        return {
            "adapterId": executor.adapter_id,
            "resources": resources,
            "recoveryPoints": points,
            "nextCursor": next_cursor,
        }
