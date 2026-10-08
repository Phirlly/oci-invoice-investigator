import copy

import pytest

from invoice_investigator.invoices.inputs import InputError, parse_invoice, parse_register


@pytest.mark.parametrize("price", [10.0, "NaN", "10.001", "-1.00", "1000000000.00"])
def test_reject_invalid_money(price, case_inputs):
    invoice, _ = case_inputs()
    invoice["lines"][0]["unit_price"] = price
    with pytest.raises(InputError):
        parse_invoice(invoice, "a" * 64)


@pytest.mark.parametrize("quantity", [True, 0, -1, 1.5, 1000001])
def test_reject_invalid_quantities(quantity, case_inputs):
    invoice, _ = case_inputs()
    invoice["lines"][0]["quantity"] = quantity
    with pytest.raises(InputError):
        parse_invoice(invoice, "a" * 64)


@pytest.mark.parametrize("change", [{"currency": "EUR"}, {"unit": "KG"}, {"tax": "1.00"}])
def test_reject_unsupported_fields(change, case_inputs):
    invoice, _ = case_inputs()
    invoice["lines"][0].update(change)
    with pytest.raises(InputError):
        parse_invoice(invoice, "a" * 64)


def test_duplicate_invoice_line_ids_rejected(case_inputs):
    invoice, _ = case_inputs()
    invoice["lines"].append(copy.deepcopy(invoice["lines"][0]))
    with pytest.raises(InputError):
        parse_invoice(invoice, "a" * 64)


@pytest.mark.parametrize(
    "timestamp", ["2026-09-16T00:00:00", "yesterday", "2026-09-16T00:00:00+01:00"]
)
def test_reject_ambiguous_or_non_utc_cutoff(timestamp, case_inputs):
    _, register = case_inputs()
    register["evidence_cutoff"] = timestamp
    with pytest.raises(InputError):
        parse_register(register)


def test_case_scope_must_match(case_inputs):
    from invoice_investigator.invoices.comparison import compare

    invoice, register = case_inputs()
    register["case_id"] = "another-case"
    with pytest.raises(InputError):
        compare(parse_invoice(invoice, "a" * 64), parse_register(register))
