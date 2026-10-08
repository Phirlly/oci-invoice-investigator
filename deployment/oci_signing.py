"""Shared in-memory signing and explicit OC1 client options."""

from .errors import PreflightError


def client_options(config, credentials, region):
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
    return {
        "config": {
            "region": region,
            "log_requests": False,
            "tenancy": config.tenancy_ocid,
            "user": config.user_ocid,
            "fingerprint": config.fingerprint,
            "key_content": credentials.private_key,
        },
        "signer": signer,
        "timeout": (3, 8),
        "retry_strategy": oci.retry.NoneRetryStrategy(),
    }
