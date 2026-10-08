import runpy
import zipfile
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[2] / "tools/verify_frontend_assets.py"


@pytest.mark.parametrize("changed", [False, True])
def test_packaged_resource_bytes_must_match_verified_source(tmp_path, changed):
    verify = runpy.run_path(str(TOOL))["verify_packaged_resources"]
    source = tmp_path / "pdf.mjs"
    source.write_bytes(b"verified renderer bytes")
    wheel = tmp_path / "test.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("pdf.mjs", source.read_bytes() + (b"X" if changed else b""))
    with zipfile.ZipFile(wheel) as archive:
        if changed:
            with pytest.raises(AssertionError, match="Packaged resource differs"):
                verify(archive.read, {source}, tmp_path)
        else:
            verify(archive.read, {source}, tmp_path)
