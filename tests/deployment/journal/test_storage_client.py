import json
import os

import pytest

from deployment.configuration import parse_configuration
from deployment.credentials import load_signing_credentials
from deployment.errors import PreflightError
from deployment.oci_storage_client import build_storage_client


def test_pinned_sdk_signs_conditional_write_without_retry(credential_environment, monkeypatch):
    monkeypatch.setenv("OCI_DEVELOPER_TOOL_CONFIGURATION_FILE_PATH", os.devnull)
    import oci

    config = parse_configuration(credential_environment["DEPLOYMENT_CONFIG"])
    credentials = load_signing_credentials(credential_environment, config.fingerprint)
    client = build_storage_client(config, credentials, "uk-london-1")
    calls = []

    def send(request, **kwargs):
        calls.append((request, kwargs))
        response = oci._vendor.requests.Response()
        response.status_code = 500
        response.headers["content-type"] = "application/json"
        response._content = json.dumps({"code": "InternalError", "message": "synthetic"}).encode()
        return response

    monkeypatch.setattr(client.base_client.session, "send", send)
    with pytest.raises(oci.exceptions.ServiceError):
        client.put_object(
            "examplenamespace", "owned-bucket", "journal.json", b"{}", if_none_match="*"
        )
    assert len(calls) == 1
    request, kwargs = calls[0]
    assert request.method == "PUT"
    assert (
        request.url
        == "https://objectstorage.uk-london-1.oraclecloud.com/n/examplenamespace/b/owned-bucket/o/journal.json"
    )
    assert request.headers["if-none-match"] == "*"
    assert "authorization" in {key.lower() for key in request.headers}
    assert kwargs["timeout"] == (3, 8)
    assert client.base_client.logger.disabled
    assert client.base_client.session.trust_env is False


def test_storage_rejects_non_oc1_region(credential_environment):
    config = parse_configuration(credential_environment["DEPLOYMENT_CONFIG"])
    credentials = load_signing_credentials(credential_environment, config.fingerprint)
    with pytest.raises(PreflightError, match="unsupported_region"):
        build_storage_client(config, credentials, "us-langley-1")
