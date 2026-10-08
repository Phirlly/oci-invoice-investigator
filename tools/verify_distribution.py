"""Inspect built wheel/source allowlists and report locked installed dependency licenses."""

import tarfile
import tomllib
import zipfile
from email.parser import BytesParser
from importlib.metadata import distributions
from pathlib import Path

from verify_frontend_assets import verify_packaged_resources, web_resources

ROOT = Path(__file__).resolve().parents[1]
PROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
STEM = PROJECT["name"].replace("-", "_") + "-" + PROJECT["version"]


def distribution_contents():
    wheel = ROOT / "dist" / f"{STEM}-py3-none-any.whl"
    source = ROOT / "dist" / f"{STEM}.tar.gz"
    resources = web_resources(ROOT)
    notices = {ROOT / name for name in PROJECT["license-files"]}
    with zipfile.ZipFile(wheel) as archive:
        names = {item.filename for item in archive.infolist() if not item.is_dir()}
        verify_packaged_resources(archive.read, resources, ROOT / "src")
        verify_packaged_resources(archive.read, notices, ROOT, STEM + ".dist-info/licenses/")
        package_metadata = BytesParser().parsebytes(archive.read(STEM + ".dist-info/METADATA"))
        assert set(package_metadata.get_all("License-File", [])) == set(PROJECT["license-files"])
    code = {
        str(path.relative_to(ROOT / "src"))
        for path in set((ROOT / "src").rglob("*.py")) | resources
    }
    metadata = {
        STEM + ".dist-info/" + name for name in ("METADATA", "WHEEL", "RECORD", "entry_points.txt")
    } | {STEM + ".dist-info/licenses/" + str(path.relative_to(ROOT)) for path in notices}
    assert names == code | metadata, f"Unexpected wheel contents: {names ^ (code | metadata)}"
    allowed = (
        {"PKG-INFO", "pyproject.toml", "pyproject.toml.orig", "README.md", "uv.lock"}
        | {
            str(path.relative_to(ROOT))
            for folder in ("src", "tests", "examples", "tools")
            for path in (ROOT / folder).rglob("*")
            if path.is_file() and path.suffix in {".py", ".json", ".pdf"}
        }
        | {str(path.relative_to(ROOT)) for path in resources}
        | {str(path.relative_to(ROOT)) for path in notices}
    )
    with tarfile.open(source) as archive:
        verify_packaged_resources(
            lambda member: archive.extractfile(member).read(), resources, ROOT, STEM + "/"
        )
        verify_packaged_resources(
            lambda member: archive.extractfile(member).read(), notices, ROOT, STEM + "/"
        )
        source_names = {
            "/".join(Path(item.name).parts[1:]) for item in archive.getmembers() if item.isfile()
        }
        if "pyproject.toml.orig" in source_names:
            original = archive.extractfile(f"{STEM}/pyproject.toml.orig")
            assert original.read() == (ROOT / "pyproject.toml").read_bytes()
    assert source_names <= allowed, f"Unexpected source contents: {source_names - allowed}"
    required = allowed - {"pyproject.toml.orig"}
    assert required <= source_names, f"Missing source files: {required - source_names}"
    print(
        f"Artifact allowlists passed: {len(names)} wheel files; {len(source_names)} source files."
    )


def dependency_licenses():
    for package in sorted(distributions(), key=lambda item: item.metadata["Name"].lower()):
        if package.metadata["Name"] == "oci-invoice-investigator":
            continue
        license_name = package.metadata.get("License-Expression")
        if not license_name:
            license_name = "; ".join(
                item
                for item in package.metadata.get_all("Classifier", [])
                if item.startswith("License ::")
            ) or package.metadata.get("License", "UNDECLARED")
        print(f"{package.metadata['Name']} {package.version}: {license_name[:160]}")


if __name__ == "__main__":
    distribution_contents()
    dependency_licenses()
