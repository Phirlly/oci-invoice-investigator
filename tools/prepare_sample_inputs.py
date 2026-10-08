"""Copy reviewed synthetic normalized inputs to independently shipped runtime samples."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    for case in ("case-001", "case-002"):
        content = (ROOT / "tests/fixtures/invoices" / case / "normalized_invoice.json").read_bytes()
        target = ROOT / "examples/invoices" / case
        (target / "normalized_invoice.json").write_bytes(content)
        (target / "sample-input.json").write_text(
            json.dumps(
                {
                    "kind": "hand_normalized_synthetic",
                    "normalized_sha256": hashlib.sha256(content).hexdigest(),
                },
                indent=2,
            )
            + "\n"
        )


if __name__ == "__main__":
    main()
