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


def main():
    mod = load("preservation", ROOT / "scripts" / "preservation.py")
    resources = [
        {
            "resourceId": "note:1",
            "contentDigest": {"algorithm": "sha256", "value": "a" * 64},
            "mediaType": "text/markdown",
            "sizeBytes": 128,
            "provenanceRefs": ["prov:note:1"],
            "relationshipRefs": ["folder:notes"],
            "evidenceRefs": ["evidence:integrity:note:1"],
            "integrityVerified": True,
        },
        {
            "resourceId": "photo:2",
            "contentDigest": {"algorithm": "sha256", "value": "b" * 64},
            "mediaType": "image/jpeg",
            "sizeBytes": 4096,
            "provenanceRefs": ["prov:photo:2"],
            "relationshipRefs": ["album:summer"],
            "evidenceRefs": ["evidence:integrity:photo:2"],
            "integrityVerified": True,
        },
    ]

    capsule = mod.build_capsule(
        "capsule:test",
        list(reversed(resources)),
        preservation_tier="archive",
        created_at="2026-08-27T12:00:00Z",
        policy_refs=["policy:archive"],
    )
    assert capsule["integrityState"] == "verified"
    assert [entry["resourceId"] for entry in capsule["entries"]] == ["note:1", "photo:2"]
    assert len(capsule["capsuleDigest"]["value"]) == 64

    repeated = mod.build_capsule(
        "capsule:test",
        resources,
        preservation_tier="archive",
        created_at="2026-08-27T12:00:00Z",
        policy_refs=["policy:archive"],
    )
    assert repeated["capsuleDigest"] == capsule["capsuleDigest"]

    export = mod.build_export_manifest(
        "export:test",
        capsule,
        "everkeep-portable/1",
        {"state": "pass", "evidenceRef": "privacy:export:allowed"},
        created_at="2026-08-27T12:01:00Z",
    )
    assert export["portable"] is True
    assert export["authorityState"] == "pass"
    assert export["integrityState"] == "verified"

    blocked = mod.build_export_manifest(
        "export:blocked",
        capsule,
        "everkeep-portable/1",
        {"state": "unknown"},
        created_at="2026-08-27T12:01:00Z",
    )
    assert blocked["portable"] is False
    assert blocked["reason"]

    incomplete = [dict(resources[0], integrityVerified=None)]
    unknown_capsule = mod.build_capsule("capsule:unknown", incomplete, created_at="2026-08-27T12:00:00Z")
    assert unknown_capsule["integrityState"] == "unknown"
    assert mod.build_export_manifest("export:unknown", unknown_capsule, "zip", {"state": "pass"})["portable"] is False

    try:
        mod.build_capsule("capsule:bad", [{"resourceId": "missing-digest"}])
    except mod.PreservationError:
        pass
    else:
        raise AssertionError("missing content digests must fail closed")

    capsule_schema = json.loads((ROOT / "contracts" / "everkeep.preservation-capsule.schema.json").read_text())
    export_schema = json.loads((ROOT / "contracts" / "everkeep.portability-manifest.schema.json").read_text())
    assert capsule_schema["properties"]["formatVersion"]["const"] == "everkeep-capsule/1"
    assert "portable" in export_schema["required"]

    migration = (ROOT / "db" / "postgres" / "002_resilience_control_plane.sql").read_text()
    for table in ["everkeep_preservation_capsules", "everkeep_portability_exports"]:
        assert table in migration

    openapi = (ROOT / "api" / "openapi.yaml").read_text()
    for route in ["/v1/preservation/capsules:", "/v1/portability/exports:"]:
        assert route in openapi

    docs = (ROOT / "docs" / "PHASE-2-PRESERVATION-PORTABILITY.md").read_text()
    for phrase in ["raw bytes", "provenance", "content digest", "Privacy Shield", "fail closed"]:
        assert phrase in docs

    print("Everkeep Phase 2 preservation and portability validation passed")


if __name__ == "__main__":
    main()
