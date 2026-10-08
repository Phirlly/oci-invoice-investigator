"""Recover control state before consulting the mutable workload target."""

from uuid import uuid4

from . import journal_schema as schema
from .journal_bucket import ensure_bucket
from .journal_errors import JournalError, require
from .journal_locator import Locator
from .journal_state import Journal
from .journal_store import JournalStore


class JournalController:
    def __init__(self, config, context, anchors, storage_for_region, discover_home):
        self.config, self.context, self.anchors = config, context, anchors
        self.storage_for_region, self.discover_home = storage_for_region, discover_home

    def execute(self, command):
        if command.operation is not None:
            require(command.operation.release == self.context.release, "operation_conflict")
        anchor = self.anchors.find()
        if anchor is None:
            require(command.action == "initialize", "anchor_missing")
            home = self.discover_home()
            locator = Locator.create(self.config, self.context.repository_id, home, str(uuid4()))
            anchor = self.anchors.initialize(locator, self.context.release)
        anchor.locator.require_tenancy(self.config.tenancy_ocid)
        require(anchor.locator.repository_id == self.context.repository_id, "identity_mismatch")
        client = self.storage_for_region(anchor.locator.control_region)
        try:
            namespace = client.get_namespace(compartment_id=self.config.tenancy_ocid).data
        except Exception:
            raise JournalError("storage_unavailable") from None
        schema.pattern(namespace, schema.NAMESPACE)
        initialize = command.action == "initialize"
        bucket = ensure_bucket(client, anchor, namespace, self.config, initialize)
        store = JournalStore(client, anchor, namespace, bucket.id, bucket.compartment_id)
        try:
            snapshot = store.read()
        except JournalError as error:
            if error.code != "journal_missing" or not initialize:
                raise
            initial = Journal.initial(anchor, namespace, bucket.id, self.config, str(uuid4()))
            snapshot = store.initialize(initial)
        journal = snapshot.journal
        if command.action == "begin":
            if command.operation.action == "deploy":
                anchor.locator.require_initial_target(self.config)
            intended = journal.begin(command.operation, str(uuid4()))
        elif command.action == "complete":
            intended = journal.complete(command.operation, command.expected_revision, str(uuid4()))
        else:
            intended = journal
        if intended is not journal:
            journal = store.save(snapshot, intended).journal
        if command.action in ("begin", "complete"):
            status = "OPERATION_" + journal.operation.state.upper()
        else:
            status = "JOURNAL_INITIALIZED" if initialize else "JOURNAL_STATUS"
        return {
            "status": status,
            "revision": journal.revision,
            "operation": journal.operation.to_dict() if journal.operation else None,
        }
