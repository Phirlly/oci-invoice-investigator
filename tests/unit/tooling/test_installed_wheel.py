import subprocess

import pytest


def test_smoke_environment_removes_editable_import_overrides(load_tool, tmp_path):
    tool = load_tool("check_installed_wheel")
    env = tool.smoke_environment(
        tmp_path,
        {
            "PYTHONPATH": "/checkout/src",
            "PYTHONHOME": "/other/python",
            "VIRTUAL_ENV": "/checkout/.venv",
            "UV_PROJECT_ENVIRONMENT": "/checkout/.venv",
            "PYTEST_ADDOPTS": "--ignore=tests/ui",
            "PATH": "/bin",
        },
    )
    assert (
        not {"PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT", "PYTEST_ADDOPTS"}
        & env.keys()
    )
    assert env["PYTHONNOUSERSITE"] == "1"
    assert env["PATH"] == "/bin"
    assert env["PLAYWRIGHT_BROWSERS_PATH"] == str(tmp_path / ".cache/ms-playwright")


def test_failed_smoke_cleans_owned_temporary_directory(load_tool, tmp_path, monkeypatch):
    tool = load_tool("check_installed_wheel")
    seen = []
    monkeypatch.setattr(tool.shutil, "which", lambda _: "/bin/uv")

    def fail(uv, root, base, env):
        assert not base.is_relative_to(root)
        seen.append(base)
        (base / "owned-file").write_text("temporary")
        raise subprocess.CalledProcessError(1, ["uv"])

    monkeypatch.setattr(tool, "verify_installation", fail)
    with pytest.raises(subprocess.CalledProcessError):
        tool.check_wheel(tmp_path)
    assert len(seen) == 1
    assert not seen[0].exists()
