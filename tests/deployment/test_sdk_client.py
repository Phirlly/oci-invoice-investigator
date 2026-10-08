import json
import os

import pytest

from deployment.configuration import parse_configuration
from deployment.credentials import load_credentials
from deployment.errors import PreflightError
from deployment.oci_client import build_client


@pytest.fixture
def sdk(monkeypatch):
    monkeypatch.setenv("OCI_DEVELOPER_TOOL_CONFIGURATION_FILE_PATH", os.devnull)
    import oci

    return oci


def test_real_sdk_signs_get_without_profile_key_files_or_retries(
    credential_environment, monkeypatch, sdk
):
    config = parse_configuration(credential_environment["DEPLOYMENT_CONFIG"])
    credentials = load_credentials(credential_environment, config.fingerprint)

    def forbidden(*args, **kwargs):
        raise AssertionError("Profile/key file was accessed")

    monkeypatch.setattr(sdk.config, "from_file", forbidden)
    monkeypatch.setattr(sdk.signer, "load_private_key_from_file", forbidden)
    client = build_client(config, credentials, config.region)
    calls = []

    def send(request, **kwargs):
        calls.append((request, kwargs))
        response = sdk._vendor.requests.Response()
        response.status_code = 500
        response.headers["content-type"] = "application/json"
        response._content = json.dumps({"code": "InternalError", "message": "synthetic"}).encode()
        return response

    monkeypatch.setattr(client.base_client.session, "send", send)
    with pytest.raises(sdk.exceptions.ServiceError):
        client.get_user(config.user_ocid)
    assert len(calls) == 1
    request, kwargs = calls[0]
    assert request.method == "GET"
    assert (
        request.url
        == "https://identity.us-ashburn-1.oci.oraclecloud.com/20160918/users/" + config.user_ocid
    )
    assert "authorization" in {name.lower() for name in request.headers}
    assert kwargs["timeout"] == (3, 8)
    assert client.base_client.logger.disabled
    assert client.base_client.session.trust_env is False


@pytest.mark.parametrize(
    "region", ["unknown-region-1", "us-langley-1", "https://untrusted.invalid"]
)
def test_only_pinned_oc1_endpoints_allowed(credential_environment, sdk, region):
    config = parse_configuration(credential_environment["DEPLOYMENT_CONFIG"])
    credentials = load_credentials(credential_environment, config.fingerprint)
    with pytest.raises(PreflightError) as failure:
        build_client(config, credentials, region)
    assert failure.value.code == "unsupported_region"
