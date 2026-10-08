"""Read-only engineering preflight: python -m deployment [--check-oci]."""

import json
import os
import sys

from .preflight import preflight


def main():
    arguments = sys.argv[1:]
    if arguments in (["-h"], ["--help"]):
        print(
            "Usage: python -m deployment [--check-oci]\n"
            "Default checks are local; --check-oci opts into OCI identity GET requests."
        )
        return 0
    if arguments not in ([], ["--check-oci"]):
        print('{"status":"FAILED","error":"unsupported_arguments"}')
        return 2
    result = preflight(os.environ, check_oci=bool(arguments))
    print(json.dumps(result, sort_keys=True))
    return 1 if result["status"] == "FAILED" else 0


if __name__ == "__main__":
    sys.exit(main())
