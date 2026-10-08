from pathlib import Path

from playwright.sync_api import expect


def test_authenticated_pdf_renders_and_citation_resolves(review_page):
    expect(review_page.get_by_role("status")).to_have_text("Page 1 of 1")
    expect(review_page.get_by_role("img", name="Invoice PDF page 1 of 1")).to_be_visible()
    expect(
        review_page.get_by_text("20 units lack receiving evidence;", exact=False)
    ).to_be_visible()
    review_page.screenshot(
        path=str(Path(__file__).resolve().parents[2] / ".tmp/reviewer.png"), full_page=True
    )
    review_page.get_by_role("link", name="purchasing.json v1 /amendments/0", exact=True).click()
    expect(review_page.locator("pre")).to_contain_text('"unit_price": "12.00"')
    review_page.get_by_role("link", name="Back to case").click()
    review_page.get_by_role("link", name="purchasing.json v1 /receipts/0", exact=True).click()
    expect(review_page.locator("pre")).to_contain_text('"quantity": 80')


def test_mobile_layout_and_keyboard_skip_link(review_page):
    review_page.set_viewport_size({"width": 390, "height": 844})
    review_page.reload()
    expect(
        review_page.get_by_role("heading", name="Receiving evidence review", exact=True)
    ).to_be_visible()
    assert review_page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    review_page.keyboard.press("Tab")
    expect(review_page.get_by_role("link", name="Skip to main content")).to_be_focused()
    review_page.keyboard.press("Enter")
    expect(review_page.locator("#main")).to_be_focused()
