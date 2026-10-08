import copy
import hashlib
import json
from dataclasses import replace

import pytest


@pytest.fixture
def second_revision(sample_directory):
    from invoice_investigator.case_storage.samples import read_sample
    from invoice_investigator.cases.proposals import payload_digest

    sample = read_sample(sample_directory / "case-002")
    invoice, register, manifest = copy.deepcopy((sample.invoice, sample.register, sample.manifest))
    for document in (invoice, register, manifest):
        document["case_version"] = 2
    source = (json.dumps(register, indent=2) + "\n").encode()
    manifest["files"]["purchasing.json"] = hashlib.sha256(source).hexdigest()
    changed = replace(
        sample, invoice=invoice, register=register, manifest=manifest, register_source=source
    )
    return replace(
        changed,
        digest=payload_digest(
            {
                "invoice": invoice,
                "register": register,
                "manifest": manifest,
            }
        ),
    )
