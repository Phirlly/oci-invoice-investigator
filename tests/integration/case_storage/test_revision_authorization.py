import pytest
from django.core.exceptions import PermissionDenied

from invoice_investigator.case_storage.approvals import approve
from invoice_investigator.case_storage.membership import revoke
from invoice_investigator.case_storage.models import FollowUpTask, Membership
from invoice_investigator.cases.errors import CaseConflict


def test_new_stale_approval_is_rejected(sample_case):
    user, case, proposal = sample_case
    case.current_revision = 2
    case.save(update_fields=["current_revision"])
    with pytest.raises(CaseConflict):
        approve(user.pk, case.pk, proposal.pk, proposal.digest)
    assert not FollowUpTask.objects.exists()


def test_committed_retry_survives_revision_but_not_revocation(sample_case):
    user, case, proposal = sample_case
    task = approve(user.pk, case.pk, proposal.pk, proposal.digest)
    case.current_revision = 2
    case.save(update_fields=["current_revision"])
    assert approve(user.pk, case.pk, proposal.pk, proposal.digest).pk == task.pk
    revoke(case.pk, user.pk)
    with pytest.raises(PermissionDenied):
        approve(user.pk, case.pk, proposal.pk, proposal.digest)


def test_readonly_membership_cannot_approve(sample_case):
    user, case, proposal = sample_case
    Membership.objects.filter(case=case, user=user).update(can_review=False)
    with pytest.raises(PermissionDenied):
        approve(user.pk, case.pk, proposal.pk, proposal.digest)
