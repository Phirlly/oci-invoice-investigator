import subprocess

import pytest


@pytest.mark.parametrize("comment", ["", " # pragma: allowlist secret", "nextline"])
@pytest.mark.parametrize("filename", ["candidate.py", "package-lock.json", "swagger.json"])
def test_new_synthetic_candidate_is_detected_even_with_suppression(
    load_tool, tmp_path, comment, filename
):
    tool = load_tool("check_secrets")
    # Construct a deliberately fake AWS-shaped candidate; never verify it online.
    candidate = "AKIA" + "Q7T2F9N4R6D8S3V5"
    text = f'api_key = "{candidate}"'
    if comment == "nextline":
        text = "# pragma: allowlist nextline secret\n" + text
    else:
        text += comment
    (tmp_path / filename).write_text(text + "\n")
    findings = tool.scan(tmp_path, [filename])
    assert any(item[:2] == (filename, "AWS Access Key") for item in findings)
    with pytest.raises(tool.GateError, match="Unreviewed"):
        tool.check_findings(findings, set())


@pytest.mark.parametrize("failure", ["returncode", "stderr", "json", "timeout"])
def test_scanner_failure_is_closed_and_does_not_echo_payload(
    load_tool, tmp_path, monkeypatch, failure
):
    tool = load_tool("check_secrets")
    sentinel = "sensitive diagnostic payload"

    def broken(*args, **kwargs):
        if failure == "timeout":
            raise subprocess.TimeoutExpired("scanner", 120, output=sentinel)
        return subprocess.CompletedProcess(
            [],
            1 if failure == "returncode" else 0,
            stdout=sentinel if failure == "json" else "{}",
            stderr=sentinel if failure == "stderr" else "",
        )

    monkeypatch.setattr(tool.subprocess, "run", broken)
    with pytest.raises(tool.GateError) as error:
        tool.scan(tmp_path, ["source.py"])
    assert sentinel not in str(error.value)
