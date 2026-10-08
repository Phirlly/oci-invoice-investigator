"""Closed internal controller context and commands; no deployment CLI surface."""

from dataclasses import asdict, dataclass

from . import journal_schema as schema
from .journal_errors import require
from .journal_operations import Operation


def repository_path(value):
    schema.pattern(value, r"[A-Za-z0-9_-]{1,100}/[A-Za-z0-9_.-]{1,100}")
    require(value.split("/")[1] not in (".", ".."))


@dataclass(frozen=True)
class Context:
    repository: str
    repository_id: int
    release: str

    def __post_init__(self):
        repository_path(self.repository)
        schema.integer(self.repository_id, 1)
        schema.pattern(self.release, r"[a-f0-9]{40}")

    @classmethod
    def parse(cls, data):
        schema.fields(data, cls.__dataclass_fields__)
        return cls(**data)


@dataclass(frozen=True)
class Command:
    action: str
    operation: Operation | None = None
    expected_revision: int | None = None

    def __post_init__(self):
        require(self.action in ("initialize", "status", "begin", "complete"))
        if self.action in ("begin", "complete"):
            require(isinstance(self.operation, Operation) and self.operation.state == "pending")
        else:
            require(self.operation is None)
        if self.action == "complete":
            schema.integer(self.expected_revision)
        else:
            require(self.expected_revision is None)

    @classmethod
    def parse(cls, data):
        schema.fields(data, cls.__dataclass_fields__)
        data = dict(data)
        if data["operation"] is not None:
            data["operation"] = Operation.parse(data["operation"])
        return cls(**data)

    def to_dict(self):
        return asdict(self)
