import json
from pathlib import Path

from invoice_investigator.cli import main

ROOT = Path(__file__).resolve().parents[2]


def test_callable_cli_returns_json_business_result(capsys):
    assert (
        main(
            [
                "--invoice",
                str(ROOT / "tests/fixtures/invoices/case-001/normalized_invoice.json"),
                "--evidence",
                str(ROOT / "examples/invoices/case-001"),
            ]
        )
        == 0
    )
    output = capsys.readouterr()
    assert json.loads(output.out)["conclusion"] == "no_discrepancy"
    assert output.err == ""


def test_callable_cli_reports_input_error_separately(capsys):
    assert main(["--invoice", "missing.json", "--evidence", "missing-directory"]) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == "Input error: An input file could not be read.\n"
