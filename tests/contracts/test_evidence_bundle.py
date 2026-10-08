import hashlib
import json
import shutil
from pathlib import Path

import pytest

from invoice_investigator.invoices.bundle import load_case
from invoice_investigator.invoices.inputs import InputError

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def bundle(tmp_path):
    source = ROOT / "examples/invoices/case-002"
    shutil.copytree(source, tmp_path / "case")
    invoice = ROOT / "tests/fixtures/invoices/case-002/normalized_invoice.json"
    return invoice, tmp_path / "case"


def test_both_bundles_resolve_to_exact_source_bytes():
    for name in ("case-001", "case-002"):
        folder = ROOT / "examples/invoices" / name
        invoice, register = load_case(
            ROOT / "tests/fixtures/invoices" / name / "normalized_invoice.json", folder
        )
        assert (
            invoice.document_sha256
            == hashlib.sha256((folder / "invoice.pdf").read_bytes()).hexdigest()
        )
        assert invoice.case_id == register.case_id == name
        assert not list(folder.glob("*expected*"))


def test_modified_source_is_rejected(bundle):
    invoice, folder = bundle
    (folder / "invoice.pdf").write_bytes(b"changed")
    with pytest.raises(InputError, match="digest"):
        load_case(invoice, folder)


def test_manifest_cannot_select_arbitrary_paths(bundle):
    invoice, folder = bundle
    manifest_path = folder / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files"]["../../private"] = "a" * 64
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(InputError):
        load_case(invoice, folder)


@pytest.mark.parametrize("payload", [b'{"case_id":1,"case_id":2}', b"[]", b"\xff", b"{"])
def test_invalid_json_is_rejected(payload, bundle, tmp_path):
    _, folder = bundle
    invoice = tmp_path / "input.json"
    invoice.write_bytes(payload)
    with pytest.raises(InputError):
        load_case(invoice, folder)


def test_missing_file_has_safe_input_error(bundle):
    invoice, folder = bundle
    (folder / "invoice.pdf").unlink()
    with pytest.raises(InputError):
        load_case(invoice, folder)


def test_non_utf8_json_rejected(bundle, tmp_path):
    invoice, folder = bundle
    alternate = tmp_path / "utf16.json"
    alternate.write_bytes(invoice.read_text().encode("utf-16"))
    with pytest.raises(InputError):
        load_case(alternate, folder)


def test_oversized_normalized_input_rejected(bundle, tmp_path):
    _, folder = bundle
    invoice = tmp_path / "oversized.json"
    invoice.write_bytes(b" " * 1_048_577)
    with pytest.raises(InputError, match="size"):
        load_case(invoice, folder)


def test_manifest_case_must_match_inputs(bundle):
    invoice, folder = bundle
    path = folder / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["case_id"] = "another-case"
    path.write_text(json.dumps(manifest))
    with pytest.raises(InputError, match="snapshots"):
        load_case(invoice, folder)
