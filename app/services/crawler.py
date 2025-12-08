import asyncio
import hashlib
import sys
from datetime import datetime
from playwright.async_api import async_playwright

from app.core.config import config
from app.core.logger import AppLogger
from app.core.models import Listing, ListingType
from app.services.notify import send_discord_notifications
from app.services.parse import parse_page

logger = AppLogger(name="crawler").get_logger()

async def read_urls():
    urls = config.urls

    if not urls:
        logger.error("No URLs configured in config.yaml")
        sys.exit(1)
    else:
        return urls

def get_url_hash(urls: list[str]) -> str:
    """Generate a hash of the URL list to detect changes."""
    url_string = "|".join(sorted(urls))
    return hashlib.md5(url_string.encode()).hexdigest()


async def check_and_handle_url_changes(urls: list[str], db_client) -> bool:
    """Check if URLs have changed since last run and flush if needed."""
    current_hash = get_url_hash(urls)
    stored_hash = await db_client.get_url_hash()

    if stored_hash is None:
        logger.info("First run detected. Storing URL configuration.")
        await db_client.set_url_hash(current_hash)
        return False

    if current_hash != stored_hash:
        logger.warning("URL configuration has changed!")
        logger.warning(f"Stored hash: {stored_hash}")
        logger.warning(f"Current hash: {current_hash}")

        if config.database.auto_flush:
            deleted_count = await db_client.flush_listings()
            logger.info(f"Flushed {deleted_count} listings due to URL change")
        else:
            logger.info("Auto-flush is disabled. Existing listings will be kept.")

        await db_client.set_url_hash(current_hash)
        return True

    logger.debug("URL configuration unchanged")
    return False

async def scrape_url(browser, page_url, db_client):
    logger.info(f"Scraping: {page_url}")

    new_listings = []
    page_num = 1

    browser_page = await browser.new_page(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )

    session_factory = db_client.async_session_factory()
    async with session_factory() as session:
        try:
            while True:
                current_url = f"{page_url}{page_num}/" if page_num > 1 else page_url

                await browser_page.goto(current_url, wait_until="domcontentloaded")
                await asyncio.sleep(2)

                listings, has_more = await parse_page(browser_page)
                logger.info(f"Found {len(listings)} listings on page {page_num}")

                # Check each listing against database
                for item_id, data in listings.items():

                    existing = await db_client.get_listing_by_id(session, item_id)

                    if existing:
                        # Check for price change
                        if existing.price != data["price"]:
                            logger.info(f"Price change detected for {item_id}: {existing.price} -> {data['price']}")
                            existing.last_price = existing.price
                            existing.price = data["price"]
                            existing.last_seen = datetime.now()
                            existing.accessed_time = datetime.now()

                            new_listings.append({
                                "item_id": item_id,
                                "url": data["url"],
                                "price": data["price"],
                                "old_price": existing.last_price,
                                "type": "price_change"
                            })
                        else:
                            existing.last_seen = datetime.now()
                            existing.accessed_time = datetime.now()
                    else:
                        # New listing
                        logger.info(f"New listing found: {item_id}")
                        now = datetime.now()

                        new_listing = Listing(
                            item_id=item_id,
                            url=data["url"],
                            listing_type=ListingType.selling,
                            price=data["price"],
                            last_price=None,
                            is_price_per_sqm=data.get("is_price_per_sqm", False),
                            location=data.get("location"),
                            first_seen=now,
                            last_seen=now,
                            accessed_time=now
                        )

                        await db_client.insert_listing(session, new_listing)

                        new_listings.append({
                            "item_id": item_id,
                            "url": data["url"],
                            "price": data["price"],
                            "old_price": None,
                            "type": "new",
                            "is_price_per_sqm": data.get("is_price_per_sqm", False),  # NEW
                            "location": data.get("location"),  # NEW
                        })

                await session.commit()

                if not has_more or page_num >= 5:
                    break

                page_num += 1
                await asyncio.sleep(10)  # Longer delay between pages

        finally:
            await browser_page.close()

    return new_listings

async def crawl(db_client):

    logger.info("Starting crawler ...")

    # Read URL configuration
    urls = await read_urls()
    if not urls:
        logger.error("No URLs configured")
        return

    logger.info(f"Found {len(urls)} URLs to scrape")

    # Check for URL changes and handle flush
    await check_and_handle_url_changes(urls, db_client)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)

        try:
            for idx, page_url in enumerate(urls, 1):
                logger.info(f"Processing URL {idx}/{len(urls)}")

                new_listings = await scrape_url(browser, page_url, db_client)

                if new_listings:
                    send_discord_notifications(new_listings)
                else:
                    logger.info("No new listings or changes found")

                # Small delay between URLs
                await asyncio.sleep(5)

        finally:
            await browser.close()

    logger.info("Crawler finished")