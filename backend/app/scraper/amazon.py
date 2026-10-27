import asyncio
import logging
import random
from urllib.parse import quote_plus

from app.schemas import RawReview
from app.scraper.parser import parse_amazon_html

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0",
]

AMAZON_CAPTCHA_STRINGS = [
    "validatecaptcha",
    "enter the characters you see below",
    "robot check",
    "api-services-support@amazon.com",
]


class ScrapeBlockedError(Exception):
    """Raised when a CAPTCHA or blocking wall is encountered."""


async def scrape_amazon(query: str, timeout: float = 8.0) -> list[RawReview]:
    """Scrapes Amazon.in reviews for the given query using Playwright.

    Aborts immediately on CAPTCHA detection without retrying.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.warning("Playwright not installed; cannot scrape live Amazon")
        return []

    url = f"https://www.amazon.in/s?k={quote_plus(query)}"
    user_agent = random.choice(USER_AGENTS)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=user_agent,
                viewport={"width": 1280, "height": 800},
                locale="en-IN",
            )
            page = await context.new_page()

            # Navigate to search page
            await page.goto(url, timeout=int(timeout * 500), wait_until="domcontentloaded")
            content = await page.content()

            # Immediate CAPTCHA check
            content_lower = content.lower()
            if any(term in content_lower for term in AMAZON_CAPTCHA_STRINGS):
                await browser.close()
                raise ScrapeBlockedError("Amazon CAPTCHA / bot verification detected")

            # Try to find first product link
            first_product = await page.query_selector("a.a-link-normal.s-no-outline, a.a-link-normal.s-underline-text")
            if not first_product:
                await browser.close()
                return []

            href = await first_product.get_attribute("href")
            if not href:
                await browser.close()
                return []

            if not href.startswith("http"):
                href = f"https://www.amazon.in{href}"

            # Navigate to product page
            await page.goto(href, timeout=int(timeout * 500), wait_until="domcontentloaded")
            product_content = await page.content()

            if any(term in product_content.lower() for term in AMAZON_CAPTCHA_STRINGS):
                await browser.close()
                raise ScrapeBlockedError("Amazon product page CAPTCHA detected")

            reviews = parse_amazon_html(product_content, product_query=query)
            await browser.close()
            return reviews

    except ScrapeBlockedError:
        raise
    except Exception as exc:
        logger.warning("Amazon live scrape error: %s", exc)
        return []
