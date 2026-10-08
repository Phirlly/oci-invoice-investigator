import pytest

from deployment.configuration import parse_configuration
from deployment.credentials import load_credentials
from deployment.errors import PreflightError


def load(environment):
    config = parse_configuration(environment["DEPLOYMENT_CONFIG"])
    return load_credentials(environment, config.fingerprint)


def test_local_key_validation_and_secret_repr(credential_environment):
    credentials = load(credential_environment)
    assert credentials.private_key == credential_environment["OCI_API_PRIVATE_KEY"]
    assert credentials.passphrase is None
    for name in ("OCI_API_PRIVATE_KEY", "OPENAI_API_KEY", "PRESENTER_PASSWORD"):
        assert credential_environment[name] not in repr(credentials)


@pytest.mark.parametrize("name", ["OCI_API_PRIVATE_KEY", "OPENAI_API_KEY", "PRESENTER_PASSWORD"])
@pytest.mark.parametrize("value", [None, "", "\x00secret", 123])
def test_missing_and_invalid_credentials_are_safe(credential_environment, name, value):
    credential_environment[name] = value
    with pytest.raises(PreflightError) as failure:
        load(credential_environment)
    assert failure.value.phase == "credentials"
    assert failure.value.field == name
    assert "secret" not in str(failure.value)


@pytest.mark.parametrize("name", ["OCI_API_PRIVATE_KEY", "OPENAI_API_KEY", "PRESENTER_PASSWORD"])
def test_oversized_secrets_fail_before_parsing(credential_environment, name):
    credential_environment[name] = "sensitive-sentinel" * 2000
    with pytest.raises(PreflightError) as failure:
        load(credential_environment)
    assert "sensitive-sentinel" not in str(failure.value)


def test_model_credential_whitespace_rejected_without_claiming_remote_validity(
    credential_environment,
):
    credential_environment["OPENAI_API_KEY"] = "contains whitespace"
    with pytest.raises(PreflightError):
        load(credential_environment)
