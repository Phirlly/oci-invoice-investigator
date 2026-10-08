from types import SimpleNamespace as Record

import pytest

from deployment.journal_bucket import ensure_bucket, ownership
from deployment.journal_errors import JournalError


class ServiceFailure(Exception):
    def __init__(self, status):
        self.status = status


@pytest.fixture
def bucket(anchor, config):
    return Record(
        id="ocid1.bucket.oc1.uk-london-1.examplebucket",
        namespace="examplenamespace",
        name=anchor.locator.bucket_name,
        compartment_id=config.compartment_ocid,
        metadata=ownership(anchor),
        public_access_type="NoPublicAccess",
        storage_tier="Standard",
        bucket_scope="NAMESPACE",
        versioning="Disabled",
        auto_tiering="Disabled",
        is_read_only=False,
        replication_enabled=False,
        object_lifecycle_policy_etag=None,
        kms_key_id=None,
        defined_tags={"automatic": {"tag": "allowed"}},
    )


class Client:
    def __init__(self, reads, create_error=None):
        self.reads = iter(reads)
        self.create_error = create_error
        self.created = []

    def get_bucket(self, namespace, name):
        value = next(self.reads)
        if isinstance(value, Exception):
            raise value
        return Record(data=value)

    def create_bucket(self, namespace, details):
        self.created.append((namespace, details))
        if self.create_error:
            raise self.create_error
        return Record(data=None)


def test_existing_owned_bucket_requires_no_mutation(bucket, anchor, config):
    client = Client([bucket])
    assert ensure_bucket(client, anchor, bucket.namespace, config, False) is bucket
    assert client.created == []


@pytest.mark.parametrize("error", [None, TimeoutError(), ServiceFailure(409)])
def test_creation_always_reconciles_ownership(bucket, anchor, config, error):
    client = Client([ServiceFailure(404), bucket], error)
    assert ensure_bucket(client, anchor, bucket.namespace, config, True) is bucket
    assert len(client.created) == 1
    namespace, details = client.created[0]
    assert namespace == bucket.namespace
    assert details.metadata == ownership(anchor)
    assert details.public_access_type == "NoPublicAccess"
    assert details.compartment_id == config.compartment_ocid


@pytest.mark.parametrize(
    "field,value",
    [
        ("metadata", {}),
        ("public_access_type", "ObjectRead"),
        ("versioning", "Enabled"),
        ("is_read_only", True),
        ("replication_enabled", True),
        ("object_lifecycle_policy_etag", "policy"),
        ("auto_tiering", "InfrequentAccess"),
        ("kms_key_id", "foreign-key"),
        ("bucket_scope", "UNKNOWN_ENUM_VALUE"),
        ("namespace", "other"),
        ("name", "other"),
    ],
)
def test_conflicting_bucket_is_never_repaired(bucket, anchor, config, field, value):
    setattr(bucket, field, value)
    client = Client([bucket])
    with pytest.raises(JournalError, match="bucket_conflict"):
        ensure_bucket(client, anchor, "examplenamespace", config, True)
    assert client.created == []


def test_read_mode_and_denied_lookup_never_create(anchor, config):
    for status, initialize in [(404, False), (403, True), (500, True)]:
        client = Client([ServiceFailure(status)])
        with pytest.raises(JournalError):
            ensure_bucket(client, anchor, "examplenamespace", config, initialize)
        assert client.created == []


def test_unknown_create_outcome_is_not_absence(anchor, config):
    client = Client([ServiceFailure(404), ServiceFailure(404)], TimeoutError())
    with pytest.raises(JournalError, match="outcome_unknown"):
        ensure_bucket(client, anchor, "examplenamespace", config, True)
    assert len(client.created) == 1
