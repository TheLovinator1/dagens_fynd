import json
from pathlib import Path

from loguru import logger


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
