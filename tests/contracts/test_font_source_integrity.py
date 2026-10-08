import runpy
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[2] / "tools/verify_frontend_assets.py"


@pytest.mark.parametrize("content", [None, b"altered font source archive"])
def test_missing_or_changed_corresponding_source_is_rejected(tmp_path, content):
    verify = runpy.run_path(str(TOOL))["font_source_resources"]
    directory = tmp_path / "src/invoice_investigator/web/third_party_sources"
    directory.mkdir(parents=True)
    if content is not None:
        (directory / "liberation-fonts-1.07.4.tar.gz").write_bytes(content)
    with pytest.raises((FileNotFoundError, ValueError)):
        verify(tmp_path)
