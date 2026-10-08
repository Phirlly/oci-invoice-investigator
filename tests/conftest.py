"""Fresh synthetic invoice inputs shared by the three offline test lanes."""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def case_inputs():
    def load(case="case-002"):
        fixture = ROOT / "tests/fixtures/invoices" / case
        evidence = ROOT / "examples/invoices" / case
        return (
            json.loads((fixture / "normalized_invoice.json").read_text()),
            json.loads((evidence / "purchasing.json").read_text()),
        )

    return load
