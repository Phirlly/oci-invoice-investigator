"""Configuration and credential preflight; explicitly not a deployment readiness gate."""

from .configuration import parse_configuration
from .credentials import load_credentials
from .errors import PreflightError
from .probe_process import run_probe
from .reporting import safe_error


def preflight(environment, *, check_oci=False, probe=run_probe):
    result = {
        "status": "FAILED",
        "deployment_ready": False,
        "not_checked": [
            "oci_read_access",
            "provisioning_permissions",
            "service_capacity",
            "openai_access",
            "presenter_password_policy",
            "service_journey",
        ],
    }
    try:
        config = parse_configuration(environment.get("DEPLOYMENT_CONFIG"))
        credentials = load_credentials(environment, config.fingerprint)
        if check_oci:
            probe(config, credentials)
            result["not_checked"].remove("oci_read_access")
        result["status"] = "OCI_READ_CHECKS_PASSED" if check_oci else "LOCAL_CHECKS_PASSED"
    except PreflightError as error:
        result["error"] = safe_error(error)
    return result
