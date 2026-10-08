"""Private controller subprocess with a hard wall deadline and closed output."""

import os
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from . import journal_schema as schema
from .journal_errors import CODES, JournalError, require
from .journal_operations import Operation

STATUSES = frozenset(
    {"JOURNAL_STATUS", "JOURNAL_INITIALIZED", "OPERATION_PENDING", "OPERATION_COMPLETED"}
)


def _read_result(result):
    try:
        require(len(result.stdout) <= 4096)
        data = schema.decode(result.stdout)
        require(isinstance(data, dict))
        if result.returncode == 1:
            schema.fields(data, {"status", "code"})
            require(
                data["status"] == "FAILED"
                and isinstance(data["code"], str)
                and data["code"] in CODES
            )
            code = data["code"]
        else:
            require(result.returncode == 0)
            schema.fields(data, {"status", "revision", "operation"})
            require(isinstance(data["status"], str) and data["status"] in STATUSES)
            schema.integer(data["revision"])
            operation = None if data["operation"] is None else Operation.parse(data["operation"])
            require((data["revision"] == 0) == (operation is None))
            if data["status"].startswith("OPERATION_"):
                require(
                    operation is not None
                    and data["status"] == "OPERATION_" + operation.state.upper()
                )
            return data
    except Exception:
        raise JournalError("outcome_unknown") from None
    raise JournalError(code)


def run_journal_command(config, credentials, github_token, context, command):
    payload = {
        "configuration": asdict(config),
        "private_key": credentials.private_key,
        "passphrase": credentials.passphrase,
        "github_token": github_token,
        "context": asdict(context),
        "command": command.to_dict(),
    }
    raw = schema.encode(payload)
    require(len(raw.encode()) <= schema.LIMIT)
    try:
        result = subprocess.run(
            [sys.executable, "-B", "-s", "-m", "deployment._journal"],
            cwd=Path(__file__).resolve().parents[1],
            env={
                "LANG": "C.UTF-8",
                "PYTHONNOUSERSITE": "1",
                "OCI_DEVELOPER_TOOL_CONFIGURATION_FILE_PATH": os.devnull,
                "OCI_HEADER_PARSING_ERROR_MAX_RETRIES": "0",
            },
            input=raw,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=60,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError, UnicodeError):
        raise JournalError("outcome_unknown") from None
    return _read_result(result)
