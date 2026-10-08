"""Own one short-lived PostgreSQL test container; never reuse an operator database."""

import json
import os
import secrets
import subprocess
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

import psycopg

DIGESTS = {
    "arm64": "a85953d6f830fd55a12929df3b7a4fa94dc96d652de62d2d714e0867ccb3670d",
    "amd64": "66aafa11cf15800a3c94763f7e11d1e7b2e37e5e84bc4ce027cb6e1e4bfaf4df",
}


def docker(*args, timeout=20):
    return subprocess.run(
        ["docker", *args], check=True, capture_output=True, text=True, timeout=timeout
    ).stdout.strip()


@contextmanager
def isolated_database():
    architecture = docker("info", "--format", "{{.Architecture}}")
    architecture = {"aarch64": "arm64", "x86_64": "amd64"}.get(architecture, architecture)
    if architecture not in DIGESTS:
        raise RuntimeError("Local checks support Docker linux/amd64 and linux/arm64.")
    image = "public.ecr.aws/docker/library/postgres@sha256:" + DIGESTS[architecture]
    name = "invoice-check-" + secrets.token_hex(6)
    password = secrets.token_urlsafe(32)
    with tempfile.TemporaryDirectory(prefix="invoice-check-") as temporary:
        secret_file = Path(temporary) / "database.env"
        secret_file.touch(mode=0o600)
        secret_file.write_text(
            f"POSTGRES_USER=invoice_checks\nPOSTGRES_DB=invoice_checks\nPOSTGRES_PASSWORD={password}\n"
        )
        try:
            docker(
                "run",
                "--detach",
                "--name",
                name,
                "--label",
                "invoice-investigator.check=true",
                "--env-file",
                str(secret_file),
                "--publish",
                "127.0.0.1::5432",
                "--tmpfs",
                "/var/lib/postgresql/data:rw,size=512m",
                image,
                timeout=180,
            )
            bindings = json.loads(
                docker("inspect", name, "--format", "{{json .NetworkSettings.Ports}}")
            )
            published = bindings["5432/tcp"]
            if len(published) != 1 or published[0]["HostIp"] != "127.0.0.1":
                raise RuntimeError("Test database is not bound exclusively to loopback.")
            port = int(published[0]["HostPort"])
            deadline = time.monotonic() + 45
            while True:
                try:
                    with psycopg.connect(
                        host="127.0.0.1",
                        port=port,
                        dbname="invoice_checks",
                        user="invoice_checks",
                        password=password,
                        connect_timeout=2,
                    ) as connection:
                        version = connection.execute("SHOW server_version_num").fetchone()[0]
                        if version != "170011":
                            raise RuntimeError("Unexpected PostgreSQL test image version.")
                    break
                except psycopg.OperationalError:
                    if time.monotonic() >= deadline:
                        raise RuntimeError("Isolated PostgreSQL readiness timed out.") from None
                    time.sleep(0.2)
            yield {
                "II_CHECK_PORT": str(port),
                "II_CHECK_PASSWORD": password,
                "II_CHECK_ISOLATED": "1",
            }
        finally:
            secret_file.unlink(missing_ok=True)
            # Remove only this unpredictable, invocation-owned name, including anonymous volumes.
            result = subprocess.run(
                ["docker", "rm", "--force", "--volumes", name],
                capture_output=True,
                text=True,
                timeout=20,
            )
            if result.returncode and "No such container" not in result.stderr:
                raise RuntimeError(f"Could not remove test container {name}; inspect it locally.")


def test_environment(database, root):
    return {
        **os.environ,
        **database,
        "PYTHONPATH": str(root / "tests"),
        "PLAYWRIGHT_BROWSERS_PATH": os.environ.get(
            "PLAYWRIGHT_BROWSERS_PATH", str(root / ".cache/ms-playwright")
        ),
        "DJANGO_SETTINGS_MODULE": "web_test_settings",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
    }
