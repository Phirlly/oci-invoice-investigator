"""Create or recover the owned control bucket without repairing foreign state."""

from . import journal_schema as schema
from .journal_errors import JournalError, require


def ownership(anchor):
    return {
        "invoice-schema": "1",
        "invoice-repository": str(anchor.locator.repository_id),
        "invoice-environment": "demo",
        "invoice-anchor": str(anchor.id),
        "invoice-installation": anchor.locator.installation_id,
        "invoice-target": anchor.locator.target_digest,
    }


def validate_bucket(bucket, anchor, namespace):
    expected = {
        "name": anchor.locator.bucket_name,
        "namespace": namespace,
        "metadata": ownership(anchor),
        "public_access_type": "NoPublicAccess",
        "storage_tier": "Standard",
        "bucket_scope": "NAMESPACE",
        "versioning": "Disabled",
        "auto_tiering": "Disabled",
        "is_read_only": False,
        "replication_enabled": False,
        "object_lifecycle_policy_etag": None,
        "kms_key_id": None,
    }
    missing = object()
    for field, value in expected.items():
        actual = getattr(bucket, field, missing)
        require(type(actual) is type(value) and actual == value, "bucket_conflict")
    schema.pattern(getattr(bucket, "id", None), schema.BUCKET)
    schema.pattern(getattr(bucket, "compartment_id", None), schema.COMPARTMENT)
    return bucket


def ensure_bucket(client, anchor, namespace, config, initialize):
    schema.pattern(namespace, schema.NAMESPACE)
    try:
        bucket = client.get_bucket(namespace, anchor.locator.bucket_name).data
    except Exception as error:
        if not initialize or getattr(error, "status", None) != 404:
            raise JournalError("storage_unavailable") from None
    else:
        return validate_bucket(bucket, anchor, namespace)
    anchor.locator.require_initial_target(config)
    from oci.object_storage.models import CreateBucketDetails

    details = CreateBucketDetails(
        name=anchor.locator.bucket_name,
        compartment_id=config.compartment_ocid,
        metadata=ownership(anchor),
        public_access_type="NoPublicAccess",
        storage_tier="Standard",
        bucket_scope="NAMESPACE",
        versioning="Disabled",
        auto_tiering="Disabled",
    )
    try:
        client.create_bucket(namespace, details)
    except Exception:
        # No create retry: 404/409 also conceal authorization. Read ownership instead.
        pass
    try:
        bucket = client.get_bucket(namespace, anchor.locator.bucket_name).data
    except Exception:
        raise JournalError("outcome_unknown") from None
    return validate_bucket(bucket, anchor, namespace)
