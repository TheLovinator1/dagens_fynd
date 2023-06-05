import json
import os
import sys
import uuid
from datetime import datetime
from email import utils
from pathlib import Path

import pytz
import requests
import requests_cache
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from loguru import logger

# The URL to the Discord webhook
discord_webhook_url: str = os.environ.get("DISCORD_WEBHOOK_URL", "")

# The URL to the Discord webhook where errors are sent
discord_webhook_url_error: str = os.environ.get("DISCORD_WEBHOOK_URL_ERROR", "")


def add_logger() -> None:
    """Add our own logger."""
    log_format: str = (
        "<green>{time:YYYY-MM-DD at HH:mm:ss}</green> <yellow>{extra[name]}</yellow>"
        " <cyan>{extra[price]}</cyan> <level>{message}</level>"
    )

    # Log to file
    logger.add(
        "logs/dagens_fynd.json",
        level="INFO",
        rotation="1GB",
        compression="zip",
        serialize=True,
    )

    # Log to stderr
    logger.add(
        sys.stderr,
        format=log_format,
        level="INFO",
        colorize=True,
        backtrace=True,
        diagnose=True,
    )


def save_to_json(data: dict) -> None:
    """Save the data to a json file.

    Args:
        data (dict): The data to save.
    """
    # Loop through the data and remove double spaces
    # For example, "1 190  kr" becomes "1 190 kr"
    for url, deal in data.items():
        for key, value in deal.items():
            if isinstance(value, str):
                data[url][key] = value.replace("  ", " ")

    # Create the json file if it doesn't exist
    if not Path.exists(Path("dagens_fynd.json")):
        with Path.open(Path("dagens_fynd.json"), "w", encoding="utf-8") as f:
            f.write("{}")

    # Save the data to the json file
    with Path.open(Path("dagens_fynd.json"), "w", encoding="utf-8") as f:
        f.write(json.dumps(data, indent=4, ensure_ascii=False))


def read_from_json() -> dict:
    """Read the data from the json file.

    Returns:
        dict: The data.
    """
    # Create the json file if it doesn't exist
    if not Path.exists(Path("dagens_fynd.json")):
        with Path.open(Path("dagens_fynd.json"), "w", encoding="utf-8") as f:
            f.write("{}")

    # Read the data from the json file
    with Path.open(Path("dagens_fynd.json"), "r", encoding="utf-8") as f:
        try:
            return json.loads(f.read())
        except json.decoder.JSONDecodeError as e:
            if e.pos == 0 and e.lineno == 1 and e.colno == 1:
                return {}

            logger.error("Could not parse json file, returning empty dict\n", error=e)
            return {}


def create_rss_feed() -> str:
    """Create a RSS feed.

    Returns:
        str: The RSS feed.
    """
    rss_feed = f"""<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
        <channel>
            <title>SweClockers - Dagens fynd</title>
            <link>https://www.sweclockers.com/dagensfynd</link>
            <description>Daily tech deals</description>
            <pubDate>{datetime.now(tz=pytz.timezone("Europe/Stockholm")).strftime("%a, %d %b %Y %H:%M:%S %z")}</pubDate>
            <managingEditor>tlovinator@gmail.com (Joakim Hellsén)</managingEditor>
            <webMaster>tlovinator@gmail.com (Joakim Hellsén)</webMaster>
            <category>SweClockers</category>
            <generator>https://github.com/TheLovinator1/dagens_fynd</generator>
            <docs>https://www.rssboard.org/rss-specification</docs>
            <ttl>60</ttl>
            <image>
                <url>https://www.sweclockers.com/gfx/apple-touch-icon.png</url>
                <title>SweClockers - Dagens fynd</title>
                <description>SweClockers logo</description>
                <link>https://www.sweclockers.com/dagensfynd</link>
            </image>
            <atom:link href="https://dagens-fynd.lovinator.space/rss" rel="self" type="application/rss+xml" />
        """

    # Get the data from our .json file
    data: dict = read_from_json()

    # Append the deals to the RSS feed
    for url, deal in data.items():
        rss_feed += f"""
        <item>
            <title>{deal["name"]}</title>
            <link>{url}</link>
            <description>{deal["vendor"]}</description>
            <category>{deal["category"]}</category>
            <pubDate>{deal["date"]}</pubDate>
            <guid isPermaLink="false">{deal["guid"]}</guid>
        </item>"""

    rss_feed += "\n</channel>\n</rss>"
    return rss_feed


def get_guid() -> str:
    """Get a unique identifier for a deal.

    Returns:
        str: The unique identifier.
    """
    our_uuid = str(uuid.uuid4())

    # Get the data from our .json file
    data: dict = read_from_json()

    # Rerun the function if our_uuid is already in the data otherwise return our_uuid
    return get_guid() if our_uuid in data else our_uuid


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
        date: str = utils.format_datetime(datetime.now(tz=pytz.timezone("Europe/Stockholm")))
        guid: str = get_guid()

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
    rss_feed: str = create_rss_feed()

    # Save the RSS feed to a file
    with Path.open(Path("dagens_fynd.rss"), "w", encoding="utf-8") as f:
        f.write(rss_feed)
