"""Private state transitions; only conditional Object Storage writes persist them."""

from dataclasses import asdict, dataclass, replace

from . import journal_schema as schema
from .journal_errors import require
from .journal_locator import Locator, target_digest
from .journal_operations import Operation


@dataclass(frozen=True, repr=False)
class Journal:
    schema_version: int
    anchor_id: int
    locator: Locator
    namespace: str
    bucket_ocid: str
    workload_region: str
    compartment_ocid: str
    revision: int
    write_id: str
    operation: Operation | None

    def __post_init__(self):
        require(type(self.schema_version) is int and self.schema_version == 1)
        schema.integer(self.anchor_id, 1)
        require(isinstance(self.locator, Locator))
        schema.pattern(self.namespace, schema.NAMESPACE)
        schema.pattern(self.bucket_ocid, schema.BUCKET)
        schema.pattern(self.workload_region, schema.REGION)
        schema.pattern(self.compartment_ocid, schema.COMPARTMENT)
        schema.integer(self.revision)
        schema.uuid(self.write_id)
        require(self.operation is None or isinstance(self.operation, Operation))
        require(
            self.locator.target_digest == target_digest(self.workload_region, self.compartment_ocid)
        )
        require((self.revision == 0) == (self.operation is None))

    @classmethod
    def initial(cls, anchor, namespace, bucket_ocid, config, write_id):
        anchor.locator.require_tenancy(config.tenancy_ocid)
        anchor.locator.require_initial_target(config)
        return cls(
            1,
            anchor.id,
            anchor.locator,
            namespace,
            bucket_ocid,
            config.region,
            config.compartment_ocid,
            0,
            write_id,
            None,
        )

    @classmethod
    def parse(cls, raw):
        data = schema.decode(raw)
        schema.fields(data, cls.__dataclass_fields__)
        data["locator"] = Locator.parse(schema.encode(data["locator"]))
        if data["operation"] is not None:
            data["operation"] = Operation.parse(data["operation"])
        return cls(**data)

    def to_bytes(self):
        return schema.encode(asdict(self)).encode()

    def require_binding(self, anchor, namespace, bucket_ocid, compartment):
        require(
            (self.anchor_id, self.locator, self.namespace, self.bucket_ocid, self.compartment_ocid)
            == (anchor.id, anchor.locator, namespace, bucket_ocid, compartment),
            "journal_conflict",
        )

    def begin(self, operation, write_id):
        require(operation.state == "pending")
        if self.operation is not None:
            if self.operation.id == operation.id:
                require(self.operation.same_identity(operation), "operation_conflict")
                return self
            require(self.operation.state == "completed", "operation_busy")
        return replace(self, operation=operation, revision=self.revision + 1, write_id=write_id)

    def complete(self, operation, expected_revision, write_id):
        schema.integer(expected_revision)
        require(expected_revision == self.revision, "journal_conflict")
        require(
            self.operation is not None and self.operation.same_identity(operation),
            "operation_conflict",
        )
        if self.operation.state == "completed":
            return self
        return replace(
            self,
            operation=replace(self.operation, state="completed"),
            revision=self.revision + 1,
            write_id=write_id,
        )
