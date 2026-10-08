import json
from dataclasses import replace

import pytest

from deployment.journal_errors import JournalError
from deployment.journal_locator import Locator


def test_public_locator_contains_no_cloud_identifiers_or_credentials(config, locator):
    body = locator.to_json()
    assert "ocid1." not in body
    assert config.user_ocid not in body
    assert config.fingerprint not in body
    assert Locator.parse(body) == locator
    assert locator.bucket_name == replace(locator, control_region="us-ashburn-1").bucket_name


def test_locator_survives_target_and_key_rotation_but_rejects_changed_tenancy(config, locator):
    changed = replace(
        config, region="eu-frankfurt-1", compartment_ocid="ocid1.compartment.oc1..new"
    )
    locator.require_tenancy(changed.tenancy_ocid)
    with pytest.raises(JournalError, match="initial_target_changed"):
        locator.require_initial_target(changed)
    with pytest.raises(JournalError, match="identity_mismatch"):
        locator.require_tenancy("ocid1.tenancy.oc1..other")


@pytest.mark.parametrize(
    "change",
    [
        {"schema_version": True},
        {"repository_id": True},
        {"repository_id": 0},
        {"environment": "production"},
        {"installation_id": "not-a-uuid"},
        {"control_region": "https://untrusted.invalid"},
        {"tenancy_digest": "sensitive"},
        {"OPENAI_API_KEY": "sensitive"},
    ],
)
def test_malformed_locator_fails_without_values(locator, change):
    data = json.loads(locator.to_json())
    data.update(change)
    with pytest.raises(JournalError) as failure:
        Locator.parse(json.dumps(data))
    assert "sensitive" not in str(failure.value)


def test_duplicate_valid_field_and_oversize_are_rejected(locator):
    for body in (locator.to_json()[:-1] + ',"environment":"demo"}', " " * 65_537):
        with pytest.raises(JournalError):
            Locator.parse(body)
