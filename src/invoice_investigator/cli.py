"""Offline normalized comparison; source extraction and agent execution are separate."""

import argparse
import json
import sys
from pathlib import Path

from .invoices.bundle import load_case
from .invoices.comparison import compare
from .invoices.inputs import InputError


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Compare trusted normalized synthetic invoice fields with local evidence."
    )
    parser.add_argument("--invoice", type=Path, required=True, help="Normalized invoice JSON.")
    parser.add_argument("--evidence", type=Path, required=True, help="Case evidence directory.")
    args = parser.parse_args(argv)
    try:
        invoice, register = load_case(args.invoice, args.evidence)
        result = compare(invoice, register)
    except InputError as error:
        print(f"Input error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
