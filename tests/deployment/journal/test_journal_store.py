import io
from types import SimpleNamespace as Record

import pytest

from deployment.journal_errors import JournalError
from deployment.journal_store import JournalStore


class ServiceFailure(Exception):
    def __init__(self, status):
        self.status = status


class Client:
    def __init__(self, reads, error=None):
        self.reads = iter(reads)
        self.error = error
        self.puts = []
        self.streams = []

    def get_object(self, *args):
        value = next(self.reads)
        if isinstance(value, Exception):
            raise value
        body, etag = value
        stream = io.BytesIO(body)
        self.streams.append(stream)
        return Record(data=Record(raw=stream, close=stream.close), headers={"etag": etag})

    def put_object(self, *args, **kwargs):
        self.puts.append((args, kwargs))
        if self.error:
            raise self.error
        return Record(headers={"etag": "new-etag"})


def store(client, journal, anchor):
    return JournalStore(
        client, anchor, journal.namespace, journal.bucket_ocid, journal.compartment_ocid
    )


def test_body_and_etag_are_from_same_get_and_stream_is_closed(journal, anchor):
    client = Client([(journal.to_bytes(), "etag-1")])
    snapshot = store(client, journal, anchor).read()
    assert snapshot.journal == journal
    assert snapshot.etag == "etag-1"
    assert client.streams[0].closed


def test_initialize_uses_create_only_condition(journal, anchor):
    client = Client([])
    store(client, journal, anchor).initialize(journal)
    args, kwargs = client.puts[0]
    assert args[-1] == journal.to_bytes()
    assert kwargs == {"if_none_match": "*", "content_type": "application/json"}


def test_update_uses_observed_etag(journal, anchor, operation):
    client = Client([(journal.to_bytes(), "etag-1")])
    storage = store(client, journal, anchor)
    snapshot = storage.read()
    intended = journal.begin(operation, operation.id)
    storage.save(snapshot, intended)
    assert client.puts[0][1] == {"if_match": "etag-1", "content_type": "application/json"}


@pytest.mark.parametrize(
    "error", [TimeoutError("sensitive"), ServiceFailure(412), ServiceFailure(500)]
)
def test_lost_write_is_success_only_if_exact_intended_state_observed(
    journal, anchor, operation, error
):
    intended = journal.begin(operation, operation.id)
    client = Client([(journal.to_bytes(), "etag-1"), (intended.to_bytes(), "etag-2")], error)
    storage = store(client, journal, anchor)
    assert storage.save(storage.read(), intended).journal == intended
    assert len(client.puts) == 1


@pytest.mark.parametrize(
    "observed,code", [("old", "journal_conflict"), ("unreadable", "outcome_unknown")]
)
def test_uncertain_put_is_not_blindly_retried(journal, anchor, operation, observed, code):
    next_read = (journal.to_bytes(), "etag-2") if observed == "old" else TimeoutError()
    client = Client([(journal.to_bytes(), "etag-1"), next_read], TimeoutError())
    storage = store(client, journal, anchor)
    with pytest.raises(JournalError, match=code):
        storage.save(storage.read(), journal.begin(operation, operation.id))
    assert len(client.puts) == 1


@pytest.mark.parametrize(
    "body,etag", [(b" " * 65_537, "etag"), (b"private-invalid", "etag"), (b"{}", "*")]
)
def test_untrusted_object_is_bounded_and_closed(journal, anchor, body, etag):
    client = Client([(body, etag)])
    with pytest.raises(JournalError):
        store(client, journal, anchor).read()
    assert client.streams[0].closed


def test_absent_or_denied_state_not_success(journal, anchor):
    client = Client([ServiceFailure(404)])
    with pytest.raises(JournalError, match="journal_missing"):
        store(client, journal, anchor).read()
