"""Translate untrusted serialized values into bounded, immutable domain records."""

from .input_fields import (
    InputError,
    choice,
    collection,
    day,
    digest,
    fields,
    flag,
    identifier,
    integer,
    money,
    timestamp,
    unique,
    versioned,
)
from .records import Amendment, Invoice, InvoiceLine, LineKey, PurchaseLine, Receipt, Register

__all__ = ["InputError", "parse_invoice", "parse_register"]

KEY_FIELDS = "po_id line_id item_code supplier_id currency unit"


def _line_fields(value, extra):
    result = fields(value, KEY_FIELDS + " " + extra)
    key = {name: identifier(result.pop(name)) for name in KEY_FIELDS.split()}
    choice(key["currency"], {"USD"})
    choice(key["unit"], {"EA"})
    return {"key": LineKey(**key), **result}


def _invoice_line(value):
    line = _line_fields(value, "quantity unit_price line_total")
    line["quantity"] = integer(line["quantity"])
    line["unit_price"] = money(line["unit_price"])
    line["line_total"] = money(line["line_total"])
    return InvoiceLine(**line)


def parse_invoice(value, document_sha256):
    record = versioned(value, "invoice_id issued_on critical_fields_confirmed total lines")
    record["invoice_id"] = identifier(record["invoice_id"])
    record["issued_on"] = day(record["issued_on"])
    record["critical_fields_confirmed"] = flag(record["critical_fields_confirmed"])
    record["total"] = money(record["total"])
    lines = tuple(_invoice_line(line) for line in collection(record["lines"]))
    if not lines or len({(line.key.po_id, line.key.supplier_id) for line in lines}) != 1:
        raise InputError("An invoice must contain lines for one supplier and purchase order.")
    unique([line.key.line_id for line in lines])
    record["lines"] = lines
    return Invoice(**record, document_sha256=digest(document_sha256))


def _purchase_line(value):
    line = _line_fields(value, "quantity unit_price")
    return PurchaseLine(line["key"], integer(line["quantity"]), money(line["unit_price"]))


def _amendment(value):
    record = _line_fields(
        value,
        "id version unit_price status approved_by approved_on "
        "effective_from effective_until supersedes_id",
    )
    record["id"] = identifier(record["id"])
    record["version"] = integer(record["version"])
    record["unit_price"] = money(record["unit_price"])
    record["status"] = choice(record["status"], {"approved", "draft", "cancelled"})
    record["approved_by"] = identifier(record["approved_by"])
    record["approved_on"] = day(record["approved_on"])
    record["effective_from"] = day(record["effective_from"])
    if record["effective_until"] is not None:
        record["effective_until"] = day(record["effective_until"])
        if record["effective_until"] < record["effective_from"]:
            raise InputError("Amendment effective date range is reversed.")
    if record["supersedes_id"] is not None:
        record["supersedes_id"] = identifier(record["supersedes_id"])
    return Amendment(**record)


def _receipt(value):
    record = _line_fields(value, "id version quantity status received_at")
    record["id"] = identifier(record["id"])
    record["version"] = integer(record["version"])
    record["quantity"] = integer(record["quantity"])
    record["status"] = choice(record["status"], {"accepted", "draft", "cancelled"})
    record["received_at"] = timestamp(record["received_at"])
    return Receipt(**record)


def parse_register(value):
    record = versioned(
        value,
        "version evidence_cutoff amendments_complete receipts_complete "
        "authorized_approvers po_lines amendments receipts",
    )
    record["version"] = integer(record["version"])
    record["evidence_cutoff"] = timestamp(record["evidence_cutoff"])
    for name in ("amendments_complete", "receipts_complete"):
        record[name] = flag(record[name])
    record["authorized_approvers"] = tuple(
        identifier(item) for item in collection(record["authorized_approvers"])
    )
    unique(record["authorized_approvers"])
    record["po_lines"] = tuple(_purchase_line(item) for item in collection(record["po_lines"]))
    unique([(line.key.po_id, line.key.line_id) for line in record["po_lines"]])
    record["amendments"] = tuple(_amendment(item) for item in collection(record["amendments"]))
    unique([item.id for item in record["amendments"]])
    record["receipts"] = tuple(_receipt(item) for item in collection(record["receipts"]))
    return Register(**record)
