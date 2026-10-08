from playwright.sync_api import expect


def test_review_confirm_refresh_and_retry_create_one_task(review_page):
    review_page.get_by_role("link", name="Review proposed task").click()
    expect(review_page.get_by_role("heading", name="Approve this follow-up?")).to_be_visible()
    expect(
        review_page.get_by_text("physical nondelivery is not established.", exact=False)
    ).to_be_visible()
    review_page.get_by_role("checkbox").check()
    review_page.get_by_role("button", name="Approve and create task").click()
    expect(review_page.locator('[id^="task-"]')).to_have_count(1)
    review_page.reload()
    expect(review_page.locator('[id^="task-"]')).to_have_count(1)
    review_page.get_by_role("link", name="Review proposed task").click()
    review_page.get_by_role("checkbox").check()
    review_page.get_by_role("button", name="Approve and create task").click()
    expect(review_page.locator('[id^="task-"]')).to_have_count(1)
