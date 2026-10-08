from types import SimpleNamespace

import pytest
from django.core.management import call_command
from django.test.testcases import LiveServerThread
from playwright.sync_api import sync_playwright


@pytest.fixture
def app_server(transactional_db, settings, tmp_path):
    settings.STATIC_ROOT = str(tmp_path / "static")
    call_command("collectstatic", interactive=False, verbosity=0)
    # Exercise WhiteNoise with DEBUG=False; no test static-files bypass.
    server = LiveServerThread("127.0.0.1", static_handler=lambda app: app)
    server.start()
    assert server.is_ready.wait(5), "Local web server startup timed out."
    if server.error:
        raise server.error
    try:
        yield SimpleNamespace(url=f"http://127.0.0.1:{server.port}")
    finally:
        server.terminate()


@pytest.fixture
def browser(sample_case):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    context = browser.new_context(viewport={"width": 1365, "height": 1000})
    page = context.new_page()
    page.set_default_timeout(7000)
    yield page
    context.close()


@pytest.fixture
def review_page(sample_case, app_server, page):
    page.goto(app_server.url)
    page.get_by_label("Username", exact=True).fill("reviewer")
    page.get_by_label("Password", exact=True).fill("local-test-password")
    page.get_by_role("button", name="Sign in", exact=True).click()
    page.get_by_role("link", name="Review case-002", exact=True).click()
    return page
