import json

import pytest

from deployment.configuration import parse_configuration
from deployment.errors import PreflightError


def test_configuration_preserves_explicit_inputs(configuration_json):
    config = parse_configuration(configuration_json)
    assert config.region == "us-ashburn-1"
    assert config.presenter_username == "demo.reviewer"
    assert config.user_ocid == "ocid1.user.oc1..exampleuser"


@pytest.mark.parametrize("payload", ["", "[]", "null", "true", "{", "NaN", "[" * 2000])
def test_invalid_json_has_owned_error_without_echo(payload):
    with pytest.raises(PreflightError) as failure:
        parse_configuration(payload)
    assert failure.value.code == "configuration_invalid"
    assert failure.value.phase == "configuration"


@pytest.mark.parametrize("value", [True, 1.0, "1", 2, None])
def test_version_is_exact_integer_one(configuration_data, value):
    configuration_data["schema_version"] = value
    with pytest.raises(PreflightError):
        parse_configuration(json.dumps(configuration_data))


@pytest.mark.parametrize(
    "field,value",
    [
        ("tenancy_ocid", "ocid1.tenancy.oc2..wrongrealm"),
        ("user_ocid", "ocid1.compartment.oc1..wrongtype"),
        ("compartment_ocid", "ocid1.tenancy.oc1..root"),
        ("region", "https://untrusted.invalid"),
        ("region", "us-ashburn-1\n"),
        ("presenter_username", '${file("secret")}'),
        ("presenter_username", "reviewer\n"),
        ("fingerprint", "12:34"),
        ("user_ocid", 123),
    ],
)
def test_invalid_field_values_fail_without_echo(configuration_data, field, value):
    configuration_data[field] = value
    with pytest.raises(PreflightError) as failure:
        parse_configuration(json.dumps(configuration_data))
    assert str(value) not in str(failure.value)
    assert failure.value.field == field


def test_missing_and_unknown_secret_keys_are_rejected(configuration_data):
    for field in ("OPENAI_API_KEY", "private_key", "untrusted-key-secret"):
        payload = {**configuration_data, field: "sensitive-input-sentinel"}
        with pytest.raises(PreflightError) as failure:
            parse_configuration(json.dumps(payload))
        assert field not in str(failure.value)
        assert "sensitive-input-sentinel" not in str(failure.value)
    configuration_data.pop("region")
    with pytest.raises(PreflightError):
        parse_configuration(json.dumps(configuration_data))


def test_duplicate_key_in_otherwise_valid_configuration_is_rejected(configuration_json):
    payload = configuration_json[:-1] + ', "region": "uk-london-1"}'
    assert json.loads(payload)["region"] == "uk-london-1"
    with pytest.raises(PreflightError):
        parse_configuration(payload)


@pytest.mark.parametrize("payload", [" " * 16385, '"\\ud800"', '{"x":Infinity}'])
def test_size_unicode_and_nonfinite_numbers_are_bounded(payload):
    with pytest.raises(PreflightError):
        parse_configuration(payload)
