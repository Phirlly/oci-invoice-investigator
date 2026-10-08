import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from deployment._probe import probe_payload


def payload(environment):
    return json.dumps(
        {
            "configuration": json.loads(environment["DEPLOYMENT_CONFIG"]),
            "private_key": environment["OCI_API_PRIVATE_KEY"],
            "passphrase": None,
        }
    )


def test_worker_revalidates_and_runs_only_identity_reads(
    credential_environment, read_client, monkeypatch
):
    monkeypatch.setattr("deployment._probe.build_client", lambda *args: read_client)
    result = probe_payload(payload(credential_environment))
    assert result == {"status": "PASSED"}
    assert [call[0] for call in read_client.calls] == [
        "get_user",
        "get_tenancy",
        "list_region_subscriptions",
        "get_compartment",
    ]


@pytest.mark.parametrize("raw", ["sensitive-invalid", "{}", "[]", " " * 65_537])
def test_worker_rejects_bad_input_without_raw_output(raw):
    assert probe_payload(raw) == {
        "status": "FAILED",
        "phase": "probe",
        "code": "probe_failed",
        "field": None,
    }


def test_worker_suppresses_unexpected_sdk_diagnostics(credential_environment, monkeypatch):
    def fail(*args):
        raise RuntimeError("sensitive-sdk-diagnostic")

    monkeypatch.setattr("deployment._probe.build_client", fail)
    assert probe_payload(payload(credential_environment))["code"] == "probe_failed"


def test_real_child_rejects_unknown_region_before_network(credential_environment):
    data = json.loads(credential_environment["DEPLOYMENT_CONFIG"])
    data["region"] = "zz-unlisted-1"
    credential_environment["DEPLOYMENT_CONFIG"] = json.dumps(data)
    result = subprocess.run(
        [sys.executable, "-B", "-s", "-m", "deployment._probe"],
        cwd=Path(__file__).resolve().parents[2],
        env={"OCI_DEVELOPER_TOOL_CONFIGURATION_FILE_PATH": os.devnull},
        input=payload(credential_environment),
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 1
    assert json.loads(result.stdout) == {
        "status": "FAILED",
        "phase": "regions",
        "code": "unsupported_region",
        "field": None,
    }
    assert not result.stderr
