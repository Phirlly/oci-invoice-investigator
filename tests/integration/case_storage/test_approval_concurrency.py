from concurrent.futures import ThreadPoolExecutor

import pytest
from django.core.exceptions import PermissionDenied
from django.db import transaction
from web_concurrency import simultaneously, submit_connection, wait_for_row_lock

from invoice_investigator.case_storage.approvals import approve
from invoice_investigator.case_storage.membership import revoke
from invoice_investigator.case_storage.models import AuditEntry, Case, FollowUpTask
from invoice_investigator.case_storage.revisions import publish_revision
from invoice_investigator.cases.errors import CaseConflict


def test_concurrent_identical_approvals_have_one_task(sample_case):
    user, case, proposal = sample_case

    def call():
        return approve(user.pk, case.pk, proposal.pk, proposal.digest).pk

    results = simultaneously(call, call)
    assert results[0] == results[1]
    assert FollowUpTask.objects.count() == AuditEntry.objects.count() == 1


@pytest.mark.parametrize("change", ["revision", "membership"])
def test_waiting_approval_rechecks_state_after_case_lock(sample_case, second_revision, change):
    user, case, proposal = sample_case

    def call():
        return approve(user.pk, case.pk, proposal.pk, proposal.digest)

    with ThreadPoolExecutor(max_workers=1) as executor:
        with transaction.atomic():
            Case.objects.select_for_update().get(pk=case.pk)
            future, pid = submit_connection(executor, call)
            wait_for_row_lock(pid)
            if change == "revision":
                publish_revision(case.pk, second_revision)
            else:
                revoke(case.pk, user.pk)
        with pytest.raises(CaseConflict if change == "revision" else PermissionDenied):
            future.result(timeout=5)
    assert FollowUpTask.objects.count() == 0
