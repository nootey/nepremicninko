import time
from logging import Logger

import requests

from app.core.config import config


def send_discord_notifications(listings, logger: Logger):
    if not config.discord.webhook_url:
        logger.warning("Discord webhook URL not configured, skipping notifications")
        return

    logger.info(f"Sending {len(listings)} notifications to Discord")

    batch_size = 10
    for i in range(0, len(listings), batch_size):
        batch = listings[i : i + batch_size]
        send_discord_batch(batch, logger)

        # Small delay between batches to avoid rate limits
        if i + batch_size < len(listings):
            time.sleep(1)


def send_discord_batch(listings, logger: Logger):
    """Send multiple listings as embeds in a single message."""
    embeds = []

    for listing_data in listings:
        # Determine embed color and title based on type
        if listing_data["type"] == "price_change":
            color = 16776960
            title = f"💰 Price Change - {listing_data['item_id']}"

            price_field_value = f"~~€{listing_data['old_price']:,.2f}~~ → **€{listing_data['price']:,.2f}**"
        else:
            color = 5763719
            title = f"🏡 New Listing - {listing_data['item_id']}"

            price_field_value = f"€{listing_data['price']:,.2f}"

        listing_type = listing_data.get("listing_type", "selling")
        type_icon = "🏷️" if listing_type == "selling" else "🔑"
        type_text = "Selling" if listing_type == "selling" else "Renting"
        fields = [
            {"name": f"{type_icon} Type", "value": type_text, "inline": True},
            {"name": "💵 Price", "value": price_field_value, "inline": True},
        ]

        if listing_data.get("size_sqm"):
            fields.append({"name": "📏 Size", "value": f"{listing_data['size_sqm']} m²", "inline": True})

        if listing_type == "selling" and listing_data.get("size_sqm"):
            price_per_sqm = listing_data["price"] / listing_data["size_sqm"]
            fields.append({"name": "📐 Price/m²", "value": f"€{price_per_sqm:,.2f}", "inline": True})

        if listing_data.get("location"):
            fields.append({"name": "📍 Location", "value": listing_data["location"], "inline": True})

        embeds.append(
            {
                "title": title,
                "url": listing_data["url"],
                "color": color,
                "fields": fields,
                "footer": {"text": "nepremicninko"},
            }
        )

    payload = {"embeds": embeds}
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(config.discord.webhook_url, json=payload, headers=headers)

        if response.status_code not in (200, 204):
            logger.warning(f"Failed to send batch to Discord: {response.status_code} - {response.text}")
        else:
            logger.info(f"Discord batch sent successfully ({len(embeds)} listings)")

    except Exception as e:
        logger.exception(f"Exception occurred while sending batch to Discord: {e}")


def send_discord_error(error_message: str, logger: Logger, page_url: str = None):
    description = f"```\n{error_message}\n```"

    fields = []
    if page_url:
        fields.append({"name": "🔗 URL", "value": page_url, "inline": False})

    embed = {
        "title": "⚠️ Scraper Error",
        "description": description,
        "color": 15158332,
        "fields": fields,
        "footer": {
            "text": "nepremicninko",
        },
    }

    payload = {"embeds": [embed]}
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(config.discord.webhook_url, json=payload, headers=headers)

        if response.status_code not in (200, 204):
            logger.warning(f"Failed to send error embed to Discord: {response.status_code} - {response.text}")
        else:
            logger.info("Discord error embed sent successfully")

    except Exception as e:
        logger.exception(f"Exception occurred while sending error embed to Discord: {e}")
