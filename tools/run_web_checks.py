"""Run the explicit PostgreSQL/browser lane with automatic isolated DB cleanup."""

import subprocess
import sys
from pathlib import Path

from check_database import isolated_database, test_environment

ROOT = Path(__file__).resolve().parents[1]


def main():
    arguments = sys.argv[1:] or [
        "tests/integration/case_storage",
        "tests/integration/web",
        "tests/ui",
    ]
    with isolated_database() as database:
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-p",
                "pytest_django.plugin",
                "-p",
                "web_support",
                "--ds=web_test_settings",
                "-o",
                "session_timeout=300",
                *arguments,
            ],
            env=test_environment(database, ROOT),
            cwd=ROOT,
            timeout=360,
        ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
