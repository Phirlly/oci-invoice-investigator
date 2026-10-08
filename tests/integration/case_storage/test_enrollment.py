import uuid

import pytest
from django.contrib.auth.hashers import check_password

from invoice_investigator.case_storage.enrollment import enroll, prepare_password
from invoice_investigator.case_storage.models import Installation, Membership
from invoice_investigator.cases.errors import CaseConflict


def test_encoded_password_consumed_once_without_double_hash(seeded_cases):
    encoded = prepare_password("reviewer", "Local-test-example-48!is-unique")
    nonce = uuid.uuid4()
    owner = enroll(seeded_cases, nonce, "reviewer", encoded)
    assert owner.password == encoded
    assert check_password("Local-test-example-48!is-unique", owner.password)
    assert enroll(seeded_cases, nonce, "reviewer", encoded).pk == owner.pk
    assert Membership.objects.filter(user=owner, can_review=True).count() == 2
    assert Installation.objects.get(pk=1).owner_id == owner.pk


def test_changed_enrollment_cannot_replace_account(seeded_cases):
    nonce = uuid.uuid4()
    encoded = prepare_password("reviewer", "Local-test-example-48!is-unique")
    owner = enroll(seeded_cases, nonce, "reviewer", encoded)
    with pytest.raises(CaseConflict):
        enroll(seeded_cases, uuid.uuid4(), "reviewer", encoded)
    owner.refresh_from_db()
    assert owner.password == encoded


@pytest.mark.parametrize("encoded", ["plain-password", "!disabled", "pbkdf2_sha256$1$x$bad"])
def test_invalid_encoded_password_rejected(seeded_cases, encoded):
    with pytest.raises(ValueError, match="password"):
        enroll(seeded_cases, uuid.uuid4(), "reviewer", encoded)
    assert Installation.objects.get(pk=1).owner_id is None


def test_enrollment_for_another_installation_is_rejected(seeded_cases):
    encoded = prepare_password("reviewer", "Local-test-example-48!is-unique")
    with pytest.raises(CaseConflict, match="installation"):
        enroll(uuid.uuid4(), uuid.uuid4(), "reviewer", encoded)
    assert Installation.objects.get(pk=1).owner_id is None
