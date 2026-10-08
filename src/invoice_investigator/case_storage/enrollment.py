"""One-time enrollment of a validated encoded password; no public enrollment route."""

import base64
import hmac
import uuid

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import PBKDF2PasswordHasher, make_password
from django.contrib.auth.password_validation import validate_password
from django.db import transaction

from invoice_investigator.cases.errors import CaseConflict
from invoice_investigator.cases.proposals import payload_digest

from .models import Case, Installation, Membership


def prepare_password(username, password):
    user = get_user_model()(username=username)
    user.full_clean(exclude=["password"])
    validate_password(password, user)
    return make_password(password)


def _validate_encoding(encoded):
    try:
        hasher = PBKDF2PasswordHasher()
        decoded = hasher.decode(encoded)
        raw = base64.b64decode(decoded["hash"], validate=True)
        if not (hasher.iterations <= decoded["iterations"] <= 5_000_000):
            raise ValueError
        if len(raw) != 32 or not (12 <= len(decoded["salt"]) <= 128):
            raise ValueError
    except (ValueError, TypeError, KeyError, AssertionError) as error:
        raise ValueError("Unsupported encoded password.") from error


@transaction.atomic
def enroll(installation_id, enrollment_id, username, encoded_password):
    _validate_encoding(encoded_password)
    enrollment_id = uuid.UUID(str(enrollment_id))
    installation = Installation.objects.select_for_update().get(pk=1)
    if installation.identity != uuid.UUID(str(installation_id)):
        raise CaseConflict("Enrollment belongs to another installation.")
    digest = payload_digest(
        {
            "installation": str(installation.identity),
            "enrollment": str(enrollment_id),
            "username": username,
            "encoded_password": encoded_password,
        }
    )
    if installation.owner_id:
        if hmac.compare_digest(installation.enrollment_digest, digest):
            return installation.owner
        raise CaseConflict("Enrollment has already been consumed.")
    user = get_user_model()(username=username, password=encoded_password, is_active=True)
    user.full_clean()
    user.save()
    Membership.objects.bulk_create(
        [Membership(case=case, user=user, can_review=True) for case in Case.objects.all()]
    )
    installation.owner = user
    installation.enrollment_id = enrollment_id
    installation.enrollment_digest = digest
    installation.save(update_fields=["owner", "enrollment_id", "enrollment_digest"])
    return user
