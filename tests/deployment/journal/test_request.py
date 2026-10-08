import pytest

from deployment.journal_errors import JournalError
from deployment.journal_request import Command, Context


@pytest.mark.parametrize(
    "data",
    [
        {"action": "shell", "operation": None, "expected_revision": None},
        {"action": "begin", "operation": None, "expected_revision": None},
        {"action": "status", "operation": None, "expected_revision": 1},
        {"action": "status", "operation": None, "expected_revision": None, "secret": "sensitive"},
    ],
)
def test_command_rejects_unsupported_and_incoherent_inputs(data):
    with pytest.raises(JournalError):
        Command.parse(data)


def test_complete_requires_expected_revision(operation):
    with pytest.raises(JournalError):
        Command("complete", operation)
    assert Command.parse(Command("complete", operation, 1).to_dict()) == Command(
        "complete", operation, 1
    )


@pytest.mark.parametrize("repository", ["a/../b", "https://untrusted.invalid", "a/..", "a/ b"])
def test_context_rejects_untrusted_paths(repository):
    with pytest.raises(JournalError):
        Context(repository, 12345, "a" * 40)
