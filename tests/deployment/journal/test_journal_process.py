import json
import subprocess
import sys
import time
from dataclasses import asdict
from types import SimpleNamespace as Record

import pytest

from deployment.credentials import SigningCredentials
from deployment.journal_errors import JournalError
from deployment.journal_process import run_journal_command
from deployment.journal_request import Command, Context

CONTEXT = Context("example/invoices", 12345, "a" * 40)
RESULT = {"status": "JOURNAL_STATUS", "revision": 0, "operation": None}


def run(config):
    return run_journal_command(
        config,
        SigningCredentials("synthetic-key", None),
        "synthetic-token",
        CONTEXT,
        Command("status"),
    )


def test_child_receives_only_signing_secrets_on_stdin_and_safe_environment(config, monkeypatch):
    calls = []

    def child(args, **kwargs):
        calls.append((args, kwargs))
        return Record(returncode=0, stdout=json.dumps(RESULT))

    monkeypatch.setattr("deployment.journal_process.subprocess.run", child)
    assert run(config) == RESULT
    args, kwargs = calls[0]
    assert args == [sys.executable, "-B", "-s", "-m", "deployment._journal"]
    assert "synthetic" not in str(args)
    assert kwargs["timeout"] == 60
    assert kwargs["stderr"] == subprocess.DEVNULL
    assert set(kwargs["env"]) == {
        "LANG",
        "PYTHONNOUSERSITE",
        "OCI_DEVELOPER_TOOL_CONFIGURATION_FILE_PATH",
        "OCI_HEADER_PARSING_ERROR_MAX_RETRIES",
    }
    assert kwargs["env"]["OCI_HEADER_PARSING_ERROR_MAX_RETRIES"] == "0"
    payload = json.loads(kwargs["input"])
    assert payload == {
        "configuration": asdict(config),
        "private_key": "synthetic-key",
        "passphrase": None,
        "github_token": "synthetic-token",
        "context": asdict(CONTEXT),
        "command": Command("status").to_dict(),
    }


@pytest.mark.parametrize(
    "result",
    [
        Record(returncode=0, stdout='{"status":"READY"}'),
        Record(returncode=0, stdout=json.dumps({**RESULT, "private_key": "sensitive"})),
        Record(returncode=1, stdout='{"status":"FAILED","code":"sensitive"}'),
        Record(returncode=0, stdout="sensitive"),
        Record(returncode=0, stdout=" " * 4097),
    ],
)
def test_untrusted_child_output_cannot_escape(result, config, monkeypatch):
    monkeypatch.setattr("deployment.journal_process.subprocess.run", lambda *a, **k: result)
    with pytest.raises(JournalError, match="outcome_unknown") as failure:
        run(config)
    assert "sensitive" not in str(failure.value)


def test_known_child_error_is_preserved(config, monkeypatch):
    monkeypatch.setattr(
        "deployment.journal_process.subprocess.run",
        lambda *a, **k: Record(returncode=1, stdout='{"status":"FAILED","code":"operation_busy"}'),
    )
    with pytest.raises(JournalError, match="operation_busy"):
        run(config)


def test_real_subprocess_deadline_returns_unknown_instead_of_retry(config, monkeypatch):
    original = subprocess.run
    calls = []

    def stalled_child(args, **kwargs):
        calls.append(args)
        kwargs["timeout"] = 0.1
        return original([sys.executable, "-c", "import time; time.sleep(30)"], **kwargs)

    monkeypatch.setattr("deployment.journal_process.subprocess.run", stalled_child)
    start = time.monotonic()
    with pytest.raises(JournalError, match="outcome_unknown"):
        run(config)
    assert time.monotonic() - start < 3
    assert len(calls) == 1
