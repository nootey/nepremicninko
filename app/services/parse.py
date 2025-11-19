from playwright.async_api import Page, Locator
from app.core.logger import AppLogger

logger = AppLogger(name="parser").get_logger()

async def parse_page(browser_page: Page) -> tuple[dict, bool]:

    logger.debug(f"Parsing page: {browser_page.url}")

    # Try to reject cookies if the button exists
    try:
        cookie_button = browser_page.get_by_role("button", name="Zavrni")
        if await cookie_button.count() > 0:
            await cookie_button.click()
            logger.debug("Rejected cookies")
    except Exception as e:
        logger.debug(f"No cookie banner or already dismissed: {e}")

    # Wait for the page to load
    await browser_page.wait_for_load_state("domcontentloaded")

    extracted_data = {}

    # Find all listing containers
    xpath = """//*[@id="vsebina760"]/div[contains(@class, "seznam")]/div/div/div/div[contains(@class, "col-md-6 col-md-12 position-relative")]"""

    results = await browser_page.locator(xpath).all()

    logger.info(f"Found {len(results)} listing containers")
    logger.info(f"Starting to parse listings...")

    # Loop through all listings
    for idx, result in enumerate(results):
        logger.info(f"Processing listing {idx + 1}/{len(results)}...")
        try:
            item_id, data = await parse_result(result, idx)
            extracted_data[item_id] = data
        except Exception as e:
            logger.warning(f"✗ Error parsing listing {idx + 1}: {e}")
            continue  # skip to next listing instead of crashing

    # Check if there's a next page button
    next_page_xpath = """xpath=//*[@id='pagination']/ul/li[contains(@class, 'paging_next')]"""
    more_pages = await browser_page.locator(next_page_xpath).count() > 0

    logger.info(f"Parsing finished. Extracted {len(extracted_data)} listings. More pages: {more_pages}")

    return extracted_data, more_pages

async def parse_result(item: Locator, idx: int) -> tuple[str, dict]:

    try:
        # Get the details section
        details = item.locator('xpath=div/div[contains(@class, "property-details")]')

        # Extract URL and item_id with timeout
        url = await details.locator("xpath=a").get_attribute("href", timeout=5000)
        if not url:
            raise ValueError("No URL found")

        item_id = url.split("/")[-2]

        # Extract title (contains location info)
        try:
            title = await details.locator("xpath=a/h2").inner_text(timeout=5000)
            location = title.split(",")[0].strip() if "," in title else title.strip()
        except Exception as e:
            logger.warning(f"  Could not get title: {e}")
            title = "Unknown"
            location = None

        # Extract price
        price_meta = details.locator('xpath=meta[@itemprop="price"]')
        is_price_per_sqm = False

        if await price_meta.count() > 0:
            price_str = await price_meta.get_attribute("content", timeout=5000)
            price = float(price_str)

            # If price is less than 100, we can assume it's per m²
            if price < 100:
                is_price_per_sqm = True

        else:
            logger.warning(f"  No price found for {item_id}")
            price = 0.0

        data = {
            "url": f"https://www.nepremicnine.net{url}" if not url.startswith("http") else url,
            "price": price,
            "is_price_per_sqm": is_price_per_sqm,
            "location": location,
            "title": title,
        }

        return item_id, data

    except Exception as e:
        logger.error(f"Failed to parse listing {idx}: {e}", exc_info=True)
        raise