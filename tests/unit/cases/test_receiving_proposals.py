import copy

import pytest

from invoice_investigator.cases.proposals import payload_digest, receiving_proposals
from invoice_investigator.invoices.inputs import parse_invoice, parse_register


def proposals(inputs):
    invoice, register = inputs
    return receiving_proposals(parse_invoice(invoice, "a" * 64), parse_register(register))


def test_matched_invoice_has_no_receiving_task(case_inputs):
    assert proposals(case_inputs("case-001")) == ()


def test_request_states_evidence_gap_without_claiming_nondelivery(case_inputs):
    (proposal,) = proposals(case_inputs())
    assert proposal["destination_role"] == "receiving"
    assert proposal["missing_evidence_quantity"] == 20
    assert proposal["case_id"] == "case-002"
    assert proposal["case_version"] == 1
    assert "physical nondelivery is not established" in proposal["body"]
    assert proposal["document_sha256"] == "a" * 64
    assert {ref["source"] for ref in proposal["evidence"]} == {
        "normalized_invoice.json",
        "purchasing.json",
    }


@pytest.mark.parametrize("field", ["receipts_complete", "amendments_complete"])
def test_incomplete_evidence_does_not_propose_task(case_inputs, field):
    invoice, register = case_inputs()
    register[field] = False
    assert proposals((invoice, register)) == ()


def test_digest_binds_exact_payload_but_not_object_key_order(case_inputs):
    (proposal,) = proposals(case_inputs())
    assert payload_digest(proposal) == payload_digest(dict(reversed(list(proposal.items()))))
    changed = copy.deepcopy(proposal)
    changed["missing_evidence_quantity"] = 19
    assert payload_digest(changed) != payload_digest(proposal)
