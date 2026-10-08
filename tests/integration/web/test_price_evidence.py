from dataclasses import replace

from invoice_investigator.case_storage.revisions import publish_revision
from invoice_investigator.cases.proposals import payload_digest


def test_supported_price_has_precise_amendment_citation(sample_case, client):
    user, _, _ = sample_case
    client.force_login(user)
    response = client.get("/cases/case-002/")
    assert b"12.00 USD" in response.content
    assert b"pointer=%2Famendments%2F0" in response.content


def test_amendment_link_follows_revision_documents(sample_case, second_revision, client):
    user, case, _ = sample_case
    client.force_login(user)
    assert b"Download supporting amendment PDF" in client.get("/cases/case-002/").content
    del second_revision.documents["amendment.pdf"]
    del second_revision.manifest["files"]["amendment.pdf"]
    changed = replace(
        second_revision,
        digest=payload_digest(
            {
                "invoice": second_revision.invoice,
                "register": second_revision.register,
                "manifest": second_revision.manifest,
            }
        ),
    )
    publish_revision(case.pk, changed)
    assert b"Download supporting amendment PDF" not in client.get("/cases/case-002/").content
