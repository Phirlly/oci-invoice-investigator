"""Strict fields for version 1 synthetic invoice input, with bounded arithmetic."""

import re
from datetime import date, datetime
from decimal import Decimal


class InputError(ValueError):
    """Input is malformed, unsupported, or outside its declared case snapshot."""


def fields(value, names):
    if not isinstance(value, dict) or set(value) != set(names.split()):
        raise InputError("Object fields do not match the supported schema.")
    return value.copy()


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", value):
        raise InputError("Identifiers must contain 1-64 ASCII letters, digits, '_' or '-'.")
    return value


def integer(value):
    if type(value) is not int or not 1 <= value <= 1_000_000:
        raise InputError("Quantities and versions must be whole numbers from 1 to 1000000.")
    return value


def flag(value):
    if type(value) is not bool:
        raise InputError("Completeness and confirmation flags must be boolean.")
    return value


def money(value):
    if not isinstance(value, str) or not re.fullmatch(r"(0|[1-9][0-9]{0,8})\.[0-9]{2}", value):
        raise InputError("Amounts must be nonnegative two-decimal strings below 1000000000.")
    return Decimal(value)


def choice(value, allowed):
    if not isinstance(value, str) or value not in allowed:
        raise InputError("Unsupported currency, unit or record status.")
    return value


def day(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise InputError("Dates must use YYYY-MM-DD.")
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise InputError("Invalid calendar date.") from error


def timestamp(value):
    if not isinstance(value, str) or not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", value
    ):
        raise InputError("Timestamps must use UTC YYYY-MM-DDTHH:MM:SSZ.")
    try:
        return datetime.fromisoformat(value)
    except ValueError as error:
        raise InputError("Invalid UTC timestamp.") from error


def collection(value):
    if not isinstance(value, list) or len(value) > 1000:
        raise InputError("Collections must be arrays with at most 1000 records.")
    return value


def unique(values):
    if len(values) != len(set(values)):
        raise InputError("Duplicate record or line identifiers are unsupported.")


def digest(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value):
        raise InputError("Expected a lowercase SHA-256 digest.")
    return value


def versioned(value, names):
    result = fields(value, "schema_version case_id case_version " + names)
    if type(result.pop("schema_version")) is not int or value["schema_version"] != 1:
        raise InputError("Only schema_version 1 is supported.")
    result["case_id"] = identifier(result["case_id"])
    result["case_version"] = integer(result["case_version"])
    return result
