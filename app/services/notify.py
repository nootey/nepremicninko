import requests
from app.core.config import config
from app.core.logger import AppLogger

logger = AppLogger(name="discord").get_logger()


def send_discord_embed(listing_data):

    # Determine embed color and title based on type
    if listing_data["type"] == "price_change":
        color = 16776960  # Yellow for price changes
        title = f"💰 Price Change - {listing_data['item_id']}"

        # Format price based on whether it's per m²
        if listing_data.get("is_price_per_sqm"):
            price_field_value = f"~~€{listing_data['old_price']:,.2f}/m²~~ → **€{listing_data['price']:,.2f}/m²**"
        else:
            price_field_value = f"~~€{listing_data['old_price']:,.2f}~~ → **€{listing_data['price']:,.2f}**"
    else:
        color = 5763719  # Green for new listings
        title = f"🏡 New Listing - {listing_data['item_id']}"

        # Format price based on whether it's per m²
        if listing_data.get("is_price_per_sqm"):
            price_field_value = f"€{listing_data['price']:,.2f}/m²"
        else:
            price_field_value = f"€{listing_data['price']:,.2f}"

    fields = [
        {
            "name": "💵 Price",
            "value": price_field_value,
            "inline": True
        },
    ]

    # Add location if available
    if listing_data.get("location"):
        fields.append({
            "name": "📍 Location",
            "value": listing_data["location"],
            "inline": True
        })

    embed = {
        "title": title,
        "url": listing_data["url"],
        "color": color,
        "fields": fields,
        "footer": {
            "text": "nepremicninko",
        },
    }

    payload = {"embeds": [embed]}
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(config.DISCORD_WEBHOOK_URL, json=payload, headers=headers)

        if response.status_code not in (200, 204):
            logger.warning(
                f"Failed to send embed to Discord: {response.status_code} - {response.text}"
            )
        else:
            logger.info(f"Discord embed sent successfully for {listing_data['item_id']}")

    except Exception as e:
        logger.exception(f"Exception occurred while sending embed to Discord: {e}")


def send_discord_notifications(listings):
    if not config.DISCORD_WEBHOOK_URL:
        logger.warning("Discord webhook URL not configured, skipping notifications")
        return

    logger.info(f"Sending {len(listings)} notifications to Discord")

    for listing in listings:
        send_discord_embed(listing)