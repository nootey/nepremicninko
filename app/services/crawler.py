import asyncio
import hashlib
import sys
from datetime import datetime
from logging import Logger

from playwright.async_api import async_playwright

from app.core.config import config
from app.core.database import DatabaseClient
from app.core.models import Listing, ListingType, get_model_hash
from app.services.notify import send_discord_error, send_discord_notifications
from app.services.parse import parse_page


def determine_listing_type(url: str) -> ListingType:
    if "oglasi-oddaja" in url:
        return ListingType.renting
    elif "oglasi-prodaja" in url:
        return ListingType.selling
    else:
        return ListingType.selling


async def read_urls(logger: Logger):
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


async def check_and_handle_url_changes(urls: list[str], db_client: DatabaseClient, logger: Logger) -> bool:
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


async def check_schema_changes(db_client: DatabaseClient, logger: Logger) -> bool:
    """Check if model schema has changed and flush if needed."""
    current_hash = get_model_hash()
    stored_hash = await db_client.get_schema_hash()

    if stored_hash is None:
        logger.info("First run detected. Storing schema hash.")
        await db_client.set_schema_hash(current_hash)
        return False

    if current_hash != stored_hash:
        logger.warning("Database schema has changed!")
        logger.warning(f"Stored hash: {stored_hash}")
        logger.warning(f"Current hash: {current_hash}")

        deleted_count = await db_client.flush_listings()
        logger.info(f"Flushed {deleted_count} listings due to schema change")

        await db_client.set_schema_hash(current_hash)
        return True

    logger.debug("Schema unchanged")
    return False


async def scrape_url(browser, page_url, db_client: DatabaseClient, logger: Logger):
    logger.info(f"Scraping: {page_url}")

    new_listings = []
    page_num = 1

    async def create_browser_page():
        """Helper to create new browser page with consistent user agent."""
        return await browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

    browser_page = await create_browser_page()

    session_factory = db_client.async_session_factory()
    async with session_factory() as session:
        try:
            while True:
                # Build URL with pagination
                if page_num == 1:
                    current_url = page_url
                else:
                    # Split URL into base and query string
                    if "?" in page_url:
                        base_url, query_string = page_url.split("?", 1)
                        current_url = f"{base_url}{page_num}/?{query_string}"
                    else:
                        current_url = f"{page_url}{page_num}/"

                logger.info(f"Navigating to page {page_num}: {current_url}")

                await browser_page.goto(current_url, wait_until="domcontentloaded", timeout=30000)  # 30s max
                await asyncio.sleep(2)

                listings, has_more = await parse_page(browser_page, logger)
                logger.info(f"Found {len(listings)} listings on page {page_num}")

                if not listings:
                    logger.info(f"No more listings on page {page_num}, stopping pagination")
                    break

                # Check each listing against database
                for item_id, data in listings.items():
                    try:
                        existing = await db_client.get_listing_by_id(session, item_id)

                        if existing:
                            # Check for price change
                            if existing.price != data["price"]:
                                logger.info(f"Price change detected for {item_id}: {existing.price} -> {data['price']}")
                                existing.last_price = existing.price
                                existing.price = data["price"]
                                existing.last_seen = datetime.now()
                                existing.accessed_time = datetime.now()

                                new_listings.append(
                                    {
                                        "item_id": item_id,
                                        "url": data["url"],
                                        "price": data["price"],
                                        "old_price": existing.last_price,
                                        "type": "price_change",
                                        "listing_type": existing.listing_type.value,
                                        "size_sqm": existing.size_sqm,
                                    }
                                )
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
                                listing_type=determine_listing_type(page_url),
                                price=data["price"],
                                last_price=None,
                                size_sqm=data.get("size_sqm"),
                                location=data.get("location"),
                                first_seen=now,
                                last_seen=now,
                                accessed_time=now,
                            )

                            await db_client.insert_listing(session, new_listing)

                            new_listings.append(
                                {
                                    "item_id": item_id,
                                    "url": data["url"],
                                    "price": data["price"],
                                    "old_price": None,
                                    "type": "new",
                                    "listing_type": determine_listing_type(page_url),
                                    "location": data.get("location"),
                                    "size_sqm": data.get("size_sqm"),
                                }
                            )

                        await session.commit()
                    except Exception as e:
                        await session.rollback()
                        logger.error(f"Failed to save listing {item_id}: {e}", exc_info=True)
                        continue

                if not has_more:
                    logger.info(f"No more pages available after page {page_num}, stopping pagination")
                    break

                if page_num >= config.app.max_pages_per_url:
                    logger.warning(
                        f"Available pages exceed configured maximum of: {config.app.max_pages_per_url}, stopping pagination"
                    )
                    break

                # Close and reopen page before going to next page
                logger.debug("Closing and reopening browser page for next page ...")
                await browser_page.close()
                browser_page = await create_browser_page()

                page_num += 1
                await asyncio.sleep(10)  # Longer delay between pages

        except Exception as e:
            logger.error(f"Error during scrape_url: {e}", exc_info=True)
            if config.discord.notify_on_error:
                send_discord_error(str(e), logger.getChild("discord"), page_url)

        finally:
            await browser_page.close()

    return new_listings


async def crawl(db_client: DatabaseClient, logger: Logger):
    c_logger = logger.getChild("crawler")
    c_logger.info("Starting crawler ...")

    # Check for schema changes first
    await check_schema_changes(db_client, c_logger)

    # Read URL configuration
    urls = await read_urls(c_logger)
    if not urls:
        c_logger.error("No URLs configured")
        return

    c_logger.info(f"Found {len(urls)} URLs to scrape")

    # Check for URL changes and handle flush
    await check_and_handle_url_changes(urls, db_client, c_logger)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)

        try:
            for idx, page_url in enumerate(urls, 1):
                c_logger.info(f"Processing URL {idx}/{len(urls)}")

                new_listings = await scrape_url(browser, page_url, db_client, c_logger)

                if new_listings:
                    send_discord_notifications(new_listings, c_logger.getChild("discord"))
                else:
                    c_logger.info("No new listings or changes found")

                # Small delay between URLs
                await asyncio.sleep(5)

        except Exception as e:
            c_logger.error(f"Error during crawl: {e}", exc_info=True)
            if config.discord.notify_on_error:
                send_discord_error(str(e), c_logger.getChild("discord"), page_url)
        finally:
            await browser.close()

    c_logger.info("Crawler finished")
