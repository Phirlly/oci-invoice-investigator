import json
from pathlib import Path

import pytest


@pytest.mark.parametrize("case", ["case-001", "case-002"])
def test_sample_matches_independent_oracle(case, case_inputs, investigate):
    invoice, register = case_inputs(case)
    result = investigate(invoice, register)
    fixture = Path(__file__).resolve().parents[2] / "fixtures/invoices" / case
    oracle = json.loads((fixture / "expected_findings.json").read_text())
    assert result["conclusion"] == oracle["conclusion"]
    assert result["lines"][0]["expected_unit_price"] == oracle["expected_unit_price"]
    assert result["lines"][0]["received_quantity"] == oracle["received_quantity"]
    assert result["lines"][0]["missing_receipt_quantity"] == oracle["missing_receipt_quantity"]
    assert [finding["code"] for finding in result["findings"]] == oracle["finding_codes"]
    assert result["snapshot"]["document_sha256"] == "a" * 64
    assert result["mode"] == "offline_normalized_comparison"
    assert result["lines"][0]["price_evidence"]
    assert result["lines"][0]["receipt_evidence"]
