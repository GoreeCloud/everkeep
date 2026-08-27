#!/usr/bin/env python3
"""Evidence-bounded Everkeep continuity posture evaluation.

This module evaluates continuity objectives from supplied authoritative evidence.
It does not probe infrastructure, perform failover, create recovery evidence, or
claim that any target environment is deployed.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

VALID_STATES = {"ready", "attention", "degraded", "unknown"}
DIMENSION_ORDER = (
    "rpo",
    "rto",
    "exercise",
    "failureDomains",
    "alternateRecoveryTarget",
    "dependencies",
    "keyMaterial",
)


class ContinuityError(ValueError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_time(value: str | None) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _state(state: str, *, measured=None, target=None, reason=None, evidence_ref=None):
    result = {"state": state}
    if measured is not None:
        result["measured"] = measured
    if target is not None:
        result["target"] = target
    if reason:
        result["reason"] = reason
    if evidence_ref:
        result["evidenceRef"] = evidence_ref
    return result


def _threshold_state(measured: float, target: float, *, lower_is_better=True):
    if target <= 0:
        return "unknown"
    ratio = measured / target if lower_is_better else target / measured
    if ratio > 1:
        return "degraded"
    if ratio >= 0.8:
        return "attention"
    return "ready"


def _boolean_dimension(value, required: bool, label: str, evidence_ref=None):
    if not required:
        return _state("ready", reason=f"{label} is not required by this objective.", evidence_ref=evidence_ref)
    if value is True:
        return _state("ready", reason=f"{label} is evidenced as ready.", evidence_ref=evidence_ref)
    if value is False:
        return _state("degraded", reason=f"{label} is evidenced as not ready.", evidence_ref=evidence_ref)
    return _state("unknown", reason=f"{label} readiness evidence is missing or unverified.", evidence_ref=evidence_ref)


def _aggregate(dimensions: dict[str, dict[str, Any]]) -> str:
    states = [dimensions[key]["state"] for key in DIMENSION_ORDER]
    if "degraded" in states:
        return "degraded"
    if "unknown" in states:
        return "unknown"
    if "attention" in states:
        return "attention"
    return "ready"


def evaluate_continuity(objective: dict[str, Any], evidence: dict[str, Any], observed_at: str | None = None):
    """Evaluate one policy-defined continuity objective.

    Missing or malformed required evidence resolves to ``unknown``. Explicit
    objective misses resolve to ``degraded``. Near-threshold measurements are
    surfaced as ``attention`` but never upgraded to ``ready``.
    """
    objective_id = objective.get("objectiveId")
    if not objective_id:
        raise ContinuityError("objectiveId is required")

    now = _parse_time(observed_at) if observed_at else _utc_now()
    if now is None:
        raise ContinuityError("observed_at must be an ISO 8601 date-time")

    rpo_target = objective.get("rpoSeconds")
    rto_target = objective.get("rtoSeconds")
    exercise_target = objective.get("maxExerciseAgeSeconds")
    min_domains = objective.get("minFailureDomains", 1)

    for name, value in [
        ("rpoSeconds", rpo_target),
        ("rtoSeconds", rto_target),
        ("maxExerciseAgeSeconds", exercise_target),
        ("minFailureDomains", min_domains),
    ]:
        if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value <= 0):
            raise ContinuityError(f"{name} must be a positive integer")

    dimensions: dict[str, dict[str, Any]] = {}
    blocker_codes: list[str] = []
    warning_codes: list[str] = []
    evidence_refs = set()

    def ref_for(key):
        refs = evidence.get("evidenceRefs") or {}
        if isinstance(refs, dict):
            ref = refs.get(key)
            if ref:
                evidence_refs.add(ref)
            return ref
        return None

    last_protection = _parse_time(evidence.get("lastProtectionAt"))
    if rpo_target is None:
        dimensions["rpo"] = _state("ready", reason="No RPO target is defined by this objective.")
    elif last_protection is None:
        dimensions["rpo"] = _state("unknown", target=rpo_target, reason="Last protection time is missing or invalid.", evidence_ref=ref_for("rpo"))
        blocker_codes.append("rpo-evidence-unknown")
    else:
        age = max(0.0, (now - last_protection).total_seconds())
        state = _threshold_state(age, rpo_target)
        dimensions["rpo"] = _state(state, measured=int(age), target=rpo_target, reason="Measured age since the last evidenced protection point.", evidence_ref=ref_for("rpo"))
        if state == "degraded":
            blocker_codes.append("rpo-missed")
        elif state == "attention":
            warning_codes.append("rpo-at-risk")

    measured_rto = evidence.get("measuredRecoverySeconds")
    if rto_target is None:
        dimensions["rto"] = _state("ready", reason="No RTO target is defined by this objective.")
    elif not isinstance(measured_rto, (int, float)) or isinstance(measured_rto, bool) or measured_rto < 0:
        dimensions["rto"] = _state("unknown", target=rto_target, reason="Measured recovery duration evidence is missing or invalid.", evidence_ref=ref_for("rto"))
        blocker_codes.append("rto-evidence-unknown")
    else:
        state = _threshold_state(float(measured_rto), rto_target)
        dimensions["rto"] = _state(state, measured=int(measured_rto), target=rto_target, reason="Measured recovery duration from an authoritative recovery exercise.", evidence_ref=ref_for("rto"))
        if state == "degraded":
            blocker_codes.append("rto-missed")
        elif state == "attention":
            warning_codes.append("rto-at-risk")

    last_exercise = _parse_time(evidence.get("lastExerciseAt"))
    if exercise_target is None:
        dimensions["exercise"] = _state("ready", reason="No recovery-exercise freshness target is defined.")
    elif last_exercise is None:
        dimensions["exercise"] = _state("unknown", target=exercise_target, reason="Recovery-exercise freshness evidence is missing or invalid.", evidence_ref=ref_for("exercise"))
        blocker_codes.append("exercise-evidence-unknown")
    else:
        age = max(0.0, (now - last_exercise).total_seconds())
        state = _threshold_state(age, exercise_target)
        dimensions["exercise"] = _state(state, measured=int(age), target=exercise_target, reason="Age of the latest authoritative recovery exercise.", evidence_ref=ref_for("exercise"))
        if state == "degraded":
            blocker_codes.append("recovery-exercise-stale")
        elif state == "attention":
            warning_codes.append("recovery-exercise-due")

    domains = evidence.get("failureDomains")
    if not isinstance(domains, list):
        dimensions["failureDomains"] = _state("unknown", target=min_domains, reason="Failure-domain evidence is missing or invalid.", evidence_ref=ref_for("failureDomains"))
        blocker_codes.append("failure-domain-evidence-unknown")
    else:
        distinct = len({str(domain).strip() for domain in domains if str(domain).strip()})
        state = "ready" if distinct >= min_domains else "degraded"
        dimensions["failureDomains"] = _state(state, measured=distinct, target=min_domains, reason="Distinct evidenced failure domains available to the protected scope.", evidence_ref=ref_for("failureDomains"))
        if state == "degraded":
            blocker_codes.append("failure-domain-concentration")

    dimensions["alternateRecoveryTarget"] = _boolean_dimension(
        evidence.get("alternateRecoveryTargetReady"),
        bool(objective.get("requireAlternateRecoveryTarget", False)),
        "Alternate recovery target",
        ref_for("alternateRecoveryTarget"),
    )
    if dimensions["alternateRecoveryTarget"]["state"] == "degraded":
        blocker_codes.append("alternate-recovery-target-unavailable")
    elif dimensions["alternateRecoveryTarget"]["state"] == "unknown":
        blocker_codes.append("alternate-recovery-target-unknown")

    dimensions["dependencies"] = _boolean_dimension(
        evidence.get("dependenciesReady"),
        bool(objective.get("requireDependencyReadiness", True)),
        "Recovery dependencies",
        ref_for("dependencies"),
    )
    if dimensions["dependencies"]["state"] == "degraded":
        blocker_codes.append("dependency-unavailable")
    elif dimensions["dependencies"]["state"] == "unknown":
        blocker_codes.append("dependency-readiness-unknown")

    dimensions["keyMaterial"] = _boolean_dimension(
        evidence.get("keyMaterialReady"),
        bool(objective.get("requireKeyMaterialReadiness", True)),
        "Recovery key material",
        ref_for("keyMaterial"),
    )
    if dimensions["keyMaterial"]["state"] == "degraded":
        blocker_codes.append("key-material-unavailable")
    elif dimensions["keyMaterial"]["state"] == "unknown":
        blocker_codes.append("key-material-readiness-unknown")

    overall = _aggregate(dimensions)
    return {
        "schemaVersion": "1.0",
        "objectiveId": objective_id,
        "scope": objective.get("scope", {}),
        "observedAt": now.isoformat().replace("+00:00", "Z"),
        "state": overall,
        "dimensions": dimensions,
        "blockerCodes": sorted(set(blocker_codes)),
        "warningCodes": sorted(set(warning_codes)),
        "evidenceRefs": sorted(evidence_refs),
        "failoverEligible": (
            overall == "ready"
            and dimensions["alternateRecoveryTarget"]["state"] == "ready"
            and dimensions["dependencies"]["state"] == "ready"
            and dimensions["keyMaterial"]["state"] == "ready"
        ),
    }


def build_exercise_record(
    exercise_id: str,
    objective_id: str,
    mode: str,
    started_at: str,
    finished_at: str,
    target_environment: str,
    verification: dict[str, Any],
):
    """Create a normalized evidence record for a recovery exercise."""
    if mode not in {"tabletop", "dry-run", "sandbox", "failover-drill", "restore-test"}:
        raise ContinuityError("unsupported recovery exercise mode")
    started = _parse_time(started_at)
    finished = _parse_time(finished_at)
    if not started or not finished or finished < started:
        raise ContinuityError("exercise timestamps are invalid")

    required_checks = ("integrity", "serviceHealth", "dependencies", "security", "privacy")
    checks = {}
    evidence_refs = set()
    for check in required_checks:
        supplied = verification.get(check) or {}
        state = supplied.get("state", "unknown")
        if state not in {"pass", "fail", "unknown"}:
            state = "unknown"
        ref = supplied.get("evidenceRef")
        if ref:
            evidence_refs.add(ref)
        checks[check] = {"state": state, "evidenceRef": ref, "reason": supplied.get("reason")}

    result = "pass" if all(item["state"] == "pass" for item in checks.values()) else (
        "fail" if any(item["state"] == "fail" for item in checks.values()) else "unknown"
    )
    return {
        "schemaVersion": "1.0",
        "exerciseId": exercise_id,
        "objectiveId": objective_id,
        "mode": mode,
        "targetEnvironment": target_environment,
        "startedAt": started.isoformat().replace("+00:00", "Z"),
        "finishedAt": finished.isoformat().replace("+00:00", "Z"),
        "durationSeconds": int((finished - started).total_seconds()),
        "result": result,
        "verification": checks,
        "evidenceRefs": sorted(evidence_refs),
        "productionMutationAllowed": False,
    }
