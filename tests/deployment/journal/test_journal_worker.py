import io
import json
from dataclasses import asdict

import pytest

from deployment import _journal
from deployment.journal_request import Command, Context


@pytest.fixture
def payload(credential_environment):
    return {
        "configuration": json.loads(credential_environment["DEPLOYMENT_CONFIG"]),
        "private_key": credential_environment["OCI_API_PRIVATE_KEY"],
        "passphrase": None,
        "github_token": "synthetic-token",
        "context": asdict(Context("example/invoices", 12345, "a" * 40)),
        "command": Command("status").to_dict(),
    }


def test_worker_validates_then_constructs_lazy_adapters(payload, monkeypatch):
    calls = []

    def controller(config, context, anchors, storage, home):
        calls.append((config, context, anchors))

        class Runner:
            def execute(self, command):
                assert command == Command("status")
                return {"status": "JOURNAL_STATUS", "revision": 0, "operation": None}

        return Runner()

    monkeypatch.setattr(_journal, "JournalController", controller)
    result = _journal.journal_payload(json.dumps(payload))
    assert result["status"] == "JOURNAL_STATUS"
    assert len(calls) == 1


@pytest.mark.parametrize(
    "change",
    [
        {"command": {"action": "shell"}},
        {"private_key": "sensitive"},
        {"github_token": "bad\r\ntoken"},
        {"extra": "secret"},
    ],
)
def test_bad_payload_never_constructs_controller(payload, monkeypatch, change):
    monkeypatch.setattr(_journal, "JournalController", lambda *a: pytest.fail("constructed"))
    result = _journal.journal_payload(json.dumps({**payload, **change}))
    assert result["status"] == "FAILED"
    assert "sensitive" not in str(result)


def test_unexpected_exception_has_no_raw_diagnostics(payload, monkeypatch):
    def broken(*args):
        raise RuntimeError("sensitive diagnostic")

    monkeypatch.setattr(_journal, "JournalController", broken)
    assert _journal.journal_payload(json.dumps(payload)) == {
        "status": "FAILED",
        "code": "outcome_unknown",
    }


def test_entrypoint_reads_bounded_input_and_only_prints_safe_json(monkeypatch, capsys):
    monkeypatch.setattr(_journal.sys, "stdin", io.StringIO("sensitive" * 10000))
    monkeypatch.setattr(_journal.logging, "disable", lambda level: None)
    assert _journal.main() == 1
    captured = capsys.readouterr()
    assert json.loads(captured.out) == {"status": "FAILED", "code": "journal_invalid"}
    assert captured.err == ""
