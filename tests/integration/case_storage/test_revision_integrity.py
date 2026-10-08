from dataclasses import replace

import pytest

from invoice_investigator.case_storage.models import CaseRevision, EvidenceDocument, Proposal
from invoice_investigator.case_storage.revisions import publish_revision
from invoice_investigator.cases.proposals import payload_digest
from invoice_investigator.invoices.inputs import InputError


@pytest.mark.parametrize("missing", ["invoice.pdf", "amendment.pdf"])
def test_missing_manifest_document_is_rejected_atomically(sample_case, second_revision, missing):
    _, case, _ = sample_case
    documents = dict(second_revision.documents)
    del documents[missing]
    with pytest.raises(InputError, match="document"):
        publish_revision(case.pk, replace(second_revision, documents=documents))
    case.refresh_from_db()
    assert case.current_revision == 1
    assert (
        CaseRevision.objects.count(),
        Proposal.objects.count(),
        EvidenceDocument.objects.count(),
    ) == (2, 1, 3)


def test_changed_register_cannot_reuse_original_source_hash(sample_case, second_revision):
    _, case, _ = sample_case
    second_revision.register["receipts"][0]["quantity"] = 100
    altered = replace(
        second_revision,
        digest=payload_digest(
            {
                "invoice": second_revision.invoice,
                "register": second_revision.register,
                "manifest": second_revision.manifest,
            }
        ),
    )
    with pytest.raises(InputError, match="register"):
        publish_revision(case.pk, altered)
    case.refresh_from_db()
    assert case.current_revision == 1
    assert CaseRevision.objects.count() == 2
