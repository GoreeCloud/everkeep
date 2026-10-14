#!/usr/bin/env python3
"""Safety checks for a planning-only Wardveil recovery preflight."""
from wardveil_cloudflare_restore_preflight import ALL_GATES, SOURCE_SHA, TARGET_ID, evaluate_preflight


def expect_invalid(value):
    try:
        evaluate_preflight(value)
    except ValueError:
        return
    raise AssertionError("invalid input should be rejected")


def main():
    blocked = evaluate_preflight()
    assert blocked["planningStatus"] == "blocked"
    assert blocked["engineExecutionAuthorized"] is False
    assert blocked["restorePerformed"] is False
    assert blocked["wardveilRuntimeAccepted"] is False
    assert blocked["sourceMutationAllowed"] is False
    assert blocked["proposedStepOrder"] == ["validate", "stage", "restore", "verify"]

    expect_invalid({"deployedRevision": "b" * 40})
    expect_invalid({"isolatedTargetId": TARGET_ID})
    expect_invalid({"gates": []})
    expect_invalid({"gates": {"identity-authorized": {"state": "other"}}})

    claimed = {
        "deployedRevision": SOURCE_SHA,
        "isolatedTargetId": "sandbox-wardveil-restore-test",
        "gates": {
            gate: {"state": "pass", "evidenceRef": "claim:" + str(i)}
            for i, gate in enumerate(ALL_GATES)
        },
    }
    result = evaluate_preflight(claimed)
    assert result["planningStatus"] == "requires_independent_authoritative_review"
    assert result["engineExecutionAuthorized"] is False
    assert result["restorePerformed"] is False
    assert result["authoritativeRestoreEvidenceIssued"] is False
    assert result["securityStateAuthorityTransferred"] is False
    print("Wardveil restore preflight safety tests passed.")


if __name__ == "__main__":
    main()
