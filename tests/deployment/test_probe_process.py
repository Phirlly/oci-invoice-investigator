import json
import subprocess
from types import SimpleNamespace as Result

import pytest

from deployment.configuration import parse_configuration
from deployment.credentials import load_credentials
from deployment.errors import PreflightError
from deployment.probe_process import run_probe


def test_probe_gets_only_signing_secret_over_stdin(credential_environment, monkeypatch):
    config = parse_configuration(credential_environment["DEPLOYMENT_CONFIG"])
    credentials = load_credentials(credential_environment, config.fingerprint)
    seen = []

    def execute(args, **kwargs):
        seen.append((args, kwargs))
        return Result(returncode=0, stdout='{"status":"PASSED"}')

    monkeypatch.setattr("deployment.probe_process.subprocess.run", execute)
    monkeypatch.setenv("OCI_CONFIG_FILE", "/private/untrusted-profile")
    monkeypatch.setenv("HTTPS_PROXY", "https://untrusted.invalid")
    run_probe(config, credentials)
    args, kwargs = seen[0]
    payload = json.loads(kwargs["input"])
    assert payload["private_key"] == credentials.private_key
    assert credentials.private_key not in " ".join(args)
    assert credentials.openai_key not in kwargs["input"]
    assert credentials.presenter_password not in kwargs["input"]
    assert "OCI_CONFIG_FILE" not in kwargs["env"]
    assert "HTTPS_PROXY" not in kwargs["env"]
    assert kwargs["timeout"] == 60
    assert kwargs["stderr"] == subprocess.DEVNULL


@pytest.mark.parametrize(
    "output,returncode",
    [
        ("sensitive-diagnostic", 1),
        ('{"status":"PASSED","secret":"value"}', 0),
        ('{"status":"PASSED"}', 1),
        ("[]", 0),
        (" " * 5000, 0),
        ('{"status":"FAILED","phase":"user","code":"sensitive","field":null}', 1),
        ('{"status":"FAILED","phase":[],"code":"probe_failed","field":null}', 1),
        ('{"status":"FAILED","phase":"user","code":[],"field":null}', 1),
        ('{"status":"FAILED","phase":"user","code":"request_failed","field":[]}', 1),
    ],
)
def test_untrusted_child_output_cannot_escape(
    credential_environment, monkeypatch, output, returncode
):
    config = parse_configuration(credential_environment["DEPLOYMENT_CONFIG"])
    credentials = load_credentials(credential_environment, config.fingerprint)
    monkeypatch.setattr(
        "deployment.probe_process.subprocess.run",
        lambda *a, **k: Result(returncode=returncode, stdout=output),
    )
    with pytest.raises(PreflightError) as failure:
        run_probe(config, credentials)
    assert failure.value.code == "probe_failed"
    assert "sensitive" not in str(failure.value)


def test_child_timeout_is_bounded_and_sanitized(credential_environment, monkeypatch):
    config = parse_configuration(credential_environment["DEPLOYMENT_CONFIG"])
    credentials = load_credentials(credential_environment, config.fingerprint)

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("child", 60, output="sensitive-output")

    monkeypatch.setattr("deployment.probe_process.subprocess.run", timeout)
    with pytest.raises(PreflightError) as failure:
        run_probe(config, credentials)
    assert failure.value.code == "probe_timeout"
    assert "sensitive-output" not in str(failure.value)


def test_owned_child_failure_retains_safe_phase(credential_environment, monkeypatch):
    config = parse_configuration(credential_environment["DEPLOYMENT_CONFIG"])
    credentials = load_credentials(credential_environment, config.fingerprint)
    monkeypatch.setattr(
        "deployment.probe_process.subprocess.run",
        lambda *a, **k: Result(
            returncode=1,
            stdout='{"status":"FAILED","phase":"user","code":"access_denied","field":null}',
        ),
    )
    with pytest.raises(PreflightError) as failure:
        run_probe(config, credentials)
    assert (failure.value.phase, failure.value.code) == ("user", "access_denied")


def test_unavailable_child_is_reported_without_os_diagnostic(credential_environment, monkeypatch):
    config = parse_configuration(credential_environment["DEPLOYMENT_CONFIG"])
    credentials = load_credentials(credential_environment, config.fingerprint)

    def unavailable(*args, **kwargs):
        raise OSError("sensitive-os-diagnostic")

    monkeypatch.setattr("deployment.probe_process.subprocess.run", unavailable)
    with pytest.raises(PreflightError) as failure:
        run_probe(config, credentials)
    assert str(failure.value) == "probe: probe_failed"
