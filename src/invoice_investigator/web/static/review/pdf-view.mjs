import { getDocument, GlobalWorkerOptions } from "./vendor/pdfjs/pdf.mjs";

const view = document.getElementById("pdf-view");
const status = document.getElementById("pdf-status");
const canvas = document.getElementById("invoice-canvas");
const previous = document.getElementById("pdf-prev");
const next = document.getElementById("pdf-next");
const assets = new URL(view.dataset.assets, location.origin).href;
GlobalWorkerOptions.workerSrc = assets + "pdf.worker.mjs";
let pdf, pageNumber = 1, busy = false;

async function render() {
  if (busy) return;
  busy = true;
  previous.disabled = next.disabled = true;
  try {
    const page = await pdf.getPage(pageNumber);
    const initial = page.getViewport({ scale: 1 });
    const scale = Math.min(1.5, Math.sqrt(4_000_000 / (initial.width * initial.height)));
    const viewport = page.getViewport({ scale });
    canvas.width = viewport.width;
    canvas.height = viewport.height;
    await page.render({ canvasContext: canvas.getContext("2d"), viewport }).promise;
    canvas.setAttribute("aria-label", `Invoice PDF page ${pageNumber} of ${pdf.numPages}`);
    status.textContent = `Page ${pageNumber} of ${pdf.numPages}`;
  } catch {
    status.textContent = "PDF could not be displayed. Read the invoice fields below.";
  } finally {
    busy = false;
    previous.disabled = pageNumber <= 1;
    next.disabled = pageNumber >= pdf.numPages;
  }
}
previous.addEventListener("click", () => { if (!busy && pageNumber > 1) { pageNumber--; render(); } });
next.addEventListener("click", () => { if (!busy && pageNumber < pdf.numPages) { pageNumber++; render(); } });

const loading = getDocument({
  url: new URL(view.dataset.document, location.origin).href,
  isEvalSupported: false, enableXfa: false, maxImageSize: 4_000_000,
  cMapUrl: assets + "cmaps/", cMapPacked: true,
  standardFontDataUrl: assets + "standard_fonts/", wasmUrl: assets + "wasm/",
});
const deadline = setTimeout(() => { loading.destroy(); }, 15000);
try {
  pdf = await loading.promise;
  if (pdf.numPages < 1 || pdf.numPages > 5) throw new Error("Unsupported page count");
  await render();
} catch {
  status.textContent = "PDF could not be displayed. Read the invoice fields below.";
} finally {
  clearTimeout(deadline);
}
