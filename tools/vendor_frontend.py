"""Vendor a bounded subset of digest-verified official release archives."""

import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "src/invoice_investigator/web/static/review/vendor"
ARCHIVES = {
    "bootstrap-5.3.8-dist.zip": "3258c873cbcb1e2d81f4374afea2ea6437d9eee9077041073fd81dd579c5ba6b",
    "pdfjs-6.4.299-dist.zip": "f2245eb7ef3f674c872fe568a177bfec15874f5c034613e55d8e307f93ebd86d",
}


def selected(name, package):
    if package == "bootstrap":
        if name == "bootstrap-5.3.8-dist/css/bootstrap.min.css":
            return "bootstrap/bootstrap.min.css"
        return None
    if name in {"LICENSE", "build/pdf.mjs", "build/pdf.worker.mjs"}:
        return "pdfjs/" + name.removeprefix("build/")
    folders = ("web/cmaps/", "web/standard_fonts/", "web/iccs/", "web/wasm/")
    if name.startswith(folders) and not name.endswith("/") and "quickjs" not in name:
        return "pdfjs/" + name.removeprefix("web/")
    return None


def main():
    files = {"bootstrap/LICENSE": (TARGET / "bootstrap/LICENSE").read_bytes()}
    for archive, digest in ARCHIVES.items():
        source = ROOT / ".cache" / archive
        if hashlib.sha256(source.read_bytes()).hexdigest() != digest:
            raise ValueError("Upstream archive digest mismatch.")
        package = archive.split("-")[0]
        with zipfile.ZipFile(source) as zipped:
            for name in zipped.namelist():
                destination = selected(name, package)
                if destination:
                    if ".." in Path(destination).parts:
                        raise ValueError("Unsafe archive member.")
                    files[destination] = zipped.read(name)
    for name, content in files.items():
        target = TARGET / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    manifest = {
        "archives": ARCHIVES,
        "bootstrap_license_source": "https://github.com/twbs/bootstrap/blob/v5.3.8/LICENSE",
        "files": {
            name: hashlib.sha256(content).hexdigest() for name, content in sorted(files.items())
        },
    }
    (TARGET / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Vendored {len(files)} verified files with upstream notices.")


if __name__ == "__main__":
    main()
