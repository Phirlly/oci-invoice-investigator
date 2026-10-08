import pytest
from django.core.exceptions import PermissionDenied

from invoice_investigator.case_storage.approvals import approve
from invoice_investigator.case_storage.models import Approval, AuditEntry, FollowUpTask
from invoice_investigator.cases.errors import CaseConflict


def test_exact_retry_creates_one_task_and_audit(sample_case):
    user, case, proposal = sample_case
    first = approve(user.pk, case.pk, proposal.pk, proposal.digest)
    second = approve(user.pk, case.pk, proposal.pk, proposal.digest)
    assert first.pk == second.pk
    assert (Approval.objects.count(), FollowUpTask.objects.count(), AuditEntry.objects.count()) == (
        1,
        1,
        1,
    )
    assert first.approval.reviewer_id == user.pk


def test_changed_payload_is_rejected_without_writes(sample_case):
    user, case, proposal = sample_case
    with pytest.raises(CaseConflict):
        approve(user.pk, case.pk, proposal.pk, "0" * 64)
    assert FollowUpTask.objects.count() == 0


def test_audit_failure_rolls_back_task_and_approval(sample_case, monkeypatch):
    user, case, proposal = sample_case

    def fail(**kwargs):
        raise RuntimeError("injected audit failure")

    monkeypatch.setattr(AuditEntry.objects, "create", fail)
    with pytest.raises(RuntimeError, match="injected"):
        approve(user.pk, case.pk, proposal.pk, proposal.digest)
    assert Approval.objects.count() == FollowUpTask.objects.count() == 0


def test_nonmember_cannot_approve_or_retry(sample_case, django_user_model):
    user, case, proposal = sample_case
    approve(user.pk, case.pk, proposal.pk, proposal.digest)
    outsider = django_user_model.objects.create_user(username="outsider")
    with pytest.raises(PermissionDenied):
        approve(outsider.pk, case.pk, proposal.pk, proposal.digest)
