"""Bounded Object Storage journal reads and conditional, reconciled writes."""

from dataclasses import dataclass

from . import journal_schema as schema
from .journal_errors import JournalError, require
from .journal_state import Journal

OBJECT_NAME = "operation-journal-v1.json"


def _etag(value):
    # An opaque ETag is passed back intact; wildcard, weak and list forms are forbidden.
    schema.pattern(value, r'(?:[A-Za-z0-9_-]{1,256}|"[A-Za-z0-9_-]{1,256}")')
    return value


@dataclass(frozen=True, repr=False)
class Snapshot:
    journal: Journal
    etag: str


class JournalStore:
    def __init__(self, client, anchor, namespace, bucket_ocid, compartment):
        self.client, self.anchor = client, anchor
        self.namespace, self.bucket_ocid, self.compartment = namespace, bucket_ocid, compartment

    def _binding(self, journal):
        journal.require_binding(self.anchor, self.namespace, self.bucket_ocid, self.compartment)

    @property
    def _location(self):
        return self.namespace, self.anchor.locator.bucket_name, OBJECT_NAME

    def read(self):
        try:
            response = self.client.get_object(*self._location)
        except Exception as error:
            code = (
                "journal_missing"
                if getattr(error, "status", None) == 404
                else "storage_unavailable"
            )
            raise JournalError(code) from None
        try:
            body = response.data.raw.read(schema.LIMIT + 1)
            journal = Journal.parse(body)
            self._binding(journal)
            return Snapshot(journal, _etag(response.headers.get("etag")))
        except JournalError:
            raise
        except Exception:
            raise JournalError("storage_unavailable") from None
        finally:
            response.data.close()

    def initialize(self, journal):
        self._binding(journal)
        require(journal.revision == 0)
        return self._write(journal, {"if_none_match": "*"})

    def save(self, snapshot, intended):
        self._binding(snapshot.journal)
        self._binding(intended)
        require(
            intended.revision == snapshot.journal.revision + 1
            and intended.write_id != snapshot.journal.write_id,
            "journal_conflict",
        )
        return self._write(intended, {"if_match": _etag(snapshot.etag)})

    def _write(self, intended, condition):
        try:
            response = self.client.put_object(
                *self._location, intended.to_bytes(), content_type="application/json", **condition
            )
            return Snapshot(intended, _etag(response.headers.get("etag")))
        except Exception:
            # Only exact intended state establishes the lost write; never retry PUT.
            pass
        try:
            observed = self.read()
        except Exception:
            raise JournalError("outcome_unknown") from None
        require(observed.journal == intended, "journal_conflict")
        return observed
