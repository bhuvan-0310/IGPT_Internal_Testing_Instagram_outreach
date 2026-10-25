"""Dedicated, persistent Playwright browser profile for manually-assisted
outreach. This module launches a real, visible Chromium window using a
profile directory separate from the user's everyday Chrome profile, and does
nothing else automatically:

- No stealth plugins, fingerprint spoofing, or bot-detection evasion.
- No CAPTCHA solving.
- No automated login — the user authenticates to Instagram themselves,
  directly in the launched window. This app never sees or stores that
  password.
- No automated sending of messages, follows, or comments. The user performs
  the action themselves; the app only helps them open the right page and
  then lets them confirm, afterwards, that they did it.
"""
from pathlib import Path
from src.config import BROWSER_PROFILE_DIR

_context = None
_playwright = None


class BrowserLaunchError(RuntimeError):
    pass


def is_running() -> bool:
    return _context is not None


def launch_dedicated_browser():
    """Launch (or return the existing) persistent browser context using the
    dedicated profile directory. Raises BrowserLaunchError with an
    actionable message if Playwright or its browsers are not installed."""
    global _context, _playwright
    if _context is not None:
        return _context
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise BrowserLaunchError(
            "Playwright is not installed. Run 'pip install playwright' and "
            "'playwright install chromium' inside the project's .venv."
        ) from exc

    BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    _playwright = sync_playwright().start()
    try:
        _context = _playwright.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_PROFILE_DIR),
            headless=False,
        )
    except Exception as exc:  # noqa: BLE001
        _playwright.stop()
        _playwright = None
        raise BrowserLaunchError(
            "Could not launch the dedicated browser. If this is the first run, install the "
            f"browser binary with 'playwright install chromium'. Details: {exc}"
        ) from exc
    return _context


def open_url(url: str):
    """Open a URL in a new tab of the dedicated browser context. The caller
    is responsible for validating the URL before calling this."""
    context = launch_dedicated_browser()
    page = context.new_page()
    page.goto(url)
    return page


def close_dedicated_browser():
    global _context, _playwright
    if _context is not None:
        try:
            _context.close()
        except Exception:
            pass
        _context = None
    if _playwright is not None:
        try:
            _playwright.stop()
        except Exception:
            pass
        _playwright = None


def is_safe_instagram_or_source_url(url: str) -> bool:
    """Minimal sanity check before opening a URL from imported/prospect data:
    require http(s) scheme. We do not restrict to instagram.com only, since
    source_reel_url may point at other permitted platforms, but we do reject
    non-http(s) schemes (javascript:, file:, data:, etc.)."""
    url = (url or "").strip()
    return url.startswith("http://") or url.startswith("https://")
