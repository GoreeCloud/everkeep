#!/usr/bin/env python3
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    service = load("service_api", ROOT / "scripts" / "service_api.py")
    store_mod = load("persistent_service", ROOT / "scripts" / "persistent_service.py")

    store = store_mod.EverkeepStore()
    api = service.EverkeepService(store)
    full = service.Principal(
        "tester",
        frozenset(service.PERMISSIONS.values()),
        authenticated=True,
        reauthenticated=True,
    )
    read_only = service.Principal(
        "reader",
        frozenset({service.PERMISSIONS["resource.read"], service.PERMISSIONS["recovery.read"]}),
    )

    resource = {
        "schemaVersion": "1.0.0",
        "resourceId": "doc:test:1",
        "resourceClass": "document",
        "application": "goreecloud-documents",
        "owner": {"subjectId": "user:test"},
        "preservationTier": "protected",
        "createdAt": "2026-08-26T00:00:00Z"
    }
    first = api.register_resource(full, resource, "idem-resource-1")
    replay = api.register_resource(full, resource, "idem-resource-1")
    assert first == replay
    assert api.get_resource(read_only, resource["resourceId"])["etag"] == first["etag"]

    try:
        api.register_resource(full, resource | {"application": "goreecloud-drive"}, "idem-resource-1")
    except service.PreconditionFailed:
        pass
    else:
        raise AssertionError("idempotency-key request mismatch must fail")

    policy = {
        "schemaVersion": "1.0.0",
        "policyId": "policy:test",
        "name": "Test",
        "enabled": True,
        "scope": {"resourceIds": [resource["resourceId"]]},
        "objectives": {"rpoSeconds": 3600, "rtoSeconds": 3600, "minimumCopies": 2, "minimumFailureDomains": 2},
        "retention": {"mode": "rolling", "minimumSeconds": 3600},
        "verification": {"integrityIntervalSeconds": 3600, "restoreTestIntervalSeconds": 86400}
    }
    saved = api.save_policy(full, policy)
    try:
        api.save_policy(full, policy | {"name": "Changed"}, if_match='"wrong"')
    except service.PreconditionFailed:
        pass
    else:
        raise AssertionError("stale policy ETag must fail")
    saved2 = api.save_policy(full, policy | {"name": "Changed"}, if_match=saved["etag"])
    assert saved2["version"] == 2

    point = {
        "schemaVersion": "1.0.0",
        "recoveryPointId": "rp:test:1",
        "resourceId": resource["resourceId"],
        "type": "snapshot",
        "createdAt": "2026-08-26T00:01:00Z",
        "state": "available",
        "copies": [{"copyId": "copy:1", "storageClass": "protected", "failureDomain": "zone-a", "encrypted": True}],
        "integrity": {"algorithm": "sha256", "digest": "abc", "state": "verified"},
        "recoveryEligibility": "eligible"
    }
    api.ingest_recovery_point(full, point, "idem-rp-1")
    api.transition_recovery_point(full, point["recoveryPointId"], "verifying")
    api.transition_recovery_point(full, point["recoveryPointId"], "available")
    projection = api.recovery_center(read_only, resource["resourceId"])
    assert projection and projection["projection"]["recoveryPoints"]

    try:
        api.save_policy(read_only, policy)
    except service.AuthorizationError:
        pass
    else:
        raise AssertionError("unauthorized policy write must fail")

    assert api.health()["status"] == "ok"
    assert api.readiness()["status"] == "ready"
    assert len(api.pending_outbox()) >= 4

    adapter_schema = json.loads((ROOT / "contracts" / "everkeep.first-party-adapter.schema.json").read_text())
    assert adapter_schema["required"] == ["schemaVersion", "adapterId", "application", "resourceClasses", "capabilities", "cursorMode"]
    adapters = json.loads((ROOT / "examples" / "adapters" / "first-party-adapters.json").read_text())
    assert {a["application"] for a in adapters} == {"goreecloud-drive", "goreecloud-documents", "goreecloud-photos", "goreecloud-vault", "goreecloud-backup"}

    openapi = (ROOT / "api" / "openapi.yaml").read_text()
    for required in ["/health:", "/ready:", "/v1/resources:", "/v1/recovery-points:", "goreecloudIdentity"]:
        assert required in openapi

    migration = (ROOT / "db" / "postgres" / "001_everkeep_core.sql").read_text()
    for required in ["everkeep_resources", "everkeep_policy_versions", "everkeep_outbox", "everkeep_idempotency", "everkeep_schema_migrations"]:
        assert required in migration

    print("Everkeep service/API validation passed")


if __name__ == "__main__":
    main()
