import uuid

from dagens_fynd.json_stuff import read_from_json


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
