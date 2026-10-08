import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run_cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "invoice_investigator.cli", *map(str, args)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )


def test_cli_reports_receiving_gap_without_executing_actions():
    result = run_cli(
        "--invoice",
        ROOT / "tests/fixtures/invoices/case-002/normalized_invoice.json",
        "--evidence",
        ROOT / "examples/invoices/case-002",
    )
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["mode"] == "offline_normalized_comparison"
    assert output["conclusion"] == "needs_review"
    assert output["lines"][0]["missing_receipt_quantity"] == 20
    assert "task_id" not in output


def test_cli_rejects_missing_input_without_traceback():
    result = run_cli("--invoice", "missing.json", "--evidence", "examples/invoices/case-001")
    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr.startswith("Input error:")
    assert "Traceback" not in result.stderr
