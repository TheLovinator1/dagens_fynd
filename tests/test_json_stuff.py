from datetime import datetime
from email import utils
from pathlib import Path

import pytz

from dagens_fynd.guid import get_guid
from dagens_fynd.json_stuff import read_from_json, save_to_json


def test_save_to_json(tmp_path: Path) -> None:
    """Test the save_to_json function."""
    path: Path = Path(f"{tmp_path}/test.json")

    # Check that the file is not there
    assert not Path.is_file(path)

    # Save the data to the json file
    data: dict[str, dict[str, str]] = {
        "https://testurl.test": {
            "name": "test",
            "category": "test_category",
            "vendor": "test_vendor",
            "price": "1337  kr",
            "date": utils.format_datetime(datetime.now(tz=pytz.timezone("Europe/Stockholm"))),
            "guid": get_guid(),
        },
    }
    save_to_json(data, path)

    # Check that the file is there
    assert Path.is_file(path)

    # Check that the data is correct
    assert read_from_json(path) == data

    # Check that the data is correct when we add more data
    data["https://testurl2.test&hello"] = {
        "name": "test2",
        "category": "test_category2",
        "vendor": "test_vendor2",
        "price": "1337  kr2",
        "date": utils.format_datetime(datetime.now(tz=pytz.timezone("Europe/Stockholm"))),
        "guid": get_guid(),
    }

    # Save the data to the json file
    save_to_json(data, path)

    # Check that the data is correct
    assert read_from_json(path) == data
