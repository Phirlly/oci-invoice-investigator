import hmac

from django.db import transaction

from invoice_investigator.cases.errors import CaseConflict
from invoice_investigator.cases.proposals import payload_digest

from .membership import require_membership
from .models import Approval, AuditEntry, Case, FollowUpTask, Proposal


@transaction.atomic
def approve(user_id, case_id, proposal_id, digest):
    case = Case.objects.select_for_update().get(pk=case_id)
    require_membership(user_id, case_id, review=True)
    try:
        proposal = Proposal.objects.select_related("revision").get(
            pk=proposal_id, revision__case_id=case_id
        )
    except Proposal.DoesNotExist as error:
        raise CaseConflict("Proposal is unavailable for this case.") from error
    if not (
        hmac.compare_digest(proposal.digest, digest)
        and hmac.compare_digest(proposal.digest, payload_digest(proposal.payload))
    ):
        raise CaseConflict("Proposal changed. Review the current case before approving.")
    existing = FollowUpTask.objects.filter(approval__proposal=proposal).first()
    if existing:
        return existing
    if proposal.revision.number != case.current_revision:
        raise CaseConflict("This proposal is stale. Review the current case.")
    approval = Approval.objects.create(proposal=proposal, reviewer_id=user_id, digest=digest)
    task = FollowUpTask.objects.create(approval=approval)
    AuditEntry.objects.create(approval=approval)
    return task
