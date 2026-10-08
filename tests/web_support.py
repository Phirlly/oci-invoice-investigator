"""Explicit PostgreSQL/UI plugin. Import and collection have no service effects."""

import os
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def django_db_modify_db_settings():
    from django.conf import settings

    port = os.environ.get("II_CHECK_PORT", "")
    password = os.environ.get("II_CHECK_PASSWORD", "")
    if not port.isdecimal() or not password or os.environ.get("II_CHECK_ISOLATED") != "1":
        raise pytest.UsageError("Use tools/run_web_checks.py for isolated PostgreSQL tests.")
    database = settings.DATABASES["default"]
    assert database["HOST"] == "127.0.0.1" and database["NAME"] == "invoice_checks"
    database.update(PORT=int(port), PASSWORD=password)


@pytest.fixture
def sample_directory():
    return Path(__file__).resolve().parents[1] / "examples/invoices"


@pytest.fixture
def seeded_cases(transactional_db, sample_directory):
    from invoice_investigator.case_storage.models import Installation
    from invoice_investigator.case_storage.samples import seed_samples

    installation, _ = Installation.objects.get_or_create(pk=1)
    seed_samples(sample_directory)
    return installation.identity


@pytest.fixture
def sample_case(seeded_cases, django_user_model):
    from invoice_investigator.case_storage.models import Case, Membership, Proposal

    user = django_user_model.objects.create_user(
        username="reviewer", password="local-test-password"
    )
    case = Case.objects.get(pk="case-002")
    Membership.objects.create(case=case, user=user, can_review=True)
    return user, case, Proposal.objects.get(revision__case=case)
