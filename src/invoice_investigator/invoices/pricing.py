"""Resolve price authority independently of the invoice's price."""

from .results import Decision, register_evidence


def _applicable(amendment, key, invoice_date, approvers):
    return (
        amendment.key == key
        and amendment.status == "approved"
        and amendment.approved_by in approvers
        and amendment.approved_on <= invoice_date
        and amendment.effective_from <= invoice_date
        and (amendment.effective_until is None or invoice_date <= amendment.effective_until)
    )


def _valid_chain(start, records):
    visited = {start.id}
    cursor = start
    while cursor.supersedes_id is not None:
        predecessor = records.get(cursor.supersedes_id)
        if predecessor is None or predecessor.key != start.key or predecessor.id in visited:
            return False
        visited.add(predecessor.id)
        cursor = predecessor
    return True


def resolve_price(line, purchase, invoice_date, register):
    register_ref = register_evidence(register, "/amendments")
    if not register.amendments_complete:
        return Decision(None, (register_ref,), "amendments_incomplete")
    records = {item.id: item for item in register.amendments}
    applicable = {
        item.id: item
        for item in register.amendments
        if _applicable(item, line.key, invoice_date, register.authorized_approvers)
    }
    references = tuple(
        register_evidence(register, f"/amendments/{register.amendments.index(item)}")
        for item in applicable.values()
    )
    if any(not _valid_chain(item, records) for item in applicable.values()):
        return Decision(None, references, "price_conflict")
    # Only an applicable successor can supersede another applicable record.
    replaced = set()
    for item in applicable.values():
        cursor = item
        while cursor.supersedes_id is not None:
            replaced.add(cursor.supersedes_id)
            cursor = records[cursor.supersedes_id]
    remaining = [item for item in applicable.values() if item.id not in replaced]
    if len(remaining) > 1:
        return Decision(None, references, "price_conflict")
    if remaining:
        item = remaining[0]
        return Decision(
            item.unit_price,
            (register_evidence(register, f"/amendments/{register.amendments.index(item)}"),),
        )
    return Decision(
        purchase.unit_price,
        (
            register_evidence(register, f"/po_lines/{register.po_lines.index(purchase)}"),
            register_ref,
        ),
    )
