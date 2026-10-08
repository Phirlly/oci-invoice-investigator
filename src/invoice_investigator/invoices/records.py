from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True)
class LineKey:
    po_id: str
    line_id: str
    item_code: str
    supplier_id: str
    currency: str
    unit: str


@dataclass(frozen=True)
class InvoiceLine:
    key: LineKey
    quantity: int
    unit_price: Decimal
    line_total: Decimal


@dataclass(frozen=True)
class Invoice:
    case_id: str
    case_version: int
    invoice_id: str
    issued_on: date
    critical_fields_confirmed: bool
    total: Decimal
    lines: tuple[InvoiceLine, ...]
    document_sha256: str


@dataclass(frozen=True)
class PurchaseLine:
    key: LineKey
    quantity: int
    unit_price: Decimal


@dataclass(frozen=True)
class Amendment:
    key: LineKey
    id: str
    version: int
    unit_price: Decimal
    status: str
    approved_by: str
    approved_on: date
    effective_from: date
    effective_until: date | None
    supersedes_id: str | None


@dataclass(frozen=True)
class Receipt:
    key: LineKey
    id: str
    version: int
    quantity: int
    status: str
    received_at: datetime


@dataclass(frozen=True)
class Register:
    case_id: str
    case_version: int
    version: int
    evidence_cutoff: datetime
    amendments_complete: bool
    receipts_complete: bool
    authorized_approvers: tuple[str, ...]
    po_lines: tuple[PurchaseLine, ...]
    amendments: tuple[Amendment, ...]
    receipts: tuple[Receipt, ...]
