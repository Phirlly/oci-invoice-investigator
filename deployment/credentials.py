"""Local credential checks; no remote authentication, enrollment or file fallback."""

import hashlib
import hmac
from dataclasses import dataclass

from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from .errors import PreflightError


@dataclass(frozen=True, repr=False)
class SigningCredentials:
    private_key: str
    passphrase: str | None


@dataclass(frozen=True, repr=False)
class Credentials(SigningCredentials):
    openai_key: str
    presenter_password: str


def _secret(environment, name, limit, optional=False):
    value = environment.get(name)
    if optional and value in (None, ""):
        return None
    try:
        valid = (
            isinstance(value, str)
            and bool(value.strip())
            and "\x00" not in value
            and len(value.encode("utf-8")) <= limit
        )
    except UnicodeError:
        valid = False
    if not valid:
        raise PreflightError("credentials", "credential_invalid", name) from None
    return value


def validate_signing_key(pem, passphrase, fingerprint):
    try:
        key = serialization.load_pem_private_key(
            pem.encode("ascii"), passphrase.encode("ascii") if passphrase is not None else None
        )
        if not isinstance(key, rsa.RSAPrivateKey) or key.key_size < 2048:
            raise ValueError
        der = key.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
        )
    except (ValueError, TypeError, UnicodeError, UnsupportedAlgorithm):
        raise PreflightError("credentials", "private_key_invalid", "OCI_API_PRIVATE_KEY") from None
    # OCI's documented fingerprint identifier, not a password/security digest.
    actual = hashlib.md5(der, usedforsecurity=False).digest().hex(":")
    if not hmac.compare_digest(actual, fingerprint):
        raise PreflightError("credentials", "key_fingerprint_mismatch", "fingerprint")


def load_signing_credentials(environment, fingerprint):
    private_key = _secret(environment, "OCI_API_PRIVATE_KEY", 16_384)
    passphrase = _secret(environment, "OCI_KEY_PASSPHRASE", 1024, optional=True)
    validate_signing_key(private_key, passphrase, fingerprint)
    return SigningCredentials(private_key, passphrase)


def load_credentials(environment, fingerprint):
    signing = load_signing_credentials(environment, fingerprint)
    openai_key = _secret(environment, "OPENAI_API_KEY", 8192)
    password = _secret(environment, "PRESENTER_PASSWORD", 1024)
    if any(char.isspace() for char in openai_key):
        raise PreflightError("credentials", "credential_invalid", "OPENAI_API_KEY")
    return Credentials(signing.private_key, signing.passphrase, openai_key, password)
