from dataclasses import replace

import pytest

from deployment.journal_errors import JournalError
from deployment.journal_operations import Operation

WRITE = "00000000-0000-4000-8000-000000000004"


def test_start_complete_and_current_operation_replay(journal, operation):
    pending = journal.begin(operation, WRITE)
    assert pending.revision == 1
    assert pending.operation == operation
    assert pending.begin(operation, journal.write_id) is pending
    done = pending.complete(operation, 1, journal.write_id)
    assert done.operation.state == "completed"
    assert done.revision == 2
    assert done.begin(operation, WRITE) is done
    assert done.complete(operation, 2, WRITE) is done


def test_other_pending_intent_blocks_and_changed_identity_conflicts(journal, operation):
    pending = journal.begin(operation, WRITE)
    with pytest.raises(JournalError, match="operation_busy"):
        pending.begin(replace(operation, id=WRITE), journal.write_id)
    for changed in (replace(operation, action="remove"), replace(operation, release="b" * 40)):
        with pytest.raises(JournalError, match="operation_conflict"):
            pending.begin(changed, journal.write_id)
        with pytest.raises(JournalError, match="operation_conflict"):
            pending.complete(changed, 1, journal.write_id)


def test_completion_requires_pending_identity_and_current_revision(journal, operation):
    with pytest.raises(JournalError):
        journal.complete(operation, 0, WRITE)
    pending = journal.begin(operation, WRITE)
    with pytest.raises(JournalError, match="journal_conflict"):
        pending.complete(operation, 0, journal.write_id)


def test_completed_slot_can_be_replaced_without_historical_replay_guarantee(journal, operation):
    done = journal.begin(operation, WRITE).complete(operation, 1, journal.write_id)
    next_operation = replace(operation, id=WRITE, action="verify")
    next_state = done.begin(next_operation, journal.write_id)
    assert next_state.operation == next_operation
    assert next_state.revision == 3
    with pytest.raises(JournalError, match="operation_busy"):
        next_state.begin(operation, WRITE)


@pytest.mark.parametrize(
    "field,value",
    [("action", "shell"), ("release", "main"), ("state", "ready"), ("id", "sensitive")],
)
def test_operation_fields_are_closed(operation, field, value):
    with pytest.raises(JournalError):
        Operation.parse({**operation.to_dict(), field: value})
