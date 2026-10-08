import json

from deployment.configuration import parse_configuration


def test_only_workload_target_enters_terraform(configuration_json):
    config = parse_configuration(configuration_json)
    expected = {
        "region": "us-ashburn-1",
        "compartment_ocid": "ocid1.compartment.oc1..examplecompartment",
    }
    assert json.loads(config.terraform_json()) == expected
    assert config.orm_variables() == expected
    assert config.terraform_json() == (
        '{\n  "compartment_ocid": "ocid1.compartment.oc1..examplecompartment",\n'
        '  "region": "us-ashburn-1"\n}\n'
    )


def test_mapping_is_independent_and_tracks_a_second_target(configuration_data):
    configuration_data["region"] = "uk-london-1"
    configuration_data["compartment_ocid"] = "ocid1.compartment.oc1..secondtarget"
    config = parse_configuration(json.dumps(configuration_data))
    first = config.orm_variables()
    first["region"] = "changed"
    assert config.orm_variables()["region"] == "uk-london-1"
    assert json.loads(config.terraform_json())["compartment_ocid"] == (
        "ocid1.compartment.oc1..secondtarget"
    )
