import pytest

from invoice_investigator.invoices.comparison import compare
from invoice_investigator.invoices.inputs import parse_invoice, parse_register


@pytest.fixture
def investigate():
    def run(invoice, register):
        return compare(parse_invoice(invoice, "a" * 64), parse_register(register)).to_dict()

    return run
