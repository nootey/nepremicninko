import re
from logging import Logger

from playwright.async_api import Locator, Page


async def parse_page(browser_page: Page, logger: Logger) -> tuple[dict, bool]:
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
    logger.info("Starting to parse listings ...")

    # Loop through all listings
    for idx, result in enumerate(results):
        logger.info(f"Processing listing {idx + 1}/{len(results)} ...")
        try:
            item_id, data = await parse_result(result, idx, logger)
            extracted_data[item_id] = data
        except Exception as e:
            logger.warning(f"✗ Error parsing listing {idx + 1}: {e}")
            continue  # skip to next listing instead of crashing

    # Check if there's a next page button
    next_page_xpath = """xpath=//*[@id='pagination']/ul/li[contains(@class, 'paging_next')]"""
    more_pages = await browser_page.locator(next_page_xpath).count() > 0

    logger.info(f"Parsing finished. Extracted {len(extracted_data)} listings. More pages: {more_pages}")

    return extracted_data, more_pages


async def parse_result(item: Locator, idx: int, logger: Logger) -> tuple[str, dict]:
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

        if await price_meta.count() > 0:
            price_str = await price_meta.get_attribute("content", timeout=5000)
            price = float(price_str)
        else:
            logger.warning(f"  No price found for {item_id}")
            price = 0.0

        # Extract size
        size_sqm = None
        try:
            property_list = details.locator('xpath=.//ul[@itemprop="disambiguatingDescription"]')
            if await property_list.count() > 0:
                list_text = await property_list.inner_text(timeout=5000)

                size_match = re.search(r"(\d+(?:[.,]\d+)?)\s*m", list_text, re.IGNORECASE)
                if size_match:
                    size_str = size_match.group(1).replace(",", ".")
                    size_sqm = float(size_str)
                else:
                    logger.warning(f"  No size match found in: {list_text}")
            else:
                logger.warning(f"  No property list found for {item_id}")
        except Exception as e:
            logger.error(f"  Could not extract size: {e}")

        data = {
            "url": f"https://www.nepremicnine.net{url}" if not url.startswith("http") else url,
            "price": price,
            "location": location,
            "title": title,
            "size_sqm": size_sqm,
        }

        return item_id, data

    except Exception as e:
        logger.error(f"Failed to parse listing {idx}: {e}", exc_info=True)
        raise
