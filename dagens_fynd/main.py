from datetime import datetime
from email import utils
from pathlib import Path
from xml.sax.saxutils import escape

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
from dagens_fynd.settings import discord_webhook_url, timezone


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

        # Escape the strings so we don't get any errors when parsing the xml
        url = escape(url.strip())
        name = escape(name.strip())
        category = escape(category.strip())
        vendor = escape(vendor.strip())
        price = escape(price.strip())
        date = escape(date.strip())
        guid = escape(guid.strip())

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
        }
        save_to_json(data)


def send_error(msg: str) -> None:
    """Send an error message to Discord."""
    logger.error(msg)
    if not discord_webhook_url:
        return

    webhook = DiscordWebhook(url=discord_webhook_url, content=msg)
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
