import os
import subprocess
import sys
from pathlib import Path


def test_inherited_django_settings_cannot_initialize_offline_collection(tmp_path):
    (tmp_path / "sentinel_settings.py").write_text(
        'raise RuntimeError("OFFLINE_SETTINGS_WERE_IMPORTED")\n'
    )
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "tests/unit/invoices"],
        cwd=root,
        env={
            **os.environ,
            "DJANGO_SETTINGS_MODULE": "sentinel_settings",
            "PYTHONPATH": str(tmp_path),
        },
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "OFFLINE_SETTINGS_WERE_IMPORTED" not in result.stdout + result.stderr
