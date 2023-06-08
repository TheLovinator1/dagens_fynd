from dagens_fynd.rss_feed import create_rss_feed


def test_create_rss_feed() -> None:
    """Test the create_rss_feed function."""
    response: str = create_rss_feed({})

    assert len(response) == 1176  # noqa: PLR2004

    # Check that the RSS feed starts with the correct string
    assert response.startswith("""<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
        <channel>
            <title>SweClockers - Dagens fynd</title>
            <link>https://www.sweclockers.com/dagensfynd</link>
            <description>Daily tech deals</description>
            <pubDate>""")
