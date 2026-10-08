"""Explicit standard regional OC1 Object Storage endpoint; no profile fallback."""

from .oci_signing import client_options


def build_storage_client(config, credentials, region):
    import oci

    client = oci.object_storage.ObjectStorageClient(
        **client_options(config, credentials, region),
        service_endpoint=f"https://objectstorage.{region}.oraclecloud.com",
    )
    client.base_client.session.trust_env = False
    return client
