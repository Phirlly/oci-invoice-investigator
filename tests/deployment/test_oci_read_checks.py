import pytest

from deployment.configuration import parse_configuration
from deployment.errors import PreflightError
from deployment.oci_read_checks import check_read_access


def test_only_scoped_reads_are_used_and_home_region_is_discovered(configuration_json, read_client):
    regions = []

    def client_for_region(region):
        regions.append(region)
        return read_client

    result = check_read_access(parse_configuration(configuration_json), client_for_region)
    assert result == "uk-london-1"
    assert regions == ["us-ashburn-1", "uk-london-1"]
    assert [call[0] for call in read_client.calls] == [
        "get_user",
        "get_tenancy",
        "list_region_subscriptions",
        "get_compartment",
    ]


@pytest.mark.parametrize(
    "field,value",
    [("id", "wrong"), ("lifecycle_state", "DELETED"), ("compartment_id", "wrong-tenancy")],
)
def test_user_identity_must_match(configuration_json, read_client, field, value):
    setattr(read_client.user, field, value)
    with pytest.raises(PreflightError) as failure:
        check_read_access(parse_configuration(configuration_json), lambda _: read_client)
    assert failure.value.phase == "user"
    assert len(read_client.calls) == 1


@pytest.mark.parametrize(
    "fault", ["wrong-tenancy", "missing-home", "two-homes", "wrong-key", "pending", "duplicate"]
)
def test_tenancy_and_region_coherence(configuration_json, read_client, fault):
    if fault == "wrong-tenancy":
        read_client.tenancy.id = "wrong"
    elif fault == "missing-home":
        read_client.regions.pop()
    elif fault == "two-homes":
        read_client.regions[0].is_home_region = True
    elif fault == "wrong-key":
        read_client.tenancy.home_region_key = "OTHER"
    elif fault == "pending":
        read_client.regions[0].status = "IN_PROGRESS"
    else:
        read_client.regions.append(read_client.regions[0])
    with pytest.raises(PreflightError):
        check_read_access(parse_configuration(configuration_json), lambda _: read_client)
    assert not any(call[0] == "get_compartment" for call in read_client.calls)
