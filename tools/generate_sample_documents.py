"""Regenerate original synthetic PDFs and integrity manifests, never expected answers."""

import hashlib
import json
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.pdfgen.canvas import Canvas

ROOT = Path(__file__).resolve().parents[1]
NAVY = HexColor("#163047")
TEAL = HexColor("#007F82")
MUTED = HexColor("#566675")


def text(canvas, x, y, value, size=11, bold=False, color=NAVY):
    canvas.setFillColor(color)
    canvas.setFont("Helvetica-Bold" if bold else "Helvetica", size)
    canvas.drawString(x, y, value)


def start(path, title, document_id):
    canvas = Canvas(str(path), pagesize=(612, 792), invariant=1, pageCompression=1)
    canvas.setTitle(f"Synthetic demo - {title} {document_id}")
    canvas.setAuthor("OCI Invoice Investigator synthetic fixtures")
    canvas.setFillColor(NAVY)
    canvas.rect(0, 678, 612, 114, fill=1, stroke=0)
    text(canvas, 42, 746, "NORTHSTAR COMPONENTS", 12, True, HexColor("#FFFFFF"))
    text(canvas, 42, 705, title, 27, True, HexColor("#FFFFFF"))
    text(canvas, 42, 650, "SYNTHETIC DEMO DOCUMENT", 10, True, TEAL)
    text(
        canvas,
        42,
        48,
        "Fictional organizations and records. No payment or bank details.",
        9,
        color=MUTED,
    )
    text(canvas, 42, 32, f"{document_id}  |  Version 1  |  Page 1 of 1", 9, color=MUTED)
    return canvas


def invoice_pdf(folder, invoice):
    canvas = start(folder / "invoice.pdf", "INVOICE", invoice["invoice_id"])
    text(canvas, 42, 612, "BILL TO", 9, True, MUTED)
    text(canvas, 42, 591, "Cedar Works Demonstration Company", 12, True)
    text(canvas, 42, 570, "Synthetic customer account CEDAR-001", 10)
    text(canvas, 368, 612, "INVOICE DETAILS", 9, True, MUTED)
    text(canvas, 368, 591, invoice["invoice_id"], 12, True)
    text(canvas, 368, 570, "Issued: " + invoice["issued_on"], 10)
    line = invoice["lines"][0]
    text(canvas, 42, 527, "Purchase order: " + line["po_id"], 11, True)
    text(canvas, 42, 506, "Supplier ID: " + line["supplier_id"], 10)
    canvas.setFillColor(HexColor("#EAF3F4"))
    canvas.rect(42, 449, 528, 29, fill=1, stroke=0)
    for x, label in [
        (50, "ITEM / PO LINE"),
        (291, "QTY"),
        (338, "UNIT"),
        (395, "PRICE"),
        (499, "AMOUNT"),
    ]:
        text(canvas, x, 460, label, 9, True)
    text(canvas, 50, 426, line["item_code"] + " / " + line["line_id"], 11, True)
    text(canvas, 50, 405, "10 Gb network interface card", 10)
    text(canvas, 291, 426, str(line["quantity"]), 11)
    text(canvas, 338, 426, line["unit"], 11)
    text(canvas, 395, 426, line["unit_price"], 11)
    text(canvas, 499, 426, line["line_total"], 11)
    canvas.setStrokeColor(HexColor("#CBD5DC"))
    canvas.line(42, 388, 570, 388)
    text(canvas, 365, 351, "TOTAL USD", 12, True)
    text(canvas, 488, 351, invoice["total"], 15, True, TEAL)
    text(canvas, 42, 285, "Document scope", 11, True)
    text(canvas, 42, 264, "One purchase order. Amounts are in USD. Quantities are each (EA).", 10)
    text(canvas, 42, 245, "No tax, freight, discounts or credits are included.", 10)
    text(canvas, 42, 207, "Case: " + invoice["case_id"], 10, color=MUTED)
    canvas.save()


def amendment_pdf(folder, amendment):
    canvas = start(folder / "amendment.pdf", "PRICE AMENDMENT", amendment["id"])
    text(canvas, 42, 606, "Purchasing agreement record", 16, True)
    rows = [
        ("Amendment", amendment["id"]),
        ("Purchase order / line", amendment["po_id"] + " / " + amendment["line_id"]),
        ("Supplier / item", amendment["supplier_id"] + " / " + amendment["item_code"]),
        ("Approved unit price", "USD " + amendment["unit_price"] + " per EA"),
        ("Effective from", amendment["effective_from"]),
        ("Effective until", amendment["effective_until"] or "Open ended"),
        ("Approval date", amendment["approved_on"]),
        ("Purchasing approver", amendment["approved_by"]),
        ("Register status", amendment["status"].upper()),
    ]
    for index, (label, value) in enumerate(rows):
        y = 557 - index * 31
        text(canvas, 42, y, label, 10, color=MUTED)
        text(canvas, 266, y, value, 11, True)
    text(canvas, 42, 218, "Scope", 11, True)
    text(
        canvas,
        42,
        196,
        "This record changes the unit price for the identified purchase-order line.",
        10,
    )
    text(canvas, 42, 177, "Ordered quantity and receiving records are unchanged.", 10)
    text(
        canvas,
        42,
        137,
        "Approval authority is verified against the synthetic purchasing register.",
        9,
        color=MUTED,
    )
    canvas.save()


def main():
    for name in ("case-001", "case-002"):
        folder = ROOT / "examples/invoices" / name
        invoice = json.loads(
            (ROOT / "tests/fixtures/invoices" / name / "normalized_invoice.json").read_text()
        )
        register = json.loads((folder / "purchasing.json").read_text())
        invoice_pdf(folder, invoice)
        files = ["invoice.pdf", "purchasing.json"]
        if register["amendments"]:
            amendment_pdf(folder, register["amendments"][0])
            files.append("amendment.pdf")
        manifest = {
            "schema_version": 1,
            "case_id": name,
            "case_version": 1,
            "files": {
                file: hashlib.sha256((folder / file).read_bytes()).hexdigest() for file in files
            },
        }
        (folder / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
