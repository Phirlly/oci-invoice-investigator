"""Check the exact vendored files and their digests before packaging."""

import hashlib
import json
import re
from pathlib import Path


def font_source_resources(root):
    directory = root / "src/invoice_investigator/web/third_party_sources"
    source = directory / "liberation-fonts-1.07.4.tar.gz"
    digest = "ad98b7498dc2992f7f0868f79b65ce4a720a3acdb63ab3f1f1cb6881117a5406"
    if hashlib.sha256(source.read_bytes()).hexdigest() != digest:
        raise ValueError("Corresponding font source digest mismatch.")
    return {source, directory / "README.md"}


def verify_packaged_resources(read_member, resources, relative_to, prefix=""):
    for path in resources:
        member = prefix + str(path.relative_to(relative_to))
        assert read_member(member) == path.read_bytes(), f"Packaged resource differs: {member}"


def web_resources(root):
    web = root / "src/invoice_investigator/web"
    vendor = web / "static/review/vendor"
    manifest_path = vendor / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    expected = manifest["files"]
    actual = {str(path.relative_to(vendor)) for path in vendor.rglob("*") if path.is_file()}
    assert actual == set(expected) | {"manifest.json"}, "Unexpected/missing vendor files."
    for name, digest in expected.items():
        path = Path(name)
        assert not path.is_absolute() and ".." not in path.parts
        allowed = name in {
            "bootstrap/LICENSE",
            "bootstrap/bootstrap.min.css",
            "pdfjs/LICENSE",
            "pdfjs/pdf.mjs",
            "pdfjs/pdf.worker.mjs",
        } or (
            len(path.parts) == 3
            and path.parts[:2]
            in {
                ("pdfjs", "cmaps"),
                ("pdfjs", "standard_fonts"),
                ("pdfjs", "wasm"),
                ("pdfjs", "iccs"),
            }
            and (
                path.name.startswith("LICENSE")
                or path.suffix in {".bcmap", ".pfb", ".ttf", ".icc", ".wasm", ".js"}
            )
        )
        assert allowed, f"Unexpected vendor member: {name}"
        assert re.fullmatch("[0-9a-f]{64}", digest)
        assert hashlib.sha256((vendor / name).read_bytes()).hexdigest() == digest
    return (
        {manifest_path}
        | {vendor / name for name in expected}
        | set((web / "templates/review").glob("*.html"))
        | {web / "static/review/workbench.css", web / "static/review/pdf-view.mjs"}
        | font_source_resources(root)
    )
