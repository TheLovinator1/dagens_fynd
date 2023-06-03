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
    """Add our own logger.

    This function is called in dagens_fynd/main.py.
    """
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


def save_deal(url: str, name: str, category: str, vendor: str, price: str) -> None:
    """Save the deal to a csv file.

    Args:
        url (str): The URL to the deal.
        name (str): The name of the deal.
        category (str): The category of the deal.
        vendor (str): The vendor of the deal.
        price (str): The price of the deal.
    """
    # Create the csv file if it doesn't exist
    if not Path.exists(Path("dagens_fynd.csv")):
        with Path.open(Path("dagens_fynd.csv"), "w", encoding="utf-8") as f:
            f.write("URL,Name,Category,Vendor,Price\n")

    # Save the deal to the csv file
    with Path.open(Path("dagens_fynd.csv"), "a", encoding="utf-8") as f:
        f.write(f"{url},{name},{category},{vendor},{price}\n")


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
        try:
            with Path.open("dagens_fynd.csv", "r", encoding="utf-8") as f:
                if f"{url},{name},{category},{vendor},{price}" in f.read():
                    logger.info("Deal already saved, skipping")
                    continue
        except FileNotFoundError:
            logger.debug("No csv file found")

        # Save the deal
        save_deal(url, name, category, vendor, price)


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
