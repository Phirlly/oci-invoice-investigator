import pytest


def test_exact_decimal_cents(case_inputs, investigate):
    invoice, register = case_inputs("case-001")
    invoice["lines"][0].update(quantity=3, unit_price="0.10", line_total="0.30")
    invoice["total"] = "0.30"
    register["po_lines"][0].update(quantity=3, unit_price="0.10")
    register["receipts"][0]["quantity"] = 3
    assert investigate(invoice, register)["conclusion"] == "no_discrepancy"


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("line_total", "999.00", "line_total_mismatch"),
        ("quantity", 101, "ordered_quantity_exceeded"),
    ],
)
def test_amount_and_order_discrepancies(field, value, code, case_inputs, investigate):
    invoice, register = case_inputs("case-001")
    invoice["lines"][0][field] = value
    assert code in [f["code"] for f in investigate(invoice, register)["findings"]]


def test_invoice_total_must_equal_declared_line_totals(case_inputs, investigate):
    invoice, register = case_inputs("case-001")
    invoice["total"] = "999.00"
    assert "invoice_total_mismatch" in [
        f["code"] for f in investigate(invoice, register)["findings"]
    ]


def test_missing_po_and_uncertain_fields_block_conclusion(case_inputs, investigate):
    invoice, register = case_inputs()
    register["po_lines"] = []
    assert investigate(invoice, register)["conclusion"] == "incomplete"
    invoice["critical_fields_confirmed"] = False
    result = investigate(invoice, register)
    assert result["conclusion"] == "incomplete"
    assert result["lines"] == ()
