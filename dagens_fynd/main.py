import json
import os
import sys
from functools import lru_cache
from pathlib import Path

import requests
import requests_cache
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from loguru import logger


class Settings:
    """Settings for the application.

    The settings are loaded from environment variables. If an environment variable is not set, a default value is used.
    The settings are cached using the lru_cache decorator, so they are only loaded once.
    """

    # The URL to the daily deals page, should probably not be changed
    url: str = os.environ.get("URL", "https://www.sweclockers.com/dagensfynd")

    # The URL to the Discord webhook
    discord_webhook_url: str = os.environ.get("DISCORD_WEBHOOK_URL", "")

    # The URL to the Discord webhook where errors are sent
    discord_webhook_url_error: str = os.environ.get("DISCORD_WEBHOOK_URL_ERROR", "")


@lru_cache
def get_settings() -> Settings:
    """Get the settings.

    This function is cached using the lru_cache decorator, so the settings are only loaded once.

    Returns:
        Settings: The settings.
    """
    return Settings()


def add_logger() -> None:
    """Add our own logger."""
    log_format: str = "<green>{time:YYYY-MM-DD at HH:mm:ss}</green> <level>{level: <5}</level> <white>{message}</white>"

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
        return json.loads(f.read())


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

        logger.info(f"Deal found:\nName: {name}\nCategory: {category}\nVendor: {vendor}\nPrice: {price}\nURL: {url}\n")

        # Check if the deal is already saved
        data: dict = read_from_json()
        if url in data:
            logger.info("Deal already saved, skipping\n")
            continue

        # Save the deal to a json file
        data: dict = read_from_json()
        data[url] = {
            "name": name,
            "category": category,
            "vendor": vendor,
            "price": price,
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
