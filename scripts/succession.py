#!/usr/bin/env python3
"""Fail-closed Succession/Digital Legacy activation eligibility evaluation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

BASE_SIGNALS = {"privacy-authorized", "wardveil-clear"}


def _parse(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _fmt(value):
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def required_signals(policy):
    signals = set(BASE_SIGNALS)
    signals.update((policy.get("activation") or {}).get("requiredSignals", []))
    dispositions = {rule.get("disposition") for rule in policy.get("rules", [])}
    if "transfer" in dispositions:
        signals.add("successor-verified")
    if "delete" in dispositions:
        signals.add("destruction-authorized")
    if (policy.get("activation") or {}).get("trustedContactQuorum", 0) > 0:
        signals.add("trusted-contact-quorum")
    return sorted(signals)


def evaluate(policy, signal_evidence, decision_id, evaluated_at, activation_event_at=None):
    now = _parse(evaluated_at)
    status = policy.get("status")
    policy_id = policy.get("policyId")
    if not policy_id:
        raise ValueError("succession policyId is required")

    if status == "revoked":
        return _decision(decision_id, policy_id, now, "revoked", False, {}, ["policy:revoked"], [], activation_event_at, False)
    if status != "active":
        return _decision(decision_id, policy_id, now, "inactive", False, {}, [f"policy:{status or 'unknown'}"], [], activation_event_at, False)
    if not activation_event_at:
        return _decision(decision_id, policy_id, now, "inactive", False, {}, ["activation-event:missing"], [], None, False)

    event_at = _parse(activation_event_at)
    waiting_seconds = int((policy.get("activation") or {}).get("waitingPeriodSeconds", 0))
    waiting_satisfied = now >= event_at + timedelta(seconds=waiting_seconds)
    blockers = [] if waiting_satisfied else ["waiting-period:pending"]
    signal_results = {}
    evidence_refs = set()
    saw_fail = False
    saw_unknown = False

    for signal in required_signals(policy):
        supplied = signal_evidence.get(signal) or {}
        state = supplied.get("state", "unknown")
        if state not in {"pass", "fail", "unknown"}:
            state = "unknown"
        evidence_ref = supplied.get("evidenceRef")
        signal_results[signal] = {
            "state": state,
            "evidenceRef": evidence_ref,
            "reason": supplied.get("reason"),
        }
        if evidence_ref:
            evidence_refs.add(evidence_ref)
        if state == "fail":
            saw_fail = True
            blockers.append(f"signal:{signal}:fail")
        elif state != "pass":
            saw_unknown = True
            blockers.append(f"signal:{signal}:unknown")

    if saw_fail or not waiting_satisfied:
        state = "blocked"
        eligible = False
    elif saw_unknown:
        state = "unknown"
        eligible = False
    else:
        state = "eligible"
        eligible = True

    return _decision(
        decision_id,
        policy_id,
        now,
        state,
        eligible,
        signal_results,
        sorted(set(blockers)),
        sorted(evidence_refs),
        _fmt(event_at),
        waiting_satisfied,
    )


def _decision(decision_id, policy_id, now, state, eligible, signals, blockers, refs, event_at, waiting_satisfied):
    return {
        "schemaVersion": "1.0",
        "decisionId": decision_id,
        "policyId": policy_id,
        "evaluatedAt": _fmt(now),
        "state": state,
        "activationEligible": eligible,
        "executionAuthorized": False,
        "signalResults": dict(sorted(signals.items())),
        "blockers": sorted(blockers),
        "evidenceRefs": sorted(refs),
        "activationEventAt": event_at,
        "waitingPeriodSatisfied": waiting_satisfied,
    }
