"""Proposals request missing records; they never approve an invoice or payment."""

import hashlib
import json
from dataclasses import asdict

from invoice_investigator.invoices.comparison import compare


def payload_digest(payload):
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def receiving_proposals(invoice, register):
    result = compare(invoice, register)
    if result.conclusion == "incomplete":
        return ()
    proposals = []
    for line in result.lines:
        missing = line.missing_receipt_quantity
        if not missing:
            continue
        finding = next(
            item
            for item in result.findings
            if item.code == "receipt_shortfall" and item.line_id == line.line_id
        )
        proposals.append(
            {
                "schema_version": 1,
                "case_id": invoice.case_id,
                "case_version": invoice.case_version,
                "document_sha256": invoice.document_sha256,
                "purchasing_version": register.version,
                "line_id": line.line_id,
                "destination_role": "receiving",
                "missing_evidence_quantity": missing,
                "title": f"Request receiving evidence for line {line.line_id}",
                "body": (
                    f"Provide receiving evidence for {missing} EA on invoice "
                    f"{invoice.invoice_id}, line {line.line_id}. "
                    "These units lack receiving evidence; physical nondelivery is not established."
                ),
                "evidence": [asdict(item) for item in finding.evidence],
            }
        )
    return tuple(proposals)
