import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_offline_command_returns_safe_report_without_sdk_import(credential_environment, tmp_path):
    (tmp_path / "oci.py").write_text('raise RuntimeError("SDK_IMPORTED_OFFLINE")\n')
    result = subprocess.run(
        [sys.executable, "-m", "deployment"],
        cwd=ROOT,
        env={**os.environ, **credential_environment, "PYTHONPATH": str(tmp_path)},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "LOCAL_CHECKS_PASSED"
    assert not report["deployment_ready"]
    assert "SDK_IMPORTED_OFFLINE" not in result.stdout + result.stderr
    assert not result.stderr


def test_arguments_are_not_echoed():
    result = subprocess.run(
        [sys.executable, "-m", "deployment", "sensitive-argument-sentinel"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 2
    assert "sensitive-argument-sentinel" not in result.stdout + result.stderr


def test_collecting_deployment_tests_cannot_import_sdk(tmp_path):
    (tmp_path / "oci.py").write_text('raise RuntimeError("SDK_IMPORTED_DURING_COLLECTION")\n')
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "tests/deployment"],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(tmp_path)},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "SDK_IMPORTED_DURING_COLLECTION" not in result.stdout + result.stderr
