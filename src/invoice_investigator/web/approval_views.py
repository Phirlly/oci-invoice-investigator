from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from invoice_investigator.case_storage.approvals import approve
from invoice_investigator.case_storage.models import Proposal
from invoice_investigator.cases.errors import CaseConflict

from .access import authorized_case
from .forms import ApprovalForm
from .presentation import evidence_links


@login_required
@never_cache
@require_http_methods(["GET", "POST"])
def confirmation(request, case_id, proposal_id):
    case = authorized_case(request.user, case_id, review=True)
    proposal = get_object_or_404(
        Proposal.objects.select_related("revision"), pk=proposal_id, revision__case=case
    )
    form = ApprovalForm(
        request.POST if request.method == "POST" else None, initial={"digest": proposal.digest}
    )
    status = 200
    if request.method == "POST":
        if form.is_valid():
            try:
                task = approve(request.user.pk, case.pk, proposal.pk, form.cleaned_data["digest"])
            except CaseConflict as error:
                form.add_error(None, str(error))
                status = 409
            else:
                return redirect(f"/cases/{case.pk}/#task-{task.pk}")
        else:
            status = 400
    return render(
        request,
        "review/confirmation.html",
        {
            "case": case,
            "proposal": proposal,
            "form": form,
            "links": evidence_links(proposal.revision, proposal.payload["evidence"]),
        },
        status=status,
    )
