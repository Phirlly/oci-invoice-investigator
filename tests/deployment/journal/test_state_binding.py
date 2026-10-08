import json
from dataclasses import replace

import pytest

from deployment.journal_errors import JournalError
from deployment.journal_state import Journal


def test_private_state_round_trip_and_bound_target(journal, anchor):
    loaded = Journal.parse(journal.to_bytes())
    assert loaded == journal
    loaded.require_binding(anchor, journal.namespace, journal.bucket_ocid, journal.compartment_ocid)
    assert "ocid1." not in repr(loaded)


@pytest.mark.parametrize(
    "field,value",
    [
        ("compartment_ocid", "ocid1.compartment.oc1..substituted"),
        ("workload_region", "eu-frankfurt-1"),
        ("anchor_id", 999),
        ("bucket_ocid", "ocid1.bucket.oc1.uk-london-1.other"),
        ("namespace", "othernamespace"),
    ],
)
def test_structurally_valid_substitution_is_rejected(journal, anchor, field, value):
    data = json.loads(journal.to_bytes())
    data[field] = value
    with pytest.raises(JournalError):
        loaded = Journal.parse(json.dumps(data).encode())
        loaded.require_binding(
            anchor, journal.namespace, journal.bucket_ocid, journal.compartment_ocid
        )


def test_private_state_cannot_accept_extra_secret_field(journal):
    data = json.loads(journal.to_bytes())
    data["private_key"] = "sensitive-value"
    with pytest.raises(JournalError) as failure:
        Journal.parse(json.dumps(data).encode())
    assert "sensitive-value" not in str(failure.value)


def test_initialization_must_match_recorded_target(journal, anchor, config):
    with pytest.raises(JournalError, match="initial_target_changed"):
        Journal.initial(
            anchor,
            journal.namespace,
            journal.bucket_ocid,
            replace(config, region="eu-frankfurt-1"),
            journal.write_id,
        )
