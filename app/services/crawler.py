import asyncio
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright
from sqlalchemy import select

from app.core.logger import AppLogger
from app.core.models import Listing, ListingType
from app.services.notify import send_discord_notifications
from app.services.parse import parse_page

logger = AppLogger(name="crawler").get_logger()

async def read_urls():
    path = Path("config/urls.txt")

    if not path.exists():
        logger.error("urls.txt not found in project root!")
        return []

    with open(path, encoding="utf-8") as file:
        return [line.strip() for line in file.readlines() if line.strip()]

async def scrape_url(browser, page_url, db_session):
    logger.info(f"Scraping: {page_url}")

    new_listings = []
    page_num = 1

    browser_page = await browser.new_page(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )

    try:
        while True:
            current_url = f"{page_url}{page_num}/" if page_num > 1 else page_url

            await browser_page.goto(current_url, wait_until="domcontentloaded")
            await asyncio.sleep(2)

            listings, has_more = await parse_page(browser_page)
            logger.info(f"Found {len(listings)} listings on page {page_num}")

            # Check each listing against database
            for item_id, data in listings.items():

                result = await db_session.execute(
                    select(Listing).where(Listing.item_id == item_id)
                )
                existing = result.scalar_one_or_none()

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

                    db_session.add(new_listing)

                    new_listings.append({
                        "item_id": item_id,
                        "url": data["url"],
                        "price": data["price"],
                        "old_price": None,
                        "type": "new",
                        "is_price_per_sqm": data.get("is_price_per_sqm", False),  # NEW
                        "location": data.get("location"),  # NEW
                    })

            await db_session.commit()

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

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)

        try:
            for idx, page_url in enumerate(urls, 1):
                logger.info(f"Processing URL {idx}/{len(urls)}")

                session_factory = db_client.async_session_factory()
                async with session_factory() as session:
                    new_listings = await scrape_url(browser, page_url, session)

                    if new_listings:
                        send_discord_notifications(new_listings)
                    else:
                        logger.info("No new listings or changes found")

                # Small delay between URLs
                await asyncio.sleep(5)

        finally:
            await browser.close()

    logger.info("Crawler finished")