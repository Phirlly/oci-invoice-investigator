"""Pure comparison: no clients, model calls, persistence or business actions."""

from decimal import Context, Decimal, localcontext

from .input_fields import InputError
from .pricing import resolve_price
from .receiving import receipt_coverage
from .results import Evidence, Finding, LineResult, Result, Snapshot, register_evidence

ISSUES = {
    "amendments_incomplete": (
        "Price authority retrieval is incomplete.",
        "Retrieve the complete amendment register.",
    ),
    "receipts_incomplete": (
        "Receiving evidence retrieval is incomplete.",
        "Retrieve the complete receipt register.",
    ),
    "price_conflict": (
        "Applicable amendment authority conflicts.",
        "Request purchasing review of amendment authority.",
    ),
    "receipt_conflict": (
        "Receipt identities have contradictory representations.",
        "Request receiving review of conflicting records.",
    ),
}


def compare(invoice, register):
    if (invoice.case_id, invoice.case_version) != (register.case_id, register.case_version):
        raise InputError("Invoice and purchasing register belong to different case snapshots.")
    if invoice.issued_on > register.evidence_cutoff.date():
        raise InputError("Invoice date is after the frozen evidence cutoff.")
    snapshot = Snapshot(
        invoice.case_id,
        invoice.case_version,
        invoice.document_sha256,
        register.version,
        register.evidence_cutoff.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    invoice_ref = Evidence("normalized_invoice.json", invoice.case_version, "")
    if not invoice.critical_fields_confirmed:
        return Result(
            snapshot,
            "incomplete",
            (),
            (
                Finding(
                    "unconfirmed_fields",
                    None,
                    "Critical normalized fields are unconfirmed.",
                    (invoice_ref,),
                    "Confirm critical fields against the source invoice.",
                ),
            ),
        )
    # Caller Decimal context cannot change exact arithmetic for the bounded schema.
    with localcontext(Context(prec=28, Emin=-999999, Emax=999999)):
        return _compare_confirmed(invoice, register, snapshot, invoice_ref)


def _compare_confirmed(invoice, register, snapshot, invoice_ref):
    findings = []
    lines = []
    if invoice.total != sum((line.line_total for line in invoice.lines), Decimal("0.00")):
        findings.append(
            Finding(
                "invoice_total_mismatch",
                None,
                "Invoice total differs from the sum of declared line totals.",
                (invoice_ref,),
                "Review invoice totals.",
            )
        )
    purchases = {line.key: line for line in register.po_lines}
    for index, line in enumerate(invoice.lines):
        observed = Evidence("normalized_invoice.json", invoice.case_version, f"/lines/{index}")

        def add(code, detail, evidence, next_step, line_id=line.key.line_id):
            findings.append(Finding(code, line_id, detail, evidence, next_step))

        if line.line_total != line.quantity * line.unit_price:
            add(
                "line_total_mismatch",
                "Line total differs from quantity times unit price.",
                (observed,),
                "Review invoice line arithmetic.",
            )
        purchase = purchases.get(line.key)
        if purchase is None:
            add(
                "purchase_line_missing",
                "No exact purchase-order line is available.",
                (observed, register_evidence(register, "/po_lines")),
                "Obtain the matching PO line.",
            )
            lines.append(LineResult(line.key.line_id, None, None, None, (), ()))
            continue
        if line.quantity > purchase.quantity:
            add(
                "ordered_quantity_exceeded",
                "Invoiced quantity exceeds ordered quantity.",
                (
                    observed,
                    register_evidence(register, f"/po_lines/{register.po_lines.index(purchase)}"),
                ),
                "Request purchasing review of ordered quantity.",
            )
        price = resolve_price(line, purchase, invoice.issued_on, register)
        receipts = receipt_coverage(line, register)
        for decision in (price, receipts):
            if decision.issue:
                detail, next_step = ISSUES[decision.issue]
                add(decision.issue, detail, decision.evidence, next_step)
        if price.value is not None and price.value != line.unit_price:
            add(
                "price_mismatch",
                f"Invoice unit price {line.unit_price:.2f} differs from "
                f"authoritative price {price.value:.2f}.",
                (observed, *price.evidence),
                "Request purchasing review of invoice price.",
            )
        missing = None if receipts.value is None else max(line.quantity - receipts.value, 0)
        if missing:
            add(
                "receipt_shortfall",
                f"{missing} units lack receiving evidence; "
                "physical nondelivery is not established.",
                (observed, *receipts.evidence),
                "Request receiving evidence for the unsupported units.",
            )
        lines.append(
            LineResult(
                line.key.line_id,
                None if price.value is None else f"{price.value:.2f}",
                receipts.value,
                missing,
                price.evidence,
                receipts.evidence,
            )
        )
    incomplete = {"purchase_line_missing", "amendments_incomplete", "receipts_incomplete"}
    conclusion = (
        "incomplete"
        if any(item.code in incomplete for item in findings)
        else "needs_review"
        if findings
        else "no_discrepancy"
    )
    return Result(snapshot, conclusion, tuple(lines), tuple(findings))
