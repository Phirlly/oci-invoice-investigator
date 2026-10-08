"""Exercise the built wheel outside the checkout with hash-locked dependencies."""

import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def smoke_environment(root, inherited):
    environment = dict(inherited)
    for name in (
        "PYTHONPATH",
        "PYTHONHOME",
        "VIRTUAL_ENV",
        "UV_PROJECT_ENVIRONMENT",
        "PYTEST_ADDOPTS",
    ):
        environment.pop(name, None)
    environment["PYTHONNOUSERSITE"] = "1"
    environment["UV_CACHE_DIR"] = str(root / ".cache/uv")
    environment["PLAYWRIGHT_BROWSERS_PATH"] = str(
        Path(inherited.get("PLAYWRIGHT_BROWSERS_PATH", root / ".cache/ms-playwright")).resolve()
    )
    return environment


def run(arguments, cwd, env, timeout=240):
    return subprocess.run(arguments, cwd=cwd, env=env, check=True, timeout=timeout)


def verify_installation(uv, root, base, env):
    project = tomllib.loads((root / "pyproject.toml").read_text())["project"]
    stem = project["name"].replace("-", "_") + "-" + project["version"]
    wheel = root / "dist" / f"{stem}-py3-none-any.whl"
    source_archive = root / "dist" / f"{stem}.tar.gz"
    if not wheel.is_file() or not source_archive.is_file():
        raise ValueError("Build the current wheel and source distribution before checking them.")
    requirements = base / "requirements.txt"
    run(
        [
            uv,
            "export",
            "--quiet",
            "--locked",
            "--all-groups",
            "--no-emit-project",
            "--output-file",
            str(requirements),
        ],
        root,
        env,
    )
    environment = base / "environment"
    run([uv, "venv", "--python", sys.executable, str(environment)], base, env)
    python = environment / "bin/python"
    run(
        [
            uv,
            "pip",
            "install",
            "--python",
            str(python),
            "--require-hashes",
            "-r",
            str(requirements),
        ],
        base,
        env,
    )
    run([uv, "pip", "install", "--python", str(python), "--no-deps", str(wheel)], base, env)
    with tarfile.open(source_archive) as archive:
        archive.extractall(base, filter="data")
    source = base / stem
    run(
        [
            str(python),
            "-I",
            "-c",
            "from pathlib import Path; import sys; "
            "import invoice_investigator.web.configuration as m; "
            "p = Path(m.__file__).resolve(); "
            "assert p.is_relative_to(Path(sys.prefix).resolve()) and 'site-packages' in p.parts; "
            "print('Fresh installed-wheel import verified.')",
        ],
        base,
        env,
    )
    for case, expected in (("case-001", "no_discrepancy"), ("case-002", "needs_review")):
        sample = source / "examples/invoices" / case
        result = subprocess.run(
            [
                str(environment / "bin/invoice-investigator"),
                "--invoice",
                str(sample / "normalized_invoice.json"),
                "--evidence",
                str(sample),
            ],
            cwd=base,
            env=env,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if json.loads(result.stdout)["conclusion"] != expected:
            raise ValueError(f"Installed CLI failed expected outcome for {case}.")
    run(
        [
            str(python),
            str(source / "tools/run_web_checks.py"),
            "tests/integration/case_storage",
            "tests/integration/web",
            "tests/ui",
            "-q",
        ],
        base,
        env,
        timeout=900,
    )
    print(
        "Installed wheel passed both CLI samples and PostgreSQL/Chromium checks outside checkout."
    )


def check_wheel(root=ROOT):
    uv = shutil.which("uv")
    if not uv:
        raise ValueError("uv must be available on PATH.")
    with tempfile.TemporaryDirectory(prefix="invoice-wheel-") as temporary:
        base = Path(temporary).resolve()
        if base.is_relative_to(root.resolve()):
            raise ValueError("The system temporary directory must be outside the checkout.")
        verify_installation(uv, root, base, smoke_environment(root, os.environ))


if __name__ == "__main__":
    check_wheel()
