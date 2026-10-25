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


def test_close_dedicated_browser_is_safe_when_nothing_running():
    browser_module.close_dedicated_browser()  # should not raise
    assert browser_module.is_running() is False
