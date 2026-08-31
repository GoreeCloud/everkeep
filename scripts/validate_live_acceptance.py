#!/usr/bin/env python3
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENVIRONMENT = "staging"
REVISION = "abcdef1"
OBSERVED_AT = "2026-08-31T03:30:00+00:00"
CAPTURED_AT = datetime(2026, 8, 31, 4, 0, tzinfo=timezone.utc)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def evidence(name, provider, **details):
    return {
        "provider": provider,
        "environment": ENVIRONMENT,
        "everkeep_revision": REVISION,
        "evidence_id": f"evidence:{name}",
        "observed_at": OBSERVED_AT,
        **details,
    }


def passing_checks(mod):
    return [
        mod.AcceptanceCheck(
            "everkeep.readiness",
            "pass",
            True,
            evidence(
                "readiness",
                "everkeep",
                ready=True,
                deployed_revision=REVISION,
            ),
        ),
        mod.AcceptanceCheck(
            "postgres.migrations",
            "pass",
            True,
            evidence(
                "migrations",
                "postgresql",
                database_reachable=True,
                migrations_current=True,
            ),
        ),
        mod.AcceptanceCheck(
            "identity.authenticated-flow",
            "pass",
            True,
            evidence(
                "identity",
                "goreecloud-identity",
                provider_revision="identity01",
                service_id="everkeep",
                authenticated_request_succeeded=True,
                unauthorized_request_rejected=True,
            ),
        ),
        mod.AcceptanceCheck(
            "privacy.deliberate-denial",
            "pass",
            True,
            evidence(
                "privacy",
                "privacy-shield",
                provider_revision="privacy01",
                denial_observed=True,
                mutation_committed=False,
                decision_id="privacy-decision-1",
            ),
        ),
        mod.AcceptanceCheck(
            "wardveil.deliberate-denial",
            "pass",
            True,
            evidence(
                "wardveil",
                "wardveil-security",
                provider_revision="wardveil1",
                denial_observed=True,
                mutation_committed=False,
                audit_reference="wardveil:audit:1",
            ),
        ),
        mod.AcceptanceCheck(
            "mesh.delivery-retry",
            "pass",
            True,
            evidence(
                "mesh",
                "goreecloud-mesh",
                provider_revision="meshrev1",
                delivery_succeeded=True,
                transient_failure_observed=True,
                retry_preserved=True,
                event_id="mesh-event-1",
            ),
        ),
        mod.AcceptanceCheck(
            "adapter.cursor-restart",
            "pass",
            True,
            evidence(
                "adapter",
                "everkeep",
                restart_observed=True,
                cursor_resumed=True,
                duplicate_detected=False,
                skip_detected=False,
                adapter_id="goreecloud-documents",
            ),
        ),
        mod.AcceptanceCheck(
            "runtime.durable-restart",
            "pass",
            True,
            evidence(
                "runtime",
                "everkeep",
                restart_observed=True,
                durable_state_preserved=True,
                idempotency_preserved=True,
                pending_outbox_preserved=True,
            ),
        ),
    ]


def conditional_evidence_schema(schema, check_name):
    conditions = schema["properties"]["checks"]["items"]["allOf"]
    for condition in conditions:
        props = condition.get("if", {}).get("properties", {})
        name = props.get("name", {}).get("const")
        if name == check_name:
            return condition["then"]["properties"]["evidence"]["allOf"][1]
    raise AssertionError(f"missing conditional schema for {check_name}")


def evaluate(mod, checks):
    return mod.evaluate(
        checks,
        ENVIRONMENT,
        REVISION,
        captured_at=CAPTURED_AT,
    )


