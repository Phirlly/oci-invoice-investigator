"""A bounded current-operation slot, not a lease or historical replay ledger."""

from dataclasses import asdict, dataclass

from . import journal_schema as schema
from .journal_errors import require

ACTIONS = frozenset(
    {"deploy", "verify", "reset", "backup", "restore", "upgrade", "recover", "remove"}
)


@dataclass(frozen=True)
class Operation:
    id: str
    action: str
    release: str
    state: str

    def __post_init__(self):
        schema.uuid(self.id)
        require(isinstance(self.action, str) and self.action in ACTIONS)
        schema.pattern(self.release, r"[a-f0-9]{40}")
        require(self.state in ("pending", "completed"))

    @classmethod
    def parse(cls, data):
        schema.fields(data, cls.__dataclass_fields__)
        return cls(**data)

    def to_dict(self):
        return asdict(self)

    def same_identity(self, other):
        return (self.id, self.action, self.release) == (other.id, other.action, other.release)
