import uuid

from web_concurrency import simultaneously

from invoice_investigator.case_storage.enrollment import enroll, prepare_password
from invoice_investigator.case_storage.models import Installation, Membership
from invoice_investigator.cases.errors import CaseConflict


def test_identical_concurrent_enrollment_creates_one_owner(seeded_cases, django_user_model):
    encoded = prepare_password("reviewer", "Local-test-example-48!is-unique")
    nonce = uuid.uuid4()

    def call():
        return enroll(seeded_cases, nonce, "reviewer", encoded).pk

    owners = simultaneously(call, call)
    assert owners[0] == owners[1]
    assert django_user_model.objects.count() == 1
    assert Membership.objects.count() == 2


def test_competing_enrollment_cannot_replace_winner(seeded_cases, django_user_model):
    encoded = prepare_password("reviewer", "Local-test-example-48!is-unique")

    def enroll_once():
        try:
            return enroll(seeded_cases, uuid.uuid4(), "reviewer", encoded).pk
        except CaseConflict:
            return None

    results = simultaneously(enroll_once, enroll_once)
    assert results.count(None) == 1
    assert Installation.objects.get(pk=1).owner_id == next(item for item in results if item)
    assert django_user_model.objects.count() == 1
