#!/usr/bin/env python3
import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    runtime = load("deployment_runtime", ROOT / "runtime" / "deployment_runtime.py")
    host = (ROOT / "runtime" / "everkeep_host.py").read_text()
    dockerfile = (ROOT / "Dockerfile").read_text()
    compose = (ROOT / "deploy" / "staging.compose.yaml").read_text()
    docs = (ROOT / "docs" / "DEPLOYMENT-READINESS.md").read_text()

    for key in ["EVERKEEP_DATABASE_URL", "EVERKEEP_IDENTITY_URL", "EVERKEEP_PRIVACY_URL", "EVERKEEP_WARDVEIL_URL", "EVERKEEP_MESH_URL"]:
        os.environ.pop(key, None)
    try:
        runtime.RuntimeConfig.from_env()
    except RuntimeError as exc:
        assert "missing required runtime configuration" in str(exc)
    else:
        raise AssertionError("runtime configuration must fail closed")

    os.environ.update({
        "EVERKEEP_DATABASE_URL": "postgresql://example",
        "EVERKEEP_IDENTITY_URL": "https://identity.example",
        "EVERKEEP_PRIVACY_URL": "https://privacy.example",
        "EVERKEEP_WARDVEIL_URL": "https://wardveil.example",
        "EVERKEEP_MESH_URL": "https://mesh.example",
    })
    config = runtime.RuntimeConfig.from_env()
    assert config.environment
    assert set(config.endpoints) == {"identity", "privacy", "wardveil", "mesh"}

    metrics = runtime.RuntimeMetrics()
    metrics.increment("test")
    assert metrics.snapshot()["counters"]["test"] == 1

    class Mesh:
        def request(self, path, method="GET", payload=None):
            assert path == "/v1/events" and method == "POST" and payload["eventType"]
            return {"accepted": True}

    acked = []
    worker = runtime.MeshOutboxWorker(Mesh(), lambda limit: [{"outbox_id": 7, "event_type": "everkeep.test", "aggregate_id": "r1", "payload": {"ok": True}}], acked.append)
    assert worker.run_once() == {"published": 1, "failed": 0}
    assert acked == [7]

    for required in ["/health", "/ready", "missingConfiguration"]:
        assert required in host
    for required in ["USER everkeep", "HEALTHCHECK", "CMD [\"python\", \"runtime/everkeep_host.py\"]"]:
        assert required in dockerfile
    for required in ["read_only: true", "no-new-privileges:true", "EVERKEEP_SERVICE_TOKEN_FILE", "${EVERKEEP_DATABASE_URL:?required}"]:
        assert required in compose
    for required in ["Staging Verification Gate", "Evidence Boundary", "does **not** establish"]:
        assert required in docs

    print("Everkeep deployment-readiness validation passed")


if __name__ == "__main__":
    main()
