"""Public locator contains hashes, never cloud inventory or credentials."""

import hashlib
from dataclasses import asdict, dataclass

from . import journal_schema as schema
from .journal_errors import require


def tenancy_digest(tenancy):
    return hashlib.sha256(("invoice-tenant-v1:" + tenancy).encode()).hexdigest()


def target_digest(region, compartment):
    return hashlib.sha256(
        ("invoice-target-v1:" + schema.encode([region, compartment])).encode()
    ).hexdigest()


@dataclass(frozen=True, repr=False)
class Locator:
    schema_version: int
    repository_id: int
    environment: str
    installation_id: str
    tenancy_digest: str
    control_region: str
    target_digest: str

    def __post_init__(self):
        require(type(self.schema_version) is int and self.schema_version == 1)
        schema.integer(self.repository_id, 1)
        require(self.environment == "demo")
        schema.uuid(self.installation_id)
        schema.pattern(self.control_region, schema.REGION)
        schema.pattern(self.tenancy_digest, r"[a-f0-9]{64}")
        schema.pattern(self.target_digest, r"[a-f0-9]{64}")

    @classmethod
    def create(cls, config, repository_id, control_region, installation_id):
        return cls(
            1,
            repository_id,
            "demo",
            installation_id,
            tenancy_digest(config.tenancy_ocid),
            control_region,
            target_digest(config.region, config.compartment_ocid),
        )

    @classmethod
    def parse(cls, raw):
        data = schema.decode(raw)
        schema.fields(data, cls.__dataclass_fields__)
        return cls(**data)

    def to_json(self):
        return schema.encode(asdict(self))

    @property
    def bucket_name(self):
        identity = f"{self.repository_id}/{self.environment}"
        return "invoice-control-" + hashlib.sha256(identity.encode()).hexdigest()[:24]

    def require_tenancy(self, tenancy):
        require(self.tenancy_digest == tenancy_digest(tenancy), "identity_mismatch")

    def require_initial_target(self, config):
        require(
            self.target_digest == target_digest(config.region, config.compartment_ocid),
            "initial_target_changed",
        )


@dataclass(frozen=True, repr=False)
class Anchor:
    id: int
    locator: Locator

    def __post_init__(self):
        schema.integer(self.id, 1)
        require(isinstance(self.locator, Locator))
