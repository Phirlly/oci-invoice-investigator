"""Owned diagnostics; provider messages and credential values never reach reports."""

from .configuration import FIELDS
from .errors import PreflightError

REMEDIATION = {
    "configuration_invalid": "Supply the exact versioned configuration fields and valid values.",
    "credential_invalid": "Supply the named secret through the configured secret environment.",
    "private_key_invalid": "Use an RSA private key (2048+ bits) with the correct passphrase.",
    "key_fingerprint_mismatch": "Match the configured fingerprint to the supplied OCI signing key.",
    "authentication_rejected": "Verify the registered API key, active user, region and clock.",
    "access_denied": "Verify identity read permissions for the configured target.",
    "unavailable_or_unauthorized": "Verify the target identifiers and identity read permissions.",
    "throttled": "Wait before retrying the read-only preflight.",
    "service_unavailable": "Check OCI service availability before retrying.",
    "request_timeout": "Check connectivity to the regional OCI Identity endpoint and retry.",
    "request_failed": "Check OCI connectivity and the configured identity read permissions.",
    "unexpected_response": "Verify the target and SDK compatibility before retrying.",
    "identity_mismatch": "Verify the active user and tenancy belong to the configured identity.",
    "region_unavailable": "Verify the workload and home region subscriptions are ready.",
    "unsupported_region": "Use an OC1 region recognized by the pinned OCI SDK.",
    "target_mismatch": "Verify the active compartment ancestry reaches the configured tenancy.",
    "probe_failed": "Check the locked deployment dependencies and rerun the preflight.",
    "probe_timeout": "Check OCI connectivity; the read-only probe exceeded its 60-second deadline.",
}
PHASES = frozenset(
    {"configuration", "credentials", "user", "tenancy", "regions", "compartment", "probe"}
)
ERROR_FIELDS = FIELDS | {
    "OCI_API_PRIVATE_KEY",
    "OCI_KEY_PASSPHRASE",
    "OPENAI_API_KEY",
    "PRESENTER_PASSWORD",
}


def safe_error(error):
    if (
        error.phase not in PHASES
        or error.code not in REMEDIATION
        or (error.field is not None and error.field not in ERROR_FIELDS)
    ):
        error = PreflightError("probe", "probe_failed")
    return {
        "phase": error.phase,
        "code": error.code,
        "field": error.field,
        "remediation": REMEDIATION[error.code],
    }
