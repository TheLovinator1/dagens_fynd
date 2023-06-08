import os
from datetime import datetime
from email import utils
from pathlib import Path

import pytz
import requests
import requests_cache
from bs4 import BeautifulSoup
from discord_webhook import DiscordWebhook
from dotenv import load_dotenv
from loguru import logger

from dagens_fynd.guid import get_guid
from dagens_fynd.json_stuff import read_from_json, save_to_json
from dagens_fynd.logging import add_logger
from dagens_fynd.rss_feed import create_rss_feed

# The URL to the Discord webhook
discord_webhook_url: str = os.environ.get("DISCORD_WEBHOOK_URL", "")
if discord_webhook_url == "https://discordapp.com/api/webhooks/123456789/abcdefghijklmnopqrstuvwxyz":
    discord_webhook_url = ""

# The URL to the Discord webhook where errors are sent
discord_webhook_url_error: str = os.environ.get("DISCORD_WEBHOOK_URL_ERROR", "")
if discord_webhook_url_error == "https://discordapp.com/api/webhooks/123456789/abcdefghijklmnopqrstuvwxyz":
    discord_webhook_url_error = ""

# The timezone to use for dates
timezone_env: str = os.environ.get("TIMEZONE", "Europe/Stockholm")
try:
    timezone = pytz.timezone(timezone_env)
except pytz.exceptions.UnknownTimeZoneError:
    logger.critical("Unknown timezone, defaulting to Europe/Stockholm")
    timezone = pytz.timezone("Europe/Stockholm")


def main() -> None:
    """Get the daily deals from SweClockers and create a RSS feed."""
    try:
        response: requests.Response = requests.get("https://www.sweclockers.com/dagensfynd", timeout=15)
    except requests.exceptions.RequestException as e:
        msg: str = f"There was an ambiguous exception that occurred while handling the request:\n{e}"
        logger.critical(msg)
        return

    if not response.ok:
        logger.critical("Response was not ok, exiting\n", response=response)
        return

    soup = BeautifulSoup(response.text, "html.parser")
    if not soup:
        logger.critical("Could not parse response, exiting\n", response=response)
        return

    # Get the daily deals
    for deal in soup.find_all("div", class_="tips-row"):
        if not deal:
            logger.error("Deal was empty, skipping")
            continue

        # Get the deal information
        url: str = deal.find("a", class_="cell-product")["href"] or "Unknown"  # type: ignore  # noqa: PGH003
        name: str = deal.find("div", class_="col-product-inner-wrapper").text or "Unknown"  # type: ignore  # noqa: PGH003, E501
        category: str = deal.find("div", class_="col-category").text or "Unknown"  # type: ignore  # noqa: PGH003
        vendor: str = deal.find("div", class_="col-vendor").text or "Unknown"  # type: ignore  # noqa: PGH003
        price: str = deal.find("div", class_="col-price").text or "Unknown"  # type: ignore  # noqa: PGH003
        date: str = utils.format_datetime(datetime.now(tz=timezone))
        guid: str = get_guid()
        sent_to_discord: bool = False
        sent_to_discord_date: str = ""

        # Check if the deal is already saved
        data: dict = read_from_json()
        if url in data:
            logger.info(
                "Deal already in json file, skipping",
                url=url,
                name=name,
                category=category,
                vendor=vendor,
                price=price,
                date=date,
                guid=guid,
                sent_to_discord=sent_to_discord,
                sent_to_discord_date=sent_to_discord_date,
            )
            continue

        logger.info(
            f"Deal found! {name} for {price}",
            url=url,
            name=name,
            category=category,
            vendor=vendor,
            price=price,
            date=date,
            guid=guid,
            sent_to_discord=sent_to_discord,
            sent_to_discord_date=sent_to_discord_date,
        )

        # Save the deal to a json file
        data: dict = read_from_json()
        data[url] = {
            "name": name,
            "category": category,
            "vendor": vendor,
            "price": price,
            "date": date,
            "guid": guid,
            "sent_to_discord": sent_to_discord,
            "sent_to_discord_date": sent_to_discord_date,
        }
        save_to_json(data)


def send_error(msg: str) -> None:
    """Send an error message to Discord."""
    logger.error(msg)
    if not discord_webhook_url_error:
        return

    webhook = DiscordWebhook(url=discord_webhook_url_error, content=msg)
    response: requests.Response = webhook.execute()
    if response.ok:
        logger.info(f"Sent error to Discord: {msg}")
    else:
        logger.error(f"Could not send error to Discord: {msg}", response=response)


if __name__ == "__main__":
    # Remove the default logger
    logger.remove()

    # Add our own logger
    add_logger()

    # Load the environment variables from the .env file
    load_dotenv()

    # Cache the response for 1 hour, so we don't spam the site while testing
    requests_cache.install_cache("dagens_fynd_cache", backend="sqlite", expire_after=3600)

    # Start checking for deals
    main()

    # Create the RSS feed
    data: dict = read_from_json()
    rss_feed: str = create_rss_feed(data)

    # Save the RSS feed to a file
    with Path.open(Path("dagens_fynd.rss"), "w", encoding="utf-8") as f:
        f.write(rss_feed)

    # Loop through the deals and send unsent deals to Discord
    for url, deal in data.items():
        if not discord_webhook_url:
            continue

        if deal["sent_to_discord"] is True:
            continue

        deal_msg: str = f"New deal: **{deal['name']}** for {deal['price']}\n{url}"
        webhook = DiscordWebhook(url=discord_webhook_url, content=deal_msg)
        response: requests.Response = webhook.execute()
        if response.ok:
            logger.info("Sent deal to Discord", url=url, name=deal["name"], price=deal["price"], response=response)
            deal["sent_to_discord"] = True
            deal["sent_to_discord_date"] = utils.format_datetime(datetime.now(tz=timezone))
            data[url] = deal
            save_to_json(data)
        else:
            send_error(f"Could not send deal to Discord: {deal_msg}")
            logger.error("Could not send deal to Discord", url=url, response=response)
