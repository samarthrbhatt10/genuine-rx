"""
scraping_keywords.py — Browser-based pharmacy scraping keywords.

Requires: robotframework-browser (18.x) + `rfbrowser init` run once.
Must run inside the Python 3.11 venv (rpaframework constraint).

Keyword names match 05_ROBOT_FRAMEWORK_SPEC.md exactly.
"""
import os

from robot.api import logger
from robot.api.deco import keyword, library


class ScrapeStructureError(Exception):
    """Raised when expected page selectors are missing.

    Never return partial or empty data silently — surfacing this error
    is the point: it means the pharmacy site changed its HTML structure
    and the selectors need updating.
    """


@library(scope="SUITE", auto_keywords=False)
class ScrapingKeywords:
    """Keyword library for outbound HTTP / browser-based scraping.

    This is the ONLY layer permitted to make network requests to external
    pharmacy sites (per 01_ARCHITECTURE.md hard-boundary rules).
    """

    ROBOT_LIBRARY_SCOPE = "SUITE"

    # CSS selectors for 1mg product pages — update here if the site changes.
    # All selectors are read from shared.resource at suite level; the defaults
    # below are used when the library is imported standalone for unit testing.
    _SEL_MEDICINE_NAME  = "h1.style__pro-title___3zKNC, h1[data-style='pro-title']"
    _SEL_MRP            = "span.style__price-tag___KzOkY, .slotDiscount_striked__price___KJSQ1"
    _SEL_PRICE          = "span.style__price___mM6an, .drug-price-container .price"
    _SEL_SALT_TEXT      = "div.DrugHeader__meta-value___vqYVV, .saltInfo"
    _USER_AGENT         = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    _NETWORK_IDLE_MS    = 5000

    def __init__(self):
        self._browser = None

    # ------------------------------------------------------------------ #
    # Keywords
    # ------------------------------------------------------------------ #

    @keyword("Open Pharmacy Source")
    def open_pharmacy_source(self, url: str) -> None:
        """Launch a Browser Library session, set a realistic user-agent,
        and wait until network activity is idle.

        Must be called once before any ``Scrape Medicine Page`` calls within
        a suite run.  The smoke suite calls this to validate connectivity.
        """
        try:
            from Browser import Browser  # noqa: PLC0415  # type: ignore[import-not-found,import-untyped]
        except ImportError as exc:
            raise RuntimeError(
                "robotframework-browser is not installed. "
                "Install it in the Python 3.11 venv with `pip install -r requirements-rpa.txt` "
                "then run `rfbrowser init`."
            ) from exc

        self._browser = Browser()
        self._browser.new_browser(
            browser="chromium",
            headless=True,
            args=[f"--user-agent={self._USER_AGENT}"],
        )
        self._browser.new_page(url)
        self._browser.wait_for_load_state(state="networkidle", timeout=self._NETWORK_IDLE_MS)
        logger.info(f"Opened pharmacy source: {url}")

    @keyword("Scrape Medicine Page")
    def scrape_medicine_page(self, product_url: str) -> dict:
        """Navigate to *product_url* and extract structured medicine data.

        Returns:
            dict with keys: ``name``, ``mrp``, ``price``, ``raw_salt_text``

        Raises:
            ScrapeStructureError: if any expected selector is absent —
                never returns partial/empty data silently.
        """
        if self._browser is None:
            raise RuntimeError(
                "Call 'Open Pharmacy Source' before 'Scrape Medicine Page'."
            )

        self._browser.go_to(product_url)
        self._browser.wait_for_load_state(state="networkidle", timeout=self._NETWORK_IDLE_MS)

        result = {}
        missing = []

        for field, selector in [
            ("name",          self._SEL_MEDICINE_NAME),
            ("mrp",           self._SEL_MRP),
            ("price",         self._SEL_PRICE),
            ("raw_salt_text", self._SEL_SALT_TEXT),
        ]:
            try:
                text = self._browser.get_text(selector)
                result[field] = text.strip()
            except Exception:
                missing.append(field)

        if missing:
            raise ScrapeStructureError(
                f"Expected selectors missing on {product_url}: {missing}. "
                "The pharmacy site may have changed its HTML structure — "
                "update the selectors in scraping_keywords.py."
            )

        logger.info(f"Scraped: {result['name']} @ {product_url}")
        return result
