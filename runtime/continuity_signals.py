#!/usr/bin/env python3
"""Runtime-capable delivery boundary for minimized Everkeep continuity signals.

The transport clients are injected by the deployment environment. Source and CI
can validate this boundary with fakes, but that does not prove GoreeCloud
Monitoring ingestion or GoreeCloud Notify delivery is deployed or accepted in
any live environment.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class ContinuitySignalDeliveryError(ValueError):
    pass


def _iso_now(value: str | None = None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise ContinuitySignalDeliveryError("attempted_at must be an ISO 8601 date-time") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _delivery_result(
    *,
    delivery_id: str,
    channel: str,
    projection_id: str,
    objective_id: str,
    authority: str,
    attempted_at: str,
    response: Any,
    evidence_refs: list[str],
    failure_reason: str | None = None,
) -> dict[str, Any]:
    if failure_reason is not None:
        state = "failed"
        receipt = None
        reason = failure_reason
    elif not isinstance(response, dict):
        state = "unknown"
        receipt = None
        reason = "provider response unavailable or malformed"
    else:
        accepted = response.get("accepted")
        if accepted is True:
            state = "accepted"
        elif accepted is False:
            state = "rejected"
        else:
            state = "unknown"
        receipt = response.get("receiptRef") if isinstance(response.get("receiptRef"), str) and response.get("receiptRef") else None
        provider_reason = response.get("reason")
        reason = provider_reason if isinstance(provider_reason, str) and provider_reason else None

    return {
        "schemaVersion": "1.0",
        "deliveryId": delivery_id,
        "channel": channel,
        "projectionId": projection_id,
        "objectiveId": objective_id,
        "attemptedAt": attempted_at,
        "state": state,
        "authority": authority,
        "providerReceiptRef": receipt,
        "reason": reason,
        "deliveryAttempted": True,
        "sensitivePayloadsExcluded": True,
        "credentialsEmbedded": False,
        "evidenceRefs": sorted(set(evidence_refs)),
    }


def deliver_monitoring_metric(
    delivery_id: str,
    metric: dict[str, Any],
    client: Any,
    attempted_at: str | None = None,
) -> dict[str, Any]:
    """Submit one minimized metric to an injected GoreeCloud Monitoring client."""
    if not delivery_id:
        raise ContinuitySignalDeliveryError("delivery_id is required")
    if metric.get("projectionOnly") is not True or metric.get("sensitivePayloadsExcluded") is not True:
        raise ContinuitySignalDeliveryError("metric must be an approved minimized projection")
    metric_id = metric.get("metricId")
    objective_id = metric.get("objectiveId")
    if not metric_id or not objective_id or not str(metric.get("metricName", "")).startswith("everkeep.continuity."):
        raise ContinuitySignalDeliveryError("metric identity is invalid")

    payload = {
        "metricId": metric_id,
        "objectiveId": objective_id,
        "generatedAt": metric.get("generatedAt"),
        "metricName": metric.get("metricName"),
        "value": metric.get("value"),
        "unit": metric.get("unit"),
        "labels": dict(metric.get("labels", {})),
    }
    attempted = _iso_now(attempted_at)
    try:
        response = client.publish_metric(payload)
        failure = None
    except Exception as exc:  # provider failures become evidence, not success
        response = None
        failure = f"provider call failed: {type(exc).__name__}"
    return _delivery_result(
        delivery_id=delivery_id,
        channel="monitoring",
        projection_id=metric_id,
        objective_id=objective_id,
        authority="goreecloud-monitoring",
        attempted_at=attempted,
        response=response,
        evidence_refs=metric.get("evidenceRefs", []),
        failure_reason=failure,
    )


def deliver_notify_intent(
    delivery_id: str,
    intent: dict[str, Any],
    client: Any,
    attempted_at: str | None = None,
) -> dict[str, Any]:
    """Submit one minimized notification intent to an injected GoreeCloud Notify client."""
    if not delivery_id:
        raise ContinuitySignalDeliveryError("delivery_id is required")
    if (
        intent.get("projectionOnly") is not True
        or intent.get("deliveryAttempted") is not False
        or intent.get("deliveryAuthority") != "goreecloud-notify"
        or intent.get("sensitivePayloadsExcluded") is not True
    ):
        raise ContinuitySignalDeliveryError("intent must be an approved undelivered minimized projection")
    intent_id = intent.get("intentId")
    objective_id = intent.get("objectiveId")
    if not intent_id or not objective_id:
        raise ContinuitySignalDeliveryError("intent identity is invalid")

    payload = {
        "intentId": intent_id,
        "objectiveId": objective_id,
        "generatedAt": intent.get("generatedAt"),
        "category": intent.get("category"),
        "severity": intent.get("severity"),
        "title": intent.get("title"),
        "reason": intent.get("reason"),
        "dedupeKey": intent.get("dedupeKey"),
    }
    attempted = _iso_now(attempted_at)
    try:
        response = client.deliver_intent(payload)
        failure = None
    except Exception as exc:
        response = None
        failure = f"provider call failed: {type(exc).__name__}"
    return _delivery_result(
        delivery_id=delivery_id,
        channel="notify",
        projection_id=intent_id,
        objective_id=objective_id,
        authority="goreecloud-notify",
        attempted_at=attempted,
        response=response,
        evidence_refs=intent.get("evidenceRefs", []),
        failure_reason=failure,
    )
