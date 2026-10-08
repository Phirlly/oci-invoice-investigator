from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404

from invoice_investigator.case_storage.membership import require_membership
from invoice_investigator.case_storage.models import Case, CaseRevision


def authorized_case(user, case_id, *, review=False):
    try:
        require_membership(user.pk, case_id, review=review)
    except PermissionDenied as error:
        raise Http404("Case is unavailable.") from error
    return get_object_or_404(Case, pk=case_id)


def authorized_revision(user, case_id, number):
    case = authorized_case(user, case_id)
    return get_object_or_404(CaseRevision, case=case, number=number)