def main():
    mod = load("live_acceptance", ROOT / "scripts" / "live_acceptance.py")
    passed = passing_checks(mod)
    accepted = evaluate(mod, passed)
    assert accepted["accepted"] is True
    assert accepted["capturedAt"] == CAPTURED_AT.isoformat()

    incomplete = passed[:-1]
    assert evaluate(mod, incomplete)["accepted"] is False

    denied = list(passed)
    denied[0] = mod.AcceptanceCheck(
        denied[0].name,
        "fail",
        True,
        denied[0].evidence,
    )
    assert evaluate(mod, denied)["accepted"] is False

    unauth = list(passed)
    unauth[0] = mod.AcceptanceCheck(
        unauth[0].name,
        "pass",
        False,
        unauth[0].evidence,
    )
    assert evaluate(mod, unauth)["accepted"] is False

    synthetic = list(passed)
    synthetic[2] = mod.AcceptanceCheck(
        "identity.authenticated-flow",
        "pass",
        True,
        {"verified": True},
    )
    assert evaluate(mod, synthetic)["accepted"] is False

    wrong_provider = list(passed)
    wrong_provider[3] = mod.AcceptanceCheck(
        "privacy.deliberate-denial",
        "pass",
        True,
        {**wrong_provider[3].evidence, "provider": "everkeep"},
    )
    assert evaluate(mod, wrong_provider)["accepted"] is False

    wrong_revision = list(passed)
    wrong_revision[4] = mod.AcceptanceCheck(
        "wardveil.deliberate-denial",
        "pass",
        True,
        {**wrong_revision[4].evidence, "everkeep_revision": "deadbee"},
    )
    assert evaluate(mod, wrong_revision)["accepted"] is False

    duplicate_checks = list(passed) + [passed[0]]
    assert evaluate(mod, duplicate_checks)["accepted"] is False

    duplicate_evidence = list(passed)
    duplicate_evidence[1] = mod.AcceptanceCheck(
        duplicate_evidence[1].name,
        duplicate_evidence[1].status,
        duplicate_evidence[1].authoritative,
        {
            **duplicate_evidence[1].evidence,
            "evidence_id": duplicate_evidence[0].evidence["evidence_id"],
        },
    )
    assert evaluate(mod, duplicate_evidence)["accepted"] is False

    stale = list(passed)
    stale[2] = mod.AcceptanceCheck(
        stale[2].name,
        stale[2].status,
        stale[2].authoritative,
        {**stale[2].evidence, "observed_at": "2026-08-31T02:59:59+00:00"},
    )
    assert evaluate(mod, stale)["accepted"] is False

    future = list(passed)
    future[5] = mod.AcceptanceCheck(
        future[5].name,
        future[5].status,
        future[5].authoritative,
        {**future[5].evidence, "observed_at": "2026-08-31T04:01:01+00:00"},
    )
    assert evaluate(mod, future)["accepted"] is False

    boundary_old = list(passed)
    boundary_old[2] = mod.AcceptanceCheck(
        boundary_old[2].name,
        boundary_old[2].status,
        boundary_old[2].authoritative,
        {**boundary_old[2].evidence, "observed_at": "2026-08-31T03:00:00+00:00"},
    )
    assert evaluate(mod, boundary_old)["accepted"] is True

    boundary_future = list(passed)
    boundary_future[5] = mod.AcceptanceCheck(
        boundary_future[5].name,
        boundary_future[5].status,
        boundary_future[5].authoritative,
        {**boundary_future[5].evidence, "observed_at": "2026-08-31T04:01:00+00:00"},
    )
    assert evaluate(mod, boundary_future)["accepted"] is True

    try:
        mod.evaluate(
            passed,
            ENVIRONMENT,
            REVISION,
            captured_at=datetime(2026, 8, 31, 4, 0),
        )
    except ValueError:
        pass
    else:
        raise AssertionError("naive acceptance capture time was accepted")

    schema = json.loads(
        (ROOT / "contracts" / "everkeep.live-acceptance.schema.json").read_text()
    )
    assert schema["properties"]["schemaVersion"]["const"] == "1.1"
    assert "accepted" in schema["required"]
    assert set(schema["properties"]["environment"]["enum"]) == {
        "staging",
        "production",
    }

    provenance = schema["$defs"]["authoritativeProvenance"]
    assert {
        "provider",
        "environment",
        "everkeep_revision",
        "evidence_id",
        "observed_at",
    }.issubset(provenance["required"])

    # Diagnostic fail/unknown checks may carry only failure details. Provenance
    # becomes structurally mandatory only for checks that claim authoritative pass.
    evidence_schema = schema["properties"]["checks"]["items"]["properties"]["evidence"]
    assert evidence_schema == {"type": "object"}
    conditions = schema["properties"]["checks"]["items"]["allOf"]
    assert len(conditions) == 9
    common = conditions[0]
    assert common["if"]["properties"]["status"]["const"] == "pass"
    assert common["if"]["properties"]["authoritative"]["const"] is True
    assert common["then"]["properties"]["evidence"]["$ref"] == "#/$defs/authoritativeProvenance"

    expected_provider_and_fields = {
        "everkeep.readiness": (
            "everkeep",
            {"ready", "deployed_revision"},
        ),
        "postgres.migrations": (
            "postgresql",
            {"database_reachable", "migrations_current"},
        ),
        "identity.authenticated-flow": (
            "goreecloud-identity",
            {
                "provider_revision",
                "service_id",
                "authenticated_request_succeeded",
                "unauthorized_request_rejected",
            },
        ),
        "privacy.deliberate-denial": (
            "privacy-shield",
            {"provider_revision", "denial_observed", "mutation_committed", "decision_id"},
        ),
        "wardveil.deliberate-denial": (
            "wardveil-security",
            {"provider_revision", "denial_observed", "mutation_committed", "audit_reference"},
        ),
        "mesh.delivery-retry": (
            "goreecloud-mesh",
            {
                "provider_revision",
                "delivery_succeeded",
                "transient_failure_observed",
                "retry_preserved",
                "event_id",
            },
        ),
        "adapter.cursor-restart": (
            "everkeep",
            {
                "restart_observed",
                "cursor_resumed",
                "duplicate_detected",
                "skip_detected",
                "adapter_id",
            },
        ),
        "runtime.durable-restart": (
            "everkeep",
            {
                "restart_observed",
                "durable_state_preserved",
                "idempotency_preserved",
                "pending_outbox_preserved",
            },
        ),
    }
    for check_name, (provider, required_fields) in expected_provider_and_fields.items():
        conditional = conditional_evidence_schema(schema, check_name)
        assert conditional["properties"]["provider"]["const"] == provider
        assert required_fields.issubset(conditional["required"])

    runbook = (ROOT / "docs" / "LIVE-ACCEPTANCE.md").read_text()
    for required in [
        "Identity",
        "Privacy Shield",
        "Wardveil",
        "Mesh",
        "cursor",
        "restart",
        "authoritative",
        "provider revision",
        "one hour",
        "60 seconds",
        "unique evidence identifier",
    ]:
        assert required in runbook

    print("Everkeep live acceptance validation passed")


if __name__ == "__main__":
    main()
