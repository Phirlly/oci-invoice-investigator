import copy
from concurrent.futures import ThreadPoolExecutor

from django.db import transaction
from web_concurrency import submit_connection, wait_for_row_lock

from invoice_investigator.case_storage.approvals import approve
from invoice_investigator.case_storage.models import Case, CaseRevision
from invoice_investigator.case_storage.revisions import publish_revision


def test_publisher_waits_for_approval_and_preserves_reviewed_snapshot(sample_case, second_revision):
    user, case, proposal = sample_case
    original_payload = copy.deepcopy(proposal.payload)
    original_result = copy.deepcopy(proposal.revision.result)
    with ThreadPoolExecutor(max_workers=1) as executor:
        with transaction.atomic():
            # Hold the service's approval lock until the competing publisher actually waits.
            task = approve(user.pk, case.pk, proposal.pk, proposal.digest)
            future, pid = submit_connection(
                executor, lambda: publish_revision(case.pk, second_revision).pk
            )
            wait_for_row_lock(pid)
        published = future.result(timeout=5)
    assert CaseRevision.objects.get(pk=published).number == 2
    assert Case.objects.get(pk=case.pk).current_revision == 2
    proposal.refresh_from_db()
    assert proposal.payload == original_payload
    assert proposal.revision.result == original_result
    assert approve(user.pk, case.pk, proposal.pk, proposal.digest).pk == task.pk
