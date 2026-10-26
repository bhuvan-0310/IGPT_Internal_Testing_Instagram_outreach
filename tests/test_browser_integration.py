"""These tests never launch a real browser or touch Instagram; they only
cover the pure validation/state-tracking logic in src.integrations.browser."""
from src.integrations import browser as browser_module


def test_is_safe_url_accepts_http_and_https():
    assert browser_module.is_safe_instagram_or_source_url("https://www.instagram.com/someone/")
    assert browser_module.is_safe_instagram_or_source_url("http://example.com/reel/123")


def test_is_safe_url_rejects_dangerous_schemes():
    assert not browser_module.is_safe_instagram_or_source_url("javascript:alert(1)")
    assert not browser_module.is_safe_instagram_or_source_url("file:///etc/passwd")
    assert not browser_module.is_safe_instagram_or_source_url("data:text/html,<script>")
    assert not browser_module.is_safe_instagram_or_source_url("")
    assert not browser_module.is_safe_instagram_or_source_url(None)


def test_profile_url_for_uses_profile_url_only_for_instagram_profiles():
    assert browser_module.profile_url_for("alice", "https://www.instagram.com/alice/") == "https://www.instagram.com/alice/"
    assert browser_module.profile_url_for("alice", "https://scontent.cdninstagram.com/avatar.jpg") == "https://www.instagram.com/alice/"
    assert browser_module.profile_url_for("@alice", None) == "https://www.instagram.com/alice/"


def test_open_url_relaunches_after_a_closed_browser_connection(monkeypatch):
    class ClosedContext:
        def new_page(self):
            raise RuntimeError("Playwright connection closed")

    class Page:
        visited = None

        def goto(self, url, wait_until):
            self.visited = (url, wait_until)

    class WorkingContext:
        def __init__(self):
            self.page = Page()

        def new_page(self):
            return self.page

    working_context = WorkingContext()
    contexts = iter([ClosedContext(), working_context])
    monkeypatch.setattr(browser_module, "launch_dedicated_browser", lambda: next(contexts))

    page = browser_module.open_url("https://www.instagram.com/alice/")

    assert page is working_context.page
    assert page.visited == ("https://www.instagram.com/alice/", "domcontentloaded")


def test_close_dedicated_browser_is_safe_when_nothing_running():
    browser_module.close_dedicated_browser()  # should not raise
    assert browser_module.is_running() is False
