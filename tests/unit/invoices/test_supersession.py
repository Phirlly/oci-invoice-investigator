import copy

import pytest


def test_applicable_successor_replaces_predecessor(case_inputs, investigate):
    invoice, register = case_inputs()
    successor = copy.deepcopy(register["amendments"][0])
    successor.update(id="AMD-002", unit_price="14.00", supersedes_id="AMD-001")
    register["amendments"].append(successor)
    assert investigate(invoice, register)["lines"][0]["expected_unit_price"] == "14.00"


@pytest.mark.parametrize("change", [{"status": "draft"}, {"effective_from": "2026-09-16"}])
def test_inapplicable_successor_cannot_remove_current_price(change, case_inputs, investigate):
    invoice, register = case_inputs()
    successor = copy.deepcopy(register["amendments"][0])
    successor.update(id="AMD-002", supersedes_id="AMD-001", **change)
    register["amendments"].append(successor)
    assert investigate(invoice, register)["lines"][0]["expected_unit_price"] == "12.00"


@pytest.mark.parametrize("failure", ["broken", "cycle", "cross_identity"])
def test_invalid_relevant_supersession_is_conflict(failure, case_inputs, investigate):
    invoice, register = case_inputs()
    current = register["amendments"][0]
    current["supersedes_id"] = "AMD-002"
    if failure != "broken":
        predecessor = copy.deepcopy(current)
        predecessor.update(id="AMD-002", supersedes_id="AMD-001" if failure == "cycle" else None)
        if failure == "cross_identity":
            predecessor["item_code"] = "OTHER"
        register["amendments"].append(predecessor)
    result = investigate(invoice, register)
    assert result["lines"][0]["expected_unit_price"] is None
    assert "price_conflict" in [f["code"] for f in result["findings"]]
