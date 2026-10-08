from dataclasses import replace
from types import SimpleNamespace as Record

import pytest

from deployment.journal_controller import JournalController
from deployment.journal_errors import JournalError
from deployment.journal_request import Command, Context
from deployment.journal_store import Snapshot


@pytest.fixture
def setup(monkeypatch, config, anchor, journal):
    calls = []

    class Anchors:
        existing = anchor

        def find(self):
            calls.append("anchor")
            return self.existing

        def initialize(self, locator, release):
            calls.append("anchor-create")
            self.existing = replace(anchor, locator=locator)
            return self.existing

    class Storage:
        snapshot = Snapshot(journal, "etag")

        def read(self):
            calls.append("read")
            if self.snapshot is None:
                raise JournalError("journal_missing")
            return self.snapshot

        def initialize(self, state):
            calls.append("journal-create")
            self.snapshot = Snapshot(state, "new-etag")
            return self.snapshot

        def save(self, previous, intended):
            calls.append("save")
            assert previous == self.snapshot
            self.snapshot = Snapshot(intended, "new-etag")
            return self.snapshot

    anchors, storage = Anchors(), Storage()

    def namespace(**kwargs):
        assert kwargs == {"compartment_id": config.tenancy_ocid}
        calls.append("namespace")
        return Record(data=journal.namespace)

    def client(region):
        calls.append(region)
        return Record(get_namespace=namespace)

    def home():
        calls.append("home-verified")
        return "uk-london-1"

    def bucket(*args):
        calls.append("bucket")
        return Record(id=journal.bucket_ocid, compartment_id=journal.compartment_ocid)

    monkeypatch.setattr("deployment.journal_controller.ensure_bucket", bucket)
    monkeypatch.setattr("deployment.journal_controller.JournalStore", lambda *a: storage)
    context = Context("example/invoices", 12345, "a" * 40)
    controller = JournalController(config, context, anchors, client, home)
    return Record(controller=controller, calls=calls, anchors=anchors, storage=storage)


def test_status_recovers_before_mutable_target_preflight(setup, config):
    setup.controller.config = replace(
        config, region="eu-frankfurt-1", compartment_ocid="ocid1.compartment.oc1..other"
    )
    result = setup.controller.execute(Command("status"))
    assert result == {"status": "JOURNAL_STATUS", "revision": 0, "operation": None}
    assert setup.calls == ["anchor", "uk-london-1", "namespace", "bucket", "read"]


def test_wrong_tenancy_stops_before_any_oci_call(setup, config):
    setup.controller.config = replace(config, tenancy_ocid="ocid1.tenancy.oc1..other")
    with pytest.raises(JournalError, match="identity_mismatch"):
        setup.controller.execute(Command("status"))
    assert setup.calls == ["anchor"]


def test_initialization_verifies_home_before_recording_anything(setup):
    setup.anchors.existing = None
    setup.storage.snapshot = None
    result = setup.controller.execute(Command("initialize"))
    assert setup.calls[:3] == ["anchor", "home-verified", "anchor-create"]
    assert setup.calls[-1] == "journal-create"
    assert result["status"] == "JOURNAL_INITIALIZED"
    assert result["revision"] == 0


def test_status_cannot_create_an_anchor(setup):
    setup.anchors.existing = None
    with pytest.raises(JournalError, match="anchor_missing"):
        setup.controller.execute(Command("status"))
    assert setup.calls == ["anchor"]


def test_begin_replay_complete_and_safe_result(setup, operation):
    result = setup.controller.execute(Command("begin", operation))
    assert result["status"] == "OPERATION_PENDING"
    assert result["revision"] == 1
    setup.controller.execute(Command("begin", operation))
    assert setup.calls.count("save") == 1
    done = setup.controller.execute(Command("complete", operation, 1))
    assert done["status"] == "OPERATION_COMPLETED"
    assert done["revision"] == 2
    assert "ocid1." not in str(done)
    assert "namespace" not in str(done)


def test_new_deploy_rejects_changed_target_but_recover_is_available(setup, config, operation):
    setup.controller.config = replace(config, region="eu-frankfurt-1")
    with pytest.raises(JournalError, match="initial_target_changed"):
        setup.controller.execute(Command("begin", operation))
    assert "save" not in setup.calls
    setup.controller.execute(Command("begin", replace(operation, action="recover")))
    assert "save" in setup.calls


def test_incomplete_initialization_rejects_target_drift(setup, config):
    setup.storage.snapshot = None
    setup.controller.config = replace(config, region="eu-frankfurt-1")
    with pytest.raises(JournalError, match="initial_target_changed"):
        setup.controller.execute(Command("initialize"))
    assert "journal-create" not in setup.calls
