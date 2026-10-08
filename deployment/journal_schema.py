"""Strict bounded serialization shared by deployment journal records."""

import json
import re
from uuid import UUID

from .journal_errors import JournalError, require

LIMIT = 65_536
REGION = r"[a-z]{2,5}-[a-z0-9]+-[0-9]{1,2}"
COMPARTMENT = r"ocid1\.compartment\.oc1\.\.[a-zA-Z0-9_-]{1,255}"
BUCKET = r"ocid1\.bucket\.oc1\.[a-z0-9-]*\.[a-zA-Z0-9_-]{1,255}"
NAMESPACE = r"[A-Za-z0-9_-]{1,256}"


def pattern(value, expression):
    require(isinstance(value, str) and re.fullmatch(expression, value) is not None)


def integer(value, minimum=0):
    require(type(value) is int and minimum <= value <= 2**53 - 1)


def uuid(value):
    try:
        require(isinstance(value, str) and str(UUID(value)) == value)
    except (ValueError, AttributeError):
        raise JournalError() from None


def fields(data, expected):
    require(isinstance(data, dict) and set(data) == set(expected))


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result)
        result[key] = value
    return result


def _constant(value):
    raise JournalError()


def decode(raw):
    try:
        require(isinstance(raw, (str, bytes)))
        body = raw.encode("utf-8") if isinstance(raw, str) else raw
        require(len(body) <= LIMIT)
        return json.loads(body.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_constant)
    except (ValueError, UnicodeError, RecursionError):
        raise JournalError() from None


def encode(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False)
