"""Fail on unreviewed scanner fingerprints without printing candidate values."""

import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
ALLOWLIST = "tools/secret_allowlist.json"
DISABLED_FILTERS = (
    "detect_secrets.filters.allowlist.is_line_allowlisted",
    "detect_secrets.filters.heuristic.is_lock_file",
    "detect_secrets.filters.heuristic.is_swagger_file",
)


class GateError(ValueError):
    """Safe diagnostic; never contains raw scanner output."""


def valid_fingerprint(filename, kind, digest):
    return (
        isinstance(filename, str)
        and filename == str(PurePosixPath(filename))
        and not PurePosixPath(filename).is_absolute()
        and ".." not in PurePosixPath(filename).parts
        and isinstance(kind, str)
        and bool(kind)
        and isinstance(digest, str)
        and re.fullmatch("[0-9a-f]{40}", digest) is not None
    )


def load_allowlist(path):
    try:
        document = json.loads(path.read_text())
        if not isinstance(document, dict):
            raise ValueError
        allowed = set()
        for filename, entry in document.items():
            if (
                set(entry) != {"reason", "findings"}
                or not isinstance(entry["reason"], str)
                or not entry["reason"].strip()
                or not isinstance(entry["findings"], list)
                or not entry["findings"]
            ):
                raise ValueError
            for kind, digest in entry["findings"]:
                item = (filename, kind, digest)
                if not valid_fingerprint(*item) or item in allowed:
                    raise ValueError
                allowed.add(item)
        return allowed
    except (OSError, ValueError, TypeError, KeyError):
        raise GateError("Invalid reviewed secret allowlist.") from None


def fingerprints(report):
    try:
        if (
            report["version"] != "1.5.0"
            or not isinstance(report["plugins_used"], list)
            or not report["plugins_used"]
        ):
            raise ValueError
        if not isinstance(report["results"], dict):
            raise ValueError
        found = set()
        for filename, entries in report["results"].items():
            if not isinstance(entries, list):
                raise ValueError
            for entry in entries:
                item = (filename, entry["type"], entry["hashed_secret"])
                if not valid_fingerprint(*item):
                    raise ValueError
                found.add(item)
        return found
    except (ValueError, TypeError, KeyError):
        raise GateError("Invalid secret scanner report.") from None


def scan(root, paths):
    command = [sys.executable, "-m", "detect_secrets", "scan", "--no-verify"]
    for name in DISABLED_FILTERS:
        command.extend(["--disable-filter", name])
    try:
        result = subprocess.run(
            [*command, "--", *paths], cwd=root, capture_output=True, text=True, timeout=120
        )
        if result.returncode or result.stderr:
            raise GateError("Secret scanner failed; output withheld.")
        return fingerprints(json.loads(result.stdout))
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        raise GateError(
            "Secret scanner failed or returned an invalid report; output withheld."
        ) from None


def check_findings(found, allowed):
    new, stale = found - allowed, allowed - found
    if new:
        paths = json.dumps(sorted({item[0] for item in new}))
        raise GateError(f"Unreviewed secret findings: {len(new)} in {paths}.")
    if stale:
        raise GateError(f"Stale allowlist fingerprints: {len(stale)}; review and remove them.")


def repository_files(root):
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )
    paths = sorted(set(result.stdout.rstrip("\0").split("\0")) - {ALLOWLIST})
    if not paths or any(
        not (root / path).is_file() or (root / path).is_symlink() for path in paths
    ):
        raise GateError("Secret scan requires existing regular repository files.")
    return paths


def main():
    try:
        paths = repository_files(ROOT)
        found = scan(ROOT, paths)
        check_findings(found, load_allowlist(ROOT / ALLOWLIST))
    except (GateError, OSError, subprocess.SubprocessError) as error:
        print(
            str(error) if isinstance(error, GateError) else "Secret gate failed; output withheld.",
            file=sys.stderr,
        )
        return 1
    print(f"Secret gate passed: {len(paths)} files, {len(found)} reviewed nonsecret fingerprints.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
