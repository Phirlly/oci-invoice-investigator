from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from invoice_investigator.case_storage.models import Case, CaseRevision, FollowUpTask

from .access import authorized_case
from .presentation import evidence_links, findings_for


@login_required
@never_cache
@require_GET
def case_list(request):
    cases = Case.objects.filter(membership__user=request.user, membership__active=True).order_by(
        "pk"
    )
    return render(request, "review/case_list.html", {"cases": cases})


@login_required
@never_cache
@require_GET
def case_detail(request, case_id):
    case = authorized_case(request.user, case_id)
    revision = get_object_or_404(CaseRevision, case=case, number=case.current_revision)
    return render(
        request,
        "review/case_detail.html",
        {
            "case": case,
            "revision": revision,
            "findings": findings_for(revision),
            "lines": [
                {**line, "price_links": evidence_links(revision, line["price_evidence"])}
                for line in revision.result["lines"]
            ],
            "has_amendment": revision.documents.filter(name="amendment.pdf").exists(),
            "conclusion": revision.result["conclusion"].replace("_", " ").capitalize(),
            "proposals": revision.proposals.all(),
            "tasks": FollowUpTask.objects.filter(approval__proposal__revision__case=case)
            .select_related("approval__proposal", "approval__reviewer")
            .order_by("created_at"),
        },
    )
