import io
import json
import tarfile
from types import SimpleNamespace


def test_wheel_smoke_runs_before_deployment_dependencies(load_tool, tmp_path, monkeypatch):
    tool = load_tool("check_installed_wheel")
    root = tmp_path / "checkout"
    root.mkdir()
    (root / "pyproject.toml").write_text('[project]\nname="sample"\nversion="1.0"\n')
    (root / "dist").mkdir()
    (root / "dist/sample-1.0-py3-none-any.whl").touch()
    with tarfile.open(root / "dist/sample-1.0.tar.gz", "w:gz") as archive:
        member = tarfile.TarInfo("sample-1.0/README.md")
        member.size = 4
        archive.addfile(member, io.BytesIO(b"demo"))
    base = tmp_path / "isolated"
    base.mkdir()
    calls = []

    def run(args, **kwargs):
        calls.append((args, kwargs))
        if "--invoice" in args:
            expected = "no_discrepancy" if "case-001" in " ".join(args) else "needs_review"
            return SimpleNamespace(stdout=json.dumps({"conclusion": expected}))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(tool.subprocess, "run", run)
    tool.verify_installation("uv", root, base, {})
    exports = [(i, args) for i, (args, _) in enumerate(calls) if "export" in args]
    assert len(exports) == 2
    assert "--no-default-groups" in exports[0][1]
    assert "--all-groups" in exports[1][1]
    cli_indexes = [i for i, (args, _) in enumerate(calls) if "--invoice" in args]
    assert exports[0][0] < min(cli_indexes) < max(cli_indexes) < exports[1][0]
    assert any(
        "tests/deployment" in args and kwargs["cwd"] == base / "sample-1.0"
        for args, kwargs in calls
    )
