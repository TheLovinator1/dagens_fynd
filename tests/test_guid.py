from uuid import UUID

from dagens_fynd.guid import get_guid


def test_get_guid() -> None:
    """Test the get_guid function."""
    response: str = get_guid()

    assert len(response) == 36  # noqa: PLR2004

    # Check that the response is a valid UUID
    assert UUID(response)
