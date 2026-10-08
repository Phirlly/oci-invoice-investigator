from deployment.errors import PreflightError
from deployment.preflight import preflight


def test_local_checks_never_claim_readiness_or_make_requests(credential_environment):
    def forbidden(*args):
        raise AssertionError("Unexpected network boundary")

    result = preflight(credential_environment, probe=forbidden)
    assert result["status"] == "LOCAL_CHECKS_PASSED"
    assert result["deployment_ready"] is False
    assert "oci_read_access" in result["not_checked"]
    assert "openai_access" in result["not_checked"]
    assert "presenter_password_policy" in result["not_checked"]


def test_explicit_probe_pass_does_not_claim_provisioning_permission(credential_environment):
    calls = []
    result = preflight(
        credential_environment, check_oci=True, probe=lambda *args: calls.append(args)
    )
    assert len(calls) == 1
    assert result["status"] == "OCI_READ_CHECKS_PASSED"
    assert result["deployment_ready"] is False
    assert "provisioning_permissions" in result["not_checked"]
    assert "oci_read_access" not in result["not_checked"]


def test_invalid_configuration_stops_before_credentials_or_probe():
    result = preflight(
        {"DEPLOYMENT_CONFIG": "sensitive-invalid-config"},
        check_oci=True,
        probe=lambda *args: (_ for _ in ()).throw(AssertionError()),
    )
    assert result["status"] == "FAILED"
    assert result["error"]["phase"] == "configuration"
    assert "sensitive" not in str(result)


def test_denial_has_actionable_owned_message(credential_environment):
    def denied(*args):
        raise PreflightError("compartment", "unavailable_or_unauthorized")

    result = preflight(credential_environment, check_oci=True, probe=denied)
    assert result["status"] == "FAILED"
    assert result["error"]["code"] == "unavailable_or_unauthorized"
    assert "permissions" in result["error"]["remediation"]
    for key in ("OCI_API_PRIVATE_KEY", "OPENAI_API_KEY", "PRESENTER_PASSWORD"):
        assert credential_environment[key] not in str(result)
