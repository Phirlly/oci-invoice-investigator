from dataclasses import replace

import pytest

from deployment.github_anchor import GitHubAnchor
from deployment.journal_controller import JournalController
from deployment.journal_errors import JournalError
from deployment.journal_request import Command, Context
from deployment.journal_state import Journal
from deployment.journal_store import JournalStore
from tests.deployment.journal.memory_services import GitHub, ObjectStorage


@pytest.fixture
def services():
    return GitHub(), ObjectStorage()


def controller(config, services):
    github, storage = services
    return JournalController(
        config,
        Context("example/invoices", 12345, "a" * 40),
        GitHubAnchor(github, "example/invoices", 12345),
        lambda region: storage,
        lambda: "uk-london-1",
    )


def test_initialize_resume_and_operation_replay_across_fresh_controllers(
    config, services, operation
):
    github, storage = services
    first = controller(config, services).execute(Command("initialize"))
    assert first["revision"] == 0
    original = Journal.parse(storage.body)
    assert controller(config, services).execute(Command("initialize")) == first
    assert github.posts == 1 and storage.puts == 1
    storage.lose_next_response = True
    pending = controller(config, services).execute(Command("begin", operation))
    assert pending["revision"] == 1
    assert controller(config, services).execute(Command("begin", operation)) == pending
    assert storage.puts == 2
    done = controller(config, services).execute(Command("complete", operation, 1))
    assert done["status"] == "OPERATION_COMPLETED"
    recovered = controller(replace(config, region="eu-frankfurt-1"), services).execute(
        Command("status")
    )
    assert recovered["operation"] == done["operation"]
    assert recovered["revision"] == 2
    assert Journal.parse(storage.body).locator == original.locator


def test_lost_anchor_does_not_authorize_bucket_adoption(config, services):
    github, storage = services
    controller(config, services).execute(Command("initialize"))
    original = storage.body
    github.records.clear()
    with pytest.raises(JournalError, match="bucket_conflict"):
        controller(config, services).execute(Command("initialize"))
    assert storage.body == original
    assert storage.puts == 1


def test_recreated_bucket_cannot_adopt_copied_journal(config, services):
    controller(config, services).execute(Command("initialize"))
    storage = services[1]
    storage.bucket.id = "ocid1.bucket.oc1.uk-london-1.recreated"
    with pytest.raises(JournalError, match="journal_conflict"):
        controller(config, services).execute(Command("status"))
    assert storage.puts == 1


def test_two_readers_cannot_overwrite_the_first_operation(config, services, operation):
    controller(config, services).execute(Command("initialize"))
    github, storage = services
    anchor = GitHubAnchor(github, "example/invoices", 12345).find()
    state = Journal.parse(storage.body)
    store = JournalStore(
        storage, anchor, state.namespace, state.bucket_ocid, state.compartment_ocid
    )
    first, stale = store.read(), store.read()
    intended = first.journal.begin(operation, operation.id)
    store.save(first, intended)
    competing = replace(operation, id="00000000-0000-4000-8000-000000000099")
    with pytest.raises(JournalError, match="journal_conflict"):
        store.save(stale, stale.journal.begin(competing, competing.id))
    assert Journal.parse(storage.body) == intended
    assert storage.puts == 3  # Initialization, winning write, rejected stale write.
