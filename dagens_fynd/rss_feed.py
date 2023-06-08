from datetime import datetime

import pytz


def create_rss_feed(data: dict) -> str:
    """Create a RSS feed.

    Args:
        data (dict): The deals to add to the RSS feed.

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

    # Append the deals to the RSS feed
    if data:
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
