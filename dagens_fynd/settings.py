import os

import pytz
from loguru import logger

# The webhook where we send errors to
discord_webhook_url: str = os.environ.get("DISCORD_WEBHOOK_URL", "")
if discord_webhook_url == "https://discordapp.com/api/webhooks/123456789/abcdefghijklmnopqrstuvwxyz":
    discord_webhook_url = ""
if discord_webhook_url:
    logger.info(f"Will send errors to {discord_webhook_url}")

# The timezone to use for dates
timezone_env: str = os.environ.get("TIMEZONE", "Europe/Stockholm")
try:
    timezone = pytz.timezone(timezone_env)
except pytz.exceptions.UnknownTimeZoneError:
    logger.critical("Unknown timezone, defaulting to Europe/Stockholm")
    timezone = pytz.timezone("Europe/Stockholm")
logger.info(f"Using timezone {timezone}")
