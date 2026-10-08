"""GET-only identity/target coherence checks; no policy simulation or provisioning."""

import re

from .errors import PreflightError


def _require(condition, phase, code="unexpected_response"):
    if not condition:
        raise PreflightError(phase, code)


def _request(phase, method, *args):
    try:
        response = method(*args)
        return response.data
    except PreflightError:
        raise
    except Exception as error:
        status = getattr(error, "status", None)
        code = (
            {
                401: "authentication_rejected",
                403: "access_denied",
                404: "unavailable_or_unauthorized",
                429: "throttled",
            }.get(status, "request_failed")
            if type(status) is int
            else "request_failed"
        )
        if type(status) is int and 500 <= status < 600:
            code = "service_unavailable"
        if isinstance(error, TimeoutError):
            code = "request_timeout"
        raise PreflightError(phase, code) from None


def _home_region(regions, region, home_key):
    _require(isinstance(regions, list) and 0 < len(regions) <= 1024, "regions")
    names = [getattr(item, "region_name", None) for item in regions]
    _require(all(isinstance(name, str) for name in names), "regions")
    _require(len(set(names)) == len(names), "regions")
    _require(
        all(type(getattr(item, "is_home_region", None)) is bool for item in regions), "regions"
    )
    home = [item for item in regions if item.is_home_region]
    target = [item for item in regions if item.region_name == region]
    _require(len(home) == 1 and len(target) == 1, "regions", "region_unavailable")
    _require(
        getattr(home[0], "status", None) == "READY"
        and getattr(target[0], "status", None) == "READY"
        and getattr(home[0], "region_key", None) == home_key,
        "regions",
        "region_unavailable",
    )
    return home[0].region_name


def _check_ancestry(client, config):
    current = config.compartment_ocid
    visited = set()
    for _ in range(6):
        _require(
            isinstance(current, str)
            and current not in visited
            and re.fullmatch(r"ocid1\.compartment\.oc1\.\.[a-zA-Z0-9_-]{1,255}", current),
            "compartment",
            "target_mismatch",
        )
        visited.add(current)
        item = _request("compartment", client.get_compartment, current)
        _require(
            getattr(item, "id", None) == current
            and getattr(item, "lifecycle_state", None) == "ACTIVE",
            "compartment",
            "target_mismatch",
        )
        current = getattr(item, "compartment_id", None)
        if current == config.tenancy_ocid:
            return
    raise PreflightError("compartment", "target_mismatch")


def check_read_access(config, client_for_region):
    client = client_for_region(config.region)
    user = _request("user", client.get_user, config.user_ocid)
    _require(user is not None, "user")
    _require(
        getattr(user, "id", None) == config.user_ocid
        and getattr(user, "lifecycle_state", None) == "ACTIVE"
        and getattr(user, "compartment_id", None) == config.tenancy_ocid,
        "user",
        "identity_mismatch",
    )
    tenancy = _request("tenancy", client.get_tenancy, config.tenancy_ocid)
    _require(getattr(tenancy, "id", None) == config.tenancy_ocid, "tenancy", "identity_mismatch")
    home_key = getattr(tenancy, "home_region_key", None)
    _require(isinstance(home_key, str) and bool(home_key), "tenancy")
    regions = _request("regions", client.list_region_subscriptions, config.tenancy_ocid)
    home = _home_region(regions, config.region, home_key)
    home_client = client_for_region(home)
    _check_ancestry(home_client, config)
    return home
