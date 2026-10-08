from types import SimpleNamespace as Record

import pytest

from deployment.configuration import parse_configuration
from deployment.errors import PreflightError
from deployment.oci_read_checks import check_read_access


def test_nested_compartment_reaches_configured_tenancy(configuration_json, read_client):
    config = parse_configuration(configuration_json)
    parent = "ocid1.compartment.oc1..parent"
    read_client.compartments[config.compartment_ocid].compartment_id = parent
    read_client.compartments[parent] = Record(
        id=parent, lifecycle_state="ACTIVE", compartment_id=config.tenancy_ocid
    )
    assert check_read_access(config, lambda _: read_client) == "uk-london-1"
    assert [c[1] for c in read_client.calls if c[0] == "get_compartment"] == [
        config.compartment_ocid,
        parent,
    ]


@pytest.mark.parametrize(
    "fault", ["cycle", "wrong-tenancy", "inactive", "wrong-id", "missing-parent", "too-deep"]
)
def test_invalid_ancestry_fails_closed(configuration_json, read_client, fault):
    config = parse_configuration(configuration_json)
    record = read_client.compartments[config.compartment_ocid]
    if fault == "cycle":
        record.compartment_id = record.id
    elif fault == "wrong-tenancy":
        record.compartment_id = "ocid1.tenancy.oc1..other"
    elif fault == "inactive":
        record.lifecycle_state = "DELETED"
    elif fault == "wrong-id":
        record.id = "wrong"
    elif fault == "missing-parent":
        record.compartment_id = None
    else:
        for index in range(8):
            parent = f"ocid1.compartment.oc1..level{index}"
            record.compartment_id = parent
            record = Record(id=parent, lifecycle_state="ACTIVE", compartment_id=config.tenancy_ocid)
            read_client.compartments[parent] = record
    with pytest.raises(PreflightError) as failure:
        check_read_access(config, lambda _: read_client)
    assert failure.value.phase == "compartment"
    assert len([c for c in read_client.calls if c[0] == "get_compartment"]) <= 6
