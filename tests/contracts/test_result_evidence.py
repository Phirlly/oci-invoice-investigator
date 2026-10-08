import copy
from decimal import Inexact, localcontext

import pytest

from invoice_investigator.invoices.comparison import compare
from invoice_investigator.invoices.inputs import parse_invoice, parse_register


@pytest.mark.parametrize("with_amendment", [False, True])
def test_evidence_locations_resolve_to_exact_source_records(with_amendment, case_inputs):
    invoice, register = case_inputs()
    extra = copy.deepcopy(register["po_lines"][0])
    extra.update(po_id="OTHER-PO", unit_price="99.00")
    register["po_lines"].append(extra)
    if not with_amendment:
        register["amendments"] = []
    invoice["total"] = "999.00"
    result = compare(parse_invoice(invoice, "a" * 64), parse_register(register)).to_dict()
    sources = {"normalized_invoice.json": invoice, "purchasing.json": register}
    line = result["lines"][0]
    references = [
        *line["price_evidence"],
        *line["receipt_evidence"],
        *(ref for finding in result["findings"] for ref in finding["evidence"]),
    ]
    for reference in references:
        selected = sources[reference["source"]]
        for part in reference["locator"].split("/")[1:]:
            selected = selected[int(part)] if isinstance(selected, list) else selected[part]
        assert selected is not None
    price_reference = line["price_evidence"][0]
    assert price_reference["locator"] == ("/amendments/0" if with_amendment else "/po_lines/0")


def test_arithmetic_is_independent_of_callers_decimal_context(case_inputs):
    invoice, register = case_inputs("case-001")
    normalized, evidence = parse_invoice(invoice, "a" * 64), parse_register(register)
    with localcontext() as context:
        context.prec = 2
        context.Emax = 2
        context.Emin = -2
        context.traps[Inexact] = True
        assert compare(normalized, evidence).conclusion == "no_discrepancy"
        assert (context.prec, context.Emax, context.Emin, context.traps[Inexact]) == (
            2,
            2,
            -2,
            True,
        )
