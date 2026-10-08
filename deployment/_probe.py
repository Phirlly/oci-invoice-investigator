"""Private child entrypoint. Never emit SDK responses, inventory or raw exceptions."""

import json
import logging
import sys

from .configuration import parse_configuration
from .credentials import load_signing_credentials
from .errors import PreflightError
from .oci_client import build_client
from .oci_read_checks import check_read_access
from .reporting import safe_error


def probe_payload(raw):
    try:
        if len(raw) > 65_536:
            raise ValueError
        data = json.loads(raw)
        if not isinstance(data, dict) or set(data) != {
            "configuration",
            "private_key",
            "passphrase",
        }:
            raise ValueError
        config = parse_configuration(json.dumps(data["configuration"]))
        credentials = load_signing_credentials(
            {"OCI_API_PRIVATE_KEY": data["private_key"], "OCI_KEY_PASSPHRASE": data["passphrase"]},
            config.fingerprint,
        )
        check_read_access(config, lambda region: build_client(config, credentials, region))
        return {"status": "PASSED"}
    except PreflightError as error:
        report = safe_error(error)
        report.pop("remediation")
        return {"status": "FAILED", **report}
    except Exception:
        return {"status": "FAILED", "phase": "probe", "code": "probe_failed", "field": None}


def main():
    logging.disable(logging.CRITICAL)
    result = probe_payload(sys.stdin.read(65_537))
    print(json.dumps(result))
    return 0 if result["status"] == "PASSED" else 1


if __name__ == "__main__":
    sys.exit(main())
