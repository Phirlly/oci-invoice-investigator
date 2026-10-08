import json

import pytest


def test_only_exact_reviewed_file_type_and_digest_are_accepted(load_tool):
    tool = load_tool("check_secrets")
    reviewed = {("source.py", "Secret Keyword", "a" * 40)}
    tool.check_findings(reviewed, reviewed)
    for candidate in (
        ("other.py", "Secret Keyword", "a" * 40),
        ("source.py", "AWS Access Key", "a" * 40),
        ("source.py", "Secret Keyword", "b" * 40),
    ):
        with pytest.raises(tool.GateError, match="Unreviewed"):
            tool.check_findings(reviewed | {candidate}, reviewed)


def test_removed_findings_require_allowlist_cleanup(load_tool):
    tool = load_tool("check_secrets")
    with pytest.raises(tool.GateError, match="Stale"):
        tool.check_findings(set(), {("source.py", "Secret Keyword", "a" * 40)})


@pytest.mark.parametrize("digest", ["plaintext", "g" * 40, None])
def test_allowlist_rejects_malformed_fingerprints(load_tool, tmp_path, digest):
    tool = load_tool("check_secrets")
    path = tmp_path / "reviewed.json"
    path.write_text(
        json.dumps(
            {"source.py": {"reason": "Synthetic test", "findings": [["Secret Keyword", digest]]}}
        )
    )
    with pytest.raises(tool.GateError, match="allowlist"):
        tool.load_allowlist(path)


@pytest.mark.parametrize("report", [{}, {"results": []}, {"results": {"source.py": [{}]}}])
def test_incomplete_scanner_report_cannot_pass(load_tool, report):
    tool = load_tool("check_secrets")
    with pytest.raises(tool.GateError, match="report"):
        tool.fingerprints(
            {"version": "1.5.0", "plugins_used": [{"name": "AWSKeyDetector"}], **report}
        )
