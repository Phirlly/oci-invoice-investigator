import copy

import pytest


def test_invoice_at_old_price_does_not_hide_applicable_amendment(case_inputs, investigate):
    invoice, register = case_inputs()
    invoice["lines"][0].update(unit_price="10.00", line_total="1000.00")
    invoice["total"] = "1000.00"
    result = investigate(invoice, register)
    assert result["lines"][0]["expected_unit_price"] == "12.00"
    assert "price_mismatch" in [f["code"] for f in result["findings"]]


@pytest.mark.parametrize(
    "change",
    [
        {"status": "draft"},
        {"approved_by": "unauthorized"},
        {"approved_on": "2026-09-16"},
        {"effective_from": "2026-09-16"},
        {"effective_until": "2026-09-14"},
        {"item_code": "OTHER"},
    ],
)
def test_inapplicable_amendment_cannot_authorize_price(change, case_inputs, investigate):
    invoice, register = case_inputs()
    register["amendments"][0].update(change)
    result = investigate(invoice, register)
    assert result["lines"][0]["expected_unit_price"] == "10.00"


def test_effective_dates_and_approval_date_are_inclusive(case_inputs, investigate):
    invoice, register = case_inputs()
    register["amendments"][0].update(
        approved_on=invoice["issued_on"],
        effective_from=invoice["issued_on"],
        effective_until=invoice["issued_on"],
    )
    assert investigate(invoice, register)["lines"][0]["expected_unit_price"] == "12.00"


def test_conflicting_approved_prices_cannot_fall_back_to_po(case_inputs, investigate):
    invoice, register = case_inputs()
    amendment = copy.deepcopy(register["amendments"][0])
    amendment.update(id="AMD-002", unit_price="13.00")
    register["amendments"].append(amendment)
    result = investigate(invoice, register)
    assert result["lines"][0]["expected_unit_price"] is None
    assert "price_conflict" in [f["code"] for f in result["findings"]]


def test_incomplete_register_cannot_use_base_price(case_inputs, investigate):
    invoice, register = case_inputs("case-001")
    register["amendments_complete"] = False
    result = investigate(invoice, register)
    assert result["conclusion"] == "incomplete"
    assert result["lines"][0]["expected_unit_price"] is None
