import pytest

from deployment.configuration import parse_configuration
from deployment.errors import PreflightError
from deployment.oci_read_checks import check_read_access


@pytest.mark.parametrize(
    "status,expected",
    [
        (401, "authentication_rejected"),
        (403, "access_denied"),
        (404, "unavailable_or_unauthorized"),
        (429, "throttled"),
        (500, "service_unavailable"),
        (409, "request_failed"),
    ],
)
def test_service_errors_never_echo_diagnostics(configuration_json, read_client, status, expected):
    class ServiceFailure(Exception):
        pass

    def denied(*args, **kwargs):
        error = ServiceFailure("sensitive-raw-oci-diagnostic")
        error.status = status
        raise error

    read_client.get_user = denied
    with pytest.raises(PreflightError) as failure:
        check_read_access(parse_configuration(configuration_json), lambda _: read_client)
    assert failure.value.code == expected
    assert "sensitive-raw" not in str(failure.value)
    assert failure.value.__suppress_context__


def test_incomplete_response_is_not_access_success(configuration_json, read_client):
    read_client.user = None
    with pytest.raises(PreflightError) as failure:
        check_read_access(parse_configuration(configuration_json), lambda _: read_client)
    assert failure.value.code == "unexpected_response"


def test_transport_timeout_is_safe(configuration_json, read_client):
    def timeout(*args, **kwargs):
        raise TimeoutError("private endpoint detail")

    read_client.get_tenancy = timeout
    with pytest.raises(PreflightError) as failure:
        check_read_access(parse_configuration(configuration_json), lambda _: read_client)
    assert failure.value.phase == "tenancy"
    assert failure.value.code == "request_timeout"
