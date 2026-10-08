"""Pinned OC1 identity client, constructed only inside the opt-in probe."""

from .errors import PreflightError


def build_client(config, credentials, region):
    import oci

    if oci.regions.REGION_REALMS.get(region) != "oc1":
        raise PreflightError("regions", "unsupported_region")
    signer = oci.signer.Signer(
        tenancy=config.tenancy_ocid,
        user=config.user_ocid,
        fingerprint=config.fingerprint,
        private_key_file_location=None,
        private_key_content=credentials.private_key,
        pass_phrase=credentials.passphrase,
    )
    client = oci.identity.IdentityClient(
        {
            "region": region,
            "log_requests": False,
            "tenancy": config.tenancy_ocid,
            "user": config.user_ocid,
            "fingerprint": config.fingerprint,
            "key_content": credentials.private_key,
        },
        signer=signer,
        service_endpoint=f"https://identity.{region}.oci.oraclecloud.com",
        timeout=(3, 8),
        retry_strategy=oci.retry.NoneRetryStrategy(),
    )
    client.base_client.session.trust_env = False
    return client
