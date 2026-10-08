"""Bounded OCI child process with signing-only stdin and a closed output contract."""

import json
import os
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from .errors import PreflightError
from .reporting import ERROR_FIELDS, PHASES, REMEDIATION


def _read_result(result):
    try:
        if len(result.stdout) > 4096:
            raise ValueError
        data = json.loads(result.stdout)
        if result.returncode == 0 and data == {"status": "PASSED"}:
            return
        if (
            result.returncode != 1
            or not isinstance(data, dict)
            or set(data) != {"status", "phase", "code", "field"}
            or data["status"] != "FAILED"
            or data["phase"] not in PHASES
            or data["code"] not in REMEDIATION
            or (data["field"] is not None and data["field"] not in ERROR_FIELDS)
        ):
            raise ValueError
    except (ValueError, TypeError, RecursionError):
        raise PreflightError("probe", "probe_failed") from None
    raise PreflightError(data["phase"], data["code"], data["field"])


def run_probe(config, credentials):
    payload = {
        "configuration": asdict(config),
        "private_key": credentials.private_key,
        "passphrase": credentials.passphrase,
    }
    try:
        result = subprocess.run(
            [sys.executable, "-B", "-s", "-m", "deployment._probe"],
            cwd=Path(__file__).resolve().parents[1],
            env={
                "LANG": "C.UTF-8",
                "PYTHONNOUSERSITE": "1",
                "OCI_DEVELOPER_TOOL_CONFIGURATION_FILE_PATH": os.devnull,
            },
            input=json.dumps(payload),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=60,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise PreflightError("probe", "probe_timeout") from None
    except (OSError, UnicodeError):
        raise PreflightError("probe", "probe_failed") from None
    _read_result(result)
