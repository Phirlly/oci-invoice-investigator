"""Receipt coverage within one immutable, isolated invoice case."""

from .results import Decision, register_evidence


def receipt_coverage(line, register):
    collection_ref = register_evidence(register, "/receipts")
    if not register.receipts_complete:
        return Decision(None, (collection_ref,), "receipts_incomplete")
    # Check contradictions across all representations of each relevant identity,
    # including status/key changes; filtering accepted rows first would hide them.
    snapshot = [item for item in register.receipts if item.received_at <= register.evidence_cutoff]
    relevant_ids = {item.id for item in snapshot if item.key == line.key}
    records = {}
    for item in snapshot:
        if item.id not in relevant_ids:
            continue
        if item.id in records and records[item.id] != item:
            return Decision(None, (collection_ref,), "receipt_conflict")
        records[item.id] = item
    accepted = [
        item
        for item in records.values()
        if item.key == line.key
        and item.status == "accepted"
        and item.received_at <= register.evidence_cutoff
    ]
    references = tuple(
        register_evidence(register, f"/receipts/{register.receipts.index(item)}")
        for item in accepted
    )
    return Decision(sum(item.quantity for item in accepted), references or (collection_ref,))
