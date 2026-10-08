import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa

from deployment.configuration import parse_configuration
from deployment.credentials import load_credentials
from deployment.errors import PreflightError


def load(environment):
    fingerprint = parse_configuration(environment["DEPLOYMENT_CONFIG"]).fingerprint
    return load_credentials(environment, fingerprint)


def test_encrypted_key_accepts_only_matching_passphrase(credential_environment, private_key):
    credential_environment["OCI_API_PRIVATE_KEY"] = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.BestAvailableEncryption(b"test-only-passphrase"),
    ).decode("ascii")
    for value in (None, "wrong-passphrase", "unicode-\u00e9"):
        credential_environment["OCI_KEY_PASSPHRASE"] = value
        with pytest.raises(PreflightError):
            load(credential_environment)
    credential_environment["OCI_KEY_PASSPHRASE"] = "test-only-passphrase"
    assert load(credential_environment).passphrase == "test-only-passphrase"


def test_unencrypted_key_rejects_unnecessary_passphrase(credential_environment):
    credential_environment["OCI_KEY_PASSPHRASE"] = "not-used"
    with pytest.raises(PreflightError):
        load(credential_environment)


def test_fingerprint_mismatch_prevents_signing(credential_environment):
    with pytest.raises(PreflightError) as failure:
        load_credentials(credential_environment, ":".join(["ff"] * 16))
    assert failure.value.code == "key_fingerprint_mismatch"


@pytest.mark.parametrize("kind", ["malformed", "public", "small_rsa", "elliptic"])
def test_unsupported_key_is_rejected(credential_environment, private_key, kind):
    if kind == "malformed":
        pem = b"sensitive-invalid-key-sentinel"
    elif kind == "public":
        pem = private_key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
    else:
        key = (
            rsa.generate_private_key(public_exponent=65537, key_size=1024)
            if kind == "small_rsa"
            else ec.generate_private_key(ec.SECP256R1())
        )
        pem = key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    credential_environment["OCI_API_PRIVATE_KEY"] = pem.decode("ascii")
    with pytest.raises(PreflightError) as failure:
        load(credential_environment)
    assert failure.value.code == "private_key_invalid"
    assert pem.decode("ascii") not in str(failure.value)
