from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import transaction

from .models import Case, Membership


def require_membership(user_id, case_id, *, review=False):
    if not get_user_model().objects.filter(pk=user_id, is_active=True).exists():
        raise PermissionDenied("Case access is unavailable.")
    query = Membership.objects.filter(case_id=case_id, user_id=user_id, active=True)
    if review:
        query = query.filter(can_review=True)
    if not query.exists():
        raise PermissionDenied("Case access is unavailable.")


@transaction.atomic
def revoke(case_id, user_id):
    Case.objects.select_for_update().get(pk=case_id)
    Membership.objects.filter(case_id=case_id, user_id=user_id).update(active=False)
