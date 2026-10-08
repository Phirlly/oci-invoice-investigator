"""Publish an immutable snapshot while holding the same lock as approval."""

import hashlib

from django.db import transaction

from invoice_investigator.cases.errors import CaseConflict
from invoice_investigator.cases.proposals import payload_digest, receiving_proposals
from invoice_investigator.invoices.comparison import compare
from invoice_investigator.invoices.inputs import InputError, parse_invoice, parse_register

from .models import Case, CaseRevision, EvidenceDocument, Proposal
from .revision_inputs import validate_sources


@transaction.atomic
def publish_revision(case_id, sample):
    case = Case.objects.select_for_update().get(pk=case_id)
    validate_sources(sample)
    invoice = parse_invoice(sample.invoice, sample.manifest["files"]["invoice.pdf"])
    register = parse_register(sample.register)
    if invoice.case_id != case.pk or invoice.case_version != case.current_revision + 1:
        raise CaseConflict("Revision must advance this case by exactly one.")
    if (sample.manifest["case_id"], sample.manifest["case_version"]) != (
        invoice.case_id,
        invoice.case_version,
    ):
        raise InputError("Manifest and case revision differ.")
    expected_digest = payload_digest(
        {
            "invoice": sample.invoice,
            "register": sample.register,
            "manifest": sample.manifest,
        }
    )
    if sample.digest != expected_digest:
        raise InputError("Revision content digest is invalid.")
    result = compare(invoice, register)
    revision = CaseRevision.objects.create(
        case=case,
        number=invoice.case_version,
        content_digest=sample.digest,
        invoice=sample.invoice,
        register=sample.register,
        manifest=sample.manifest,
        result=result.to_dict(),
    )
    EvidenceDocument.objects.bulk_create(
        [
            EvidenceDocument(
                revision=revision,
                name=name,
                sha256=hashlib.sha256(content).hexdigest(),
                content=content,
            )
            for name, content in sample.documents.items()
        ]
    )
    Proposal.objects.bulk_create(
        [
            Proposal(revision=revision, payload=payload, digest=payload_digest(payload))
            for payload in receiving_proposals(invoice, register)
        ]
    )
    case.current_revision = revision.number
    case.save(update_fields=["current_revision"])
    return revision
