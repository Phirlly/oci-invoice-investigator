import hashlib
import json
from types import SimpleNamespace as Record

import pytest


@pytest.fixture
def configuration_data():
    return {
        "schema_version": 1,
        "tenancy_ocid": "ocid1.tenancy.oc1..exampletenancy",
        "user_ocid": "ocid1.user.oc1..exampleuser",
        "fingerprint": ":".join(["12"] * 16),
        "region": "us-ashburn-1",
        "compartment_ocid": "ocid1.compartment.oc1..examplecompartment",
        "presenter_username": "demo.reviewer",
    }


@pytest.fixture
def configuration_json(configuration_data):
    return json.dumps(configuration_data)


@pytest.fixture(scope="module")
def private_key():
    from cryptography.hazmat.primitives.asymmetric import rsa

    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def credential_environment(private_key, configuration_data):
    from cryptography.hazmat.primitives import serialization

    der = private_key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    configuration_data["fingerprint"] = hashlib.md5(der, usedforsecurity=False).digest().hex(":")
    pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode("ascii")
    return {
        "DEPLOYMENT_CONFIG": json.dumps(configuration_data),
        "OCI_API_PRIVATE_KEY": pem,
        "OPENAI_API_KEY": "synthetic-model-credential",
        "PRESENTER_PASSWORD": "synthetic-presenter-credential",
    }


@pytest.fixture
def read_client(configuration_data):
    class Client:
        def __init__(self):
            self.calls = []
            self.user = Record(
                id=configuration_data["user_ocid"],
                lifecycle_state="ACTIVE",
                compartment_id=configuration_data["tenancy_ocid"],
            )
            self.tenancy = Record(id=configuration_data["tenancy_ocid"], home_region_key="LHR")
            self.regions = [
                Record(
                    region_name="us-ashburn-1",
                    region_key="IAD",
                    status="READY",
                    is_home_region=False,
                ),
                Record(
                    region_name="uk-london-1", region_key="LHR", status="READY", is_home_region=True
                ),
            ]
            self.compartments = {
                configuration_data["compartment_ocid"]: Record(
                    id=configuration_data["compartment_ocid"],
                    lifecycle_state="ACTIVE",
                    compartment_id=configuration_data["tenancy_ocid"],
                )
            }

        def get_user(self, identity, **kwargs):
            self.calls.append(("get_user", identity, kwargs))
            return Record(data=self.user)

        def get_tenancy(self, identity, **kwargs):
            self.calls.append(("get_tenancy", identity, kwargs))
            return Record(data=self.tenancy)

        def list_region_subscriptions(self, identity, **kwargs):
            self.calls.append(("list_region_subscriptions", identity, kwargs))
            return Record(data=self.regions)

        def get_compartment(self, identity, **kwargs):
            self.calls.append(("get_compartment", identity, kwargs))
            return Record(data=self.compartments[identity])

    return Client()
