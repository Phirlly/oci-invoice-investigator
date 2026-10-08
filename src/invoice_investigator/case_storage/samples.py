"""Import only versioned, explicitly hand-normalized synthetic sample bundles."""

import hashlib
from dataclasses import dataclass
from pathlib import Path

from django.db import transaction

from invoice_investigator.cases.errors import CaseConflict
from invoice_investigator.cases.proposals import payload_digest
from invoice_investigator.invoices.bundle import JSON_LIMIT, PDF_LIMIT, _json, _read, load_case
from invoice_investigator.invoices.inputs import InputError

from .models import Case, Installation, Membership
from .revisions import publish_revision


@dataclass(frozen=True)
class Sample:
    invoice: dict
    register: dict
    manifest: dict
    documents: dict
    register_source: bytes
    digest: str


def read_sample(directory: Path):
    invoice_bytes = _read(directory / "normalized_invoice.json", JSON_LIMIT)
    provenance = _json(_read(directory / "sample-input.json", JSON_LIMIT))
    if provenance != {
        "kind": "hand_normalized_synthetic",
        "normalized_sha256": hashlib.sha256(invoice_bytes).hexdigest(),
    }:
        raise InputError("Sample input provenance or digest is invalid.")
    load_case(directory / "normalized_invoice.json", directory)
    manifest = _json(_read(directory / "manifest.json", JSON_LIMIT))
    payloads = {}
    for name, expected in manifest["files"].items():
        content = _read(directory / name, JSON_LIMIT if name.endswith(".json") else PDF_LIMIT)
        if hashlib.sha256(content).hexdigest() != expected:
            raise InputError("Source digest changed while reading sample.")
        payloads[name] = content
    invoice = _json(invoice_bytes)
    register_source = payloads.pop("purchasing.json")
    register = _json(register_source)
    digest = payload_digest({"invoice": invoice, "register": register, "manifest": manifest})
    return Sample(invoice, register, manifest, payloads, register_source, digest)


@transaction.atomic
def seed_samples(directory: Path):
    samples = [read_sample(directory / case) for case in ("case-001", "case-002")]
    installation = Installation.objects.select_for_update().get(pk=1)
    for sample in samples:
        case_id = sample.invoice["case_id"]
        case, _ = Case.objects.get_or_create(
            pk=case_id,
            defaults={
                "title": "Matched control"
                if case_id == "case-001"
                else "Receiving evidence review",
            },
        )
        existing = case.revisions.filter(number=sample.invoice["case_version"]).first()
        if existing:
            if existing.content_digest != sample.digest:
                raise CaseConflict("Sample version already exists with different content.")
        else:
            publish_revision(case.pk, sample)
        if installation.owner_id:
            Membership.objects.get_or_create(
                case=case, user_id=installation.owner_id, defaults={"can_review": True}
            )
