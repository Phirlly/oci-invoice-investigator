import json
import socket

import pytest

from deployment.configuration import parse_configuration


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Journal tests must intercept service calls before network access")

    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)


@pytest.fixture
def config(configuration_json):
    return parse_configuration(configuration_json)


@pytest.fixture
def locator(config):
    from deployment.journal_locator import Locator

    return Locator.create(config, 12345, "uk-london-1", "00000000-0000-4000-8000-000000000001")


@pytest.fixture
def anchor(locator):
    from deployment.journal_locator import Anchor

    return Anchor(101, locator)


@pytest.fixture
def journal(config, anchor):
    from deployment.journal_state import Journal

    return Journal.initial(
        anchor,
        "examplenamespace",
        "ocid1.bucket.oc1.uk-london-1.examplebucket",
        config,
        "00000000-0000-4000-8000-000000000002",
    )


@pytest.fixture
def operation():
    from deployment.journal_operations import Operation

    return Operation("00000000-0000-4000-8000-000000000003", "deploy", "a" * 40, "pending")


@pytest.fixture
def github_record(anchor):
    return {
        "id": anchor.id,
        "task": "invoice-control-v1",
        "environment": "demo",
        "original_environment": "demo",
        "payload": json.loads(anchor.locator.to_json()),
    }
