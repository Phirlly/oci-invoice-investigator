"""Pinned OC1 identity client, constructed only inside the opt-in probe."""

from .oci_signing import client_options


def build_client(config, credentials, region):
    import oci

    client = oci.identity.IdentityClient(
        **client_options(config, credentials, region),
        service_endpoint=f"https://identity.{region}.oci.oraclecloud.com",
    )
    client.base_client.session.trust_env = False
    return client
