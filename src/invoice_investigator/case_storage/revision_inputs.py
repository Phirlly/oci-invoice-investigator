import hashlib

from invoice_investigator.invoices.bundle import JSON_LIMIT, PDF_LIMIT, _json
from invoice_investigator.invoices.input_fields import InputError, versioned


def validate_sources(sample):
    manifest = versioned(sample.manifest, "files")
    sources = manifest["files"]
    if not isinstance(sources, dict) or set(sources) not in (
        {"invoice.pdf", "purchasing.json"},
        {"invoice.pdf", "purchasing.json", "amendment.pdf"},
    ):
        raise InputError("Unsupported source document set.")
    if set(sample.documents) != set(sources) - {"purchasing.json"}:
        raise InputError("Required evidence document set is incomplete.")
    if (
        len(sample.register_source) > JSON_LIMIT
        or hashlib.sha256(sample.register_source).hexdigest() != sources["purchasing.json"]
        or _json(sample.register_source) != sample.register
    ):
        raise InputError("Purchasing register does not match its source.")
    for name, content in sample.documents.items():
        if len(content) > PDF_LIMIT or hashlib.sha256(content).hexdigest() != sources[name]:
            raise InputError("Evidence document digest or size is invalid.")
