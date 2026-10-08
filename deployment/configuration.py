"""Strict, nonsecret inputs for the first deployment preflight contract."""

import json
import re
from dataclasses import dataclass

from .errors import PreflightError

CONFIGURATION_LIMIT = 16_384
FIELDS = frozenset(
    {
        "schema_version",
        "tenancy_ocid",
        "user_ocid",
        "fingerprint",
        "region",
        "compartment_ocid",
        "presenter_username",
    }
)


@dataclass(frozen=True, repr=False)
class Configuration:
    schema_version: int
    tenancy_ocid: str
    user_ocid: str
    fingerprint: str
    region: str
    compartment_ocid: str
    presenter_username: str

    def orm_variables(self):
        # Authentication and presenter metadata never become Terraform inputs.
        return {"compartment_ocid": self.compartment_ocid, "region": self.region}

    def terraform_json(self):
        return json.dumps(self.orm_variables(), sort_keys=True, indent=2) + "\n"


def _invalid(field=None):
    raise PreflightError("configuration", "configuration_invalid", field) from None


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _invalid()
        result[key] = value
    return result


def _nonfinite(value):
    _invalid()


def parse_configuration(raw):
    if not isinstance(raw, str):
        _invalid()
    try:
        if len(raw.encode("utf-8")) > CONFIGURATION_LIMIT:
            _invalid()
        data = json.loads(raw, object_pairs_hook=_unique_object, parse_constant=_nonfinite)
    except (ValueError, UnicodeError, RecursionError):
        _invalid()
    if not isinstance(data, dict) or set(data) != FIELDS:
        _invalid()
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        _invalid("schema_version")
    patterns = {
        "region": r"[a-z]{2,5}-[a-z0-9]+-[0-9]{1,2}",
        "presenter_username": r"[A-Za-z0-9@.+_-]{1,150}",
        "fingerprint": r"[0-9a-f]{2}(?::[0-9a-f]{2}){15}",
    }
    for field, resource in (
        ("tenancy_ocid", "tenancy"),
        ("user_ocid", "user"),
        ("compartment_ocid", "compartment"),
    ):
        patterns[field] = rf"ocid1\.{resource}\.oc1\.\.[a-zA-Z0-9_-]{{1,255}}"
    for field, pattern in patterns.items():
        if not isinstance(data[field], str) or not re.fullmatch(pattern, data[field]):
            _invalid(field)
    return Configuration(**data)
