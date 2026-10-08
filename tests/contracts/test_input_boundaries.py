import copy

import pytest

from invoice_investigator.invoices.comparison import compare
from invoice_investigator.invoices.inputs import InputError, parse_invoice, parse_register


@pytest.mark.parametrize(
    "change",
    [
        {"invoice_id": "../secret"},
        {"critical_fields_confirmed": "true"},
        {"issued_on": "2026-02-30"},
        {"issued_on": "20260915"},
        {"schema_version": True},
        {"schema_version": 2},
        {"lines": []},
    ],
)
def test_invoice_schema_boundaries(change, case_inputs):
    invoice, _ = case_inputs()
    invoice.update(change)
    with pytest.raises(InputError):
        parse_invoice(invoice, "a" * 64)


def test_multiple_purchase_orders_rejected(case_inputs):
    invoice, _ = case_inputs()
    extra = copy.deepcopy(invoice["lines"][0])
    extra.update(po_id="PO-OTHER", line_id="2")
    invoice["lines"].append(extra)
    with pytest.raises(InputError):
        parse_invoice(invoice, "a" * 64)


def test_record_collections_are_bounded(case_inputs):
    _, register = case_inputs()
    register["receipts"] *= 1001
    with pytest.raises(InputError):
        parse_register(register)


@pytest.mark.parametrize(
    "change",
    [
        {"evidence_cutoff": "2026-09-31T00:00:00Z"},
        {"amendments_complete": 1},
    ],
)
def test_register_schema_boundaries(change, case_inputs):
    _, register = case_inputs()
    register.update(change)
    with pytest.raises(InputError):
        parse_register(register)


def test_reversed_amendment_interval_rejected(case_inputs):
    _, register = case_inputs()
    register["amendments"][0]["effective_until"] = "2026-08-01"
    with pytest.raises(InputError):
        parse_register(register)


def test_invalid_source_digest_rejected(case_inputs):
    invoice, _ = case_inputs()
    with pytest.raises(InputError):
        parse_invoice(invoice, "not-a-digest")


def test_invoice_after_cutoff_rejected(case_inputs):
    invoice, register = case_inputs()
    invoice["issued_on"] = "2026-09-17"
    with pytest.raises(InputError):
        compare(parse_invoice(invoice, "a" * 64), parse_register(register))
