import shutil

import pytest

from invoice_investigator.case_storage.models import Case, CaseRevision, EvidenceDocument, Proposal
from invoice_investigator.case_storage.samples import seed_samples
from invoice_investigator.invoices.inputs import InputError


def test_seed_is_idempotent_and_scopes_shared_po(seeded_cases, sample_directory):
    seed_samples(sample_directory)
    assert Case.objects.count() == CaseRevision.objects.count() == 2
    assert Proposal.objects.count() == 1
    assert EvidenceDocument.objects.count() == 3
    revisions = list(CaseRevision.objects.order_by("case_id"))
    assert (
        revisions[0].register["po_lines"][0]["po_id"]
        == revisions[1].register["po_lines"][0]["po_id"]
    )
    assert revisions[0].result["conclusion"] == "no_discrepancy"
    assert revisions[1].result["lines"][0]["missing_receipt_quantity"] == 20


def test_corrupted_normalized_input_fails_before_seed(seeded_cases, sample_directory, tmp_path):
    copied = tmp_path / "samples"
    shutil.copytree(sample_directory, copied)
    invoice = copied / "case-002/normalized_invoice.json"
    invoice.write_text(invoice.read_text().replace('"1200.00"', '"1199.00"'))
    with pytest.raises(InputError, match="digest"):
        seed_samples(copied)
    assert CaseRevision.objects.count() == 2
