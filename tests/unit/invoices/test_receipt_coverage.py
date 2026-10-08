import copy

import pytest


def test_incomplete_retrieval_never_claims_final_shortfall(case_inputs, investigate):
    invoice, register = case_inputs()
    register["receipts_complete"] = False
    result = investigate(invoice, register)
    assert result["conclusion"] == "incomplete"
    assert result["lines"][0]["missing_receipt_quantity"] is None
    assert "receipt_shortfall" not in [f["code"] for f in result["findings"]]


def test_complete_empty_receipts_support_zero_units(case_inputs, investigate):
    invoice, register = case_inputs()
    register["receipts"] = []
    line = investigate(invoice, register)["lines"][0]
    assert (line["received_quantity"], line["missing_receipt_quantity"]) == (0, 100)


def test_identical_receipts_are_counted_once(case_inputs, investigate):
    invoice, register = case_inputs()
    register["receipts"].append(copy.deepcopy(register["receipts"][0]))
    assert investigate(invoice, register)["lines"][0]["received_quantity"] == 80


@pytest.mark.parametrize("change", [{"quantity": 20}, {"status": "cancelled"}, {"version": 2}])
def test_contradictory_same_id_receipts_conflict(change, case_inputs, investigate):
    invoice, register = case_inputs()
    conflicting = copy.deepcopy(register["receipts"][0])
    conflicting.update(change)
    register["receipts"].append(conflicting)
    result = investigate(invoice, register)
    assert result["lines"][0]["received_quantity"] is None
    assert "receipt_conflict" in [f["code"] for f in result["findings"]]


@pytest.mark.parametrize(
    "change",
    [{"status": "draft"}, {"status": "cancelled"}, {"received_at": "2026-09-16T00:00:01Z"}],
)
def test_unaccepted_or_future_receipts_do_not_count(change, case_inputs, investigate):
    invoice, register = case_inputs()
    register["receipts"][0].update(change)
    assert investigate(invoice, register)["lines"][0]["received_quantity"] == 0


def test_receipt_exactly_at_cutoff_counts(case_inputs, investigate):
    invoice, register = case_inputs()
    register["receipts"][0]["received_at"] = register["evidence_cutoff"]
    assert investigate(invoice, register)["lines"][0]["received_quantity"] == 80


def test_future_version_cannot_change_frozen_receiving_snapshot(case_inputs, investigate):
    invoice, register = case_inputs()
    future = copy.deepcopy(register["receipts"][0])
    future.update(version=2, quantity=100, received_at="2026-09-17T00:00:00Z")
    register["receipts"].append(future)
    assert investigate(invoice, register)["lines"][0]["received_quantity"] == 80


def test_other_line_receipts_do_not_supply_coverage(case_inputs, investigate):
    invoice, register = case_inputs()
    register["receipts"][0]["line_id"] = "2"
    assert investigate(invoice, register)["lines"][0]["received_quantity"] == 0
