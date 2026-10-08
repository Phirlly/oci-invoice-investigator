# Third-party notices

Original project code, documentation and synthetic examples use the root MIT
license. Third-party files retain their own copyrights and terms. The MIT
license does not replace the notices below.

## Bundled frontend assets

Assets are unchanged selections from Bootstrap 5.3.8 and PDF.js 6.4.299 official
release archives. Their file and archive digests are recorded in
`src/invoice_investigator/web/static/review/vendor/manifest.json`.

Within that vendor directory:

| Component | License/notice location |
| --- | --- |
| Bootstrap CSS | `bootstrap/LICENSE` (MIT) |
| PDF.js renderer and worker | `pdfjs/LICENSE` (Apache-2.0) |
| Adobe character maps | `pdfjs/cmaps/LICENSE` |
| Foxit/PDFium standard fonts | `pdfjs/standard_fonts/LICENSE_FOXIT` |
| Liberation Sans 1.07.4 | `pdfjs/standard_fonts/LICENSE_LIBERATION` (GPL-2 with the stated Liberation exceptions) |
| ICC profile | `pdfjs/iccs/LICENSE` (CC0-1.0) |
| JBIG2 decoder | `pdfjs/wasm/LICENSE_JBIG2`, `LICENSE_PDFJS_JBIG2` |
| OpenJPEG decoder | `pdfjs/wasm/LICENSE_OPENJPEG`, `LICENSE_PDFJS_OPENJPEG` |
| QCMS color conversion | `pdfjs/wasm/LICENSE_QCMS`, `LICENSE_PDFJS_QCMS` |

All these notices accompany their assets in the repository, wheel and source
distribution. Upstream sources:

- [Bootstrap 5.3.8](https://github.com/twbs/bootstrap/releases/tag/v5.3.8)
- [PDF.js 6.4.299](https://github.com/mozilla/pdf.js/releases/tag/v6.4.299)

## Liberation corresponding source

The complete upstream Liberation Fonts 1.07.4 source archive accompanies the
fonts at
`src/invoice_investigator/web/third_party_sources/liberation-fonts-1.07.4.tar.gz`.
It contains the editable SFD sources, build scripts, Makefile, authors and
license texts. See the adjacent `README.md` for provenance, digest and build
instructions. Installed wheels retain these files under
`invoice_investigator/web/third_party_sources/` in site-packages.

The bundled fonts are unchanged from the pinned PDF.js release. Its maintainers
identify them as 1.07.4 using their metadata and font metrics in
[PDF.js PR 21750](https://github.com/mozilla/pdf.js/pull/21750).
The project does not claim a locally reproduced font build or byte equality to
another upstream prebuilt archive.

## Separately installed dependencies

`pyproject.toml` and `uv.lock` identify dependencies. Their installed distributions
retain their own license notices; those distributions are not embedded in this
source repository or application wheel. In particular, Psycopg uses LGPL-3.0.
Any future container or bundled runtime release must carry the notices and
source provisions applicable to the dependency binaries it actually includes.
