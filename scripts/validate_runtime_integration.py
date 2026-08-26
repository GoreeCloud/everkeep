#!/usr/bin/env python3
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class Identity:
    def __init__(self, service):
        self.service = service
    def resolve_principal(self, bearer_token, *, require_recent_reauth=False):
        assert bearer_token == "token"
        return self.service.Principal(
            "user:test",
            frozenset(self.service.PERMISSIONS.values()),
            authenticated=True,
            reauthenticated=require_recent_reauth,
        )


class AllowProvider:
    def authorize(self, action, resource, context):
        return {"decision": "allow", "action": action, "reason": "test-allow"}


class DenyProvider:
    def authorize(self, action, resource, context):
        return {"decision": "deny", "action": action, "reason": "test-deny"}


class Mesh:
    def __init__(self):
        self.events = []
    def publish(self, event_type, aggregate_id, payload):
        self.events.append((event_type, aggregate_id, payload))
        return f"mesh:{len(self.events)}"


class Adapter:
    adapter_id = "goreecloud-documents"
    def collect(self, cursor=None):
        return {"resources": [{"resourceId": "doc:adapter:1"}], "recoveryPoints": [], "nextCursor": "cursor:1"}


def main():
    store_mod = load("persistent_service", ROOT / "scripts" / "persistent_service.py")
    service_mod = load("service_api", ROOT / "scripts" / "service_api.py")
    runtime_mod = load("runtime_integration", ROOT / "scripts" / "runtime_integration.py")

    store = store_mod.EverkeepStore()
    service = service_mod.EverkeepService(store)
    mesh = Mesh()
    runtime = runtime_mod.EverkeepRuntime(
        service,
        runtime_mod.RuntimeContext(Identity(service_mod), AllowProvider(), AllowProvider(), mesh),
    )

    resource = {
        "schemaVersion": "1.0.0",
        "resourceId": "doc:runtime:1",
        "resourceClass": "document",
        "application": "goreecloud-documents",
        "owner": {"subjectId": "user:test"},
        "preservationTier": "protected",
        "createdAt": "2026-08-26T00:00:00Z"
    }
    registered = runtime.register_resource("token", resource, "runtime-idem-1")
    assert registered["resource"]["resourceId"] == resource["resourceId"]
    publish = runtime.publish_outbox()
    assert publish["published"] >= 1 and publish["failed"] == 0 and mesh.events

    adapter = runtime.run_adapter(Adapter())
    assert adapter["nextCursor"] == "cursor:1"

    denied = runtime_mod.EverkeepRuntime(
        service,
        runtime_mod.RuntimeContext(Identity(service_mod), DenyProvider(), AllowProvider(), mesh),
    )
    try:
        denied.gate("everkeep.resource.register", resource)
    except runtime_mod.PlatformDecisionDenied:
        pass
    else:
        raise AssertionError("Privacy Shield denial must fail closed")

    schema = json.loads((ROOT / "contracts" / "everkeep.runtime-config.schema.json").read_text())
    assert schema["required"] == ["schemaVersion", "environment", "database", "platform", "outbox", "adapters"]

    postgres = (ROOT / "scripts" / "postgres_repository.py").read_text()
    for required in ["FOR UPDATE", "SKIP LOCKED", "everkeep_outbox", "everkeep_policy_versions"]:
        assert required in postgres

    print("Everkeep runtime integration validation passed")


if __name__ == "__main__":
    main()
