"""Load explicitly selected local fixtures; verify source integrity before comparison."""

import hashlib
import json
from pathlib import Path

from .input_fields import InputError, digest, versioned
from .inputs import parse_invoice, parse_register

JSON_LIMIT = 1_048_576
PDF_LIMIT = 10_485_760


def _read(path, limit):
    try:
        with path.open("rb") as stream:
            payload = stream.read(limit + 1)
    except OSError as error:
        raise InputError("An input file could not be read.") from error
    if len(payload) > limit:
        raise InputError("Input exceeds the supported file size.")
    return payload


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InputError("Duplicate JSON object keys are unsupported.")
        result[key] = value
    return result


def _json(payload):
    try:
        return json.loads(payload.decode("utf-8"), object_pairs_hook=_unique_object)
    except (ValueError, UnicodeError, RecursionError) as error:
        raise InputError("Input must be valid UTF-8 JSON with unique object keys.") from error


def load_case(invoice_path: Path, evidence_directory: Path):
    manifest = versioned(_json(_read(evidence_directory / "manifest.json", JSON_LIMIT)), "files")
    files = manifest["files"]
    if not isinstance(files, dict) or set(files) not in (
        {"invoice.pdf", "purchasing.json"},
        {"invoice.pdf", "purchasing.json", "amendment.pdf"},
    ):
        raise InputError("Manifest must name only the supported source files.")
    payloads = {}
    for name, expected_hash in files.items():
        payload = _read(
            evidence_directory / name, JSON_LIMIT if name.endswith(".json") else PDF_LIMIT
        )
        if hashlib.sha256(payload).hexdigest() != digest(expected_hash):
            raise InputError("Source digest does not match the case manifest.")
        payloads[name] = payload
    invoice = parse_invoice(_json(_read(invoice_path, JSON_LIMIT)), files["invoice.pdf"])
    register = parse_register(_json(payloads["purchasing.json"]))
    if any(
        (record.case_id, record.case_version) != (manifest["case_id"], manifest["case_version"])
        for record in (invoice, register)
    ):
        raise InputError("Manifest and input case snapshots differ.")
    return invoice, register
