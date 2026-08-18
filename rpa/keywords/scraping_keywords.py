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

    # CSS selectors for UMANG Jan Aushadhi Sugam
    _SEL_SEARCH_ICON    = ".search-page, .fa-search"
    _SEL_SEARCH_INPUT   = "input.search-box, input[placeholder='Search Medicine']"
    _SEL_MEDICINE_NAME  = "mat-cell.mat-column-MedicineName p"
    _SEL_SIZE           = "mat-cell.mat-column-Size span, mat-cell.mat-column-Size p"
    _SEL_PRICE          = "mat-cell.mat-column-Price p"
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

        Must be called once before any scraping calls within a suite run.
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

    @keyword("Scrape UMANG Medicine")
    def scrape_umang_medicine(self, salt_name: str) -> dict:
        """Search for *salt_name* on the UMANG portal and extract the top result.

        Returns:
            dict with keys: ``name``, ``size``, ``price``

        Raises:
            ScrapeStructureError: if any expected selector is absent.
        """
        if self._browser is None:
            raise RuntimeError("Call 'Open Pharmacy Source' first.")

        # If search input isn't visible, click the magnifying glass
        try:
            # Short wait to see if input is already there
            self._browser.wait_for_elements_state(self._SEL_SEARCH_INPUT, "visible", timeout=2000)
        except Exception:
            self._browser.click(self._SEL_SEARCH_ICON)
            self._browser.wait_for_elements_state(self._SEL_SEARCH_INPUT, "visible", timeout=2000)

        # Type the search term and press Enter
        self._browser.fill_text(self._SEL_SEARCH_INPUT, salt_name)
        self._browser.press_keys(self._SEL_SEARCH_INPUT, "Enter")

        # Wait for network idle after search
        self._browser.wait_for_load_state(state="networkidle", timeout=self._NETWORK_IDLE_MS)
        self._browser.sleep("2s") # Extra stabilization for Angular mat-table rendering

        result = {}
        missing = []

        for field, selector in [
            ("name",  self._SEL_MEDICINE_NAME),
            ("size",  self._SEL_SIZE),
            ("price", self._SEL_PRICE),
        ]:
            try:
                # get_text gets the text of the first matching element
                text = self._browser.get_text(selector)
                result[field] = text.strip()
            except Exception:
                missing.append(field)

        if missing:
            raise ScrapeStructureError(
                f"Expected selectors missing for '{salt_name}': {missing}. "
                "The UMANG site may have changed its HTML structure."
            )

        logger.info(f"Scraped UMANG: {result['name']} | Size: {result['size']} | Price: {result['price']}")
        return result
