from dataclasses import asdict, dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Evidence:
    source: str
    version: int
    locator: str


@dataclass(frozen=True)
class Decision:
    value: Decimal | int | None
    evidence: tuple[Evidence, ...]
    issue: str | None = None


@dataclass(frozen=True)
class Finding:
    code: str
    line_id: str | None
    detail: str
    evidence: tuple[Evidence, ...]
    next_step: str


@dataclass(frozen=True)
class LineResult:
    line_id: str
    expected_unit_price: str | None
    received_quantity: int | None
    missing_receipt_quantity: int | None
    price_evidence: tuple[Evidence, ...]
    receipt_evidence: tuple[Evidence, ...]


@dataclass(frozen=True)
class Snapshot:
    case_id: str
    case_version: int
    document_sha256: str
    purchasing_version: int
    evidence_cutoff: str


@dataclass(frozen=True)
class Result:
    snapshot: Snapshot
    conclusion: str
    lines: tuple[LineResult, ...]
    findings: tuple[Finding, ...]
    mode: str = "offline_normalized_comparison"

    def to_dict(self):
        return asdict(self)


def register_evidence(register, locator):
    return Evidence("purchasing.json", register.version, locator)
