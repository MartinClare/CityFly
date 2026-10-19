"""Map publisher domains Unwire cites onto RSS feeds we can crawl ourselves."""

from __future__ import annotations

# domain (no www) -> (display name, feed url)
OUTLET_FEEDS: dict[str, tuple[str, str]] = {
    "macrumors.com": ("MacRumors", "https://feeds.macrumors.com/MacRumors-All"),
    "9to5mac.com": ("9to5Mac", "https://9to5mac.com/feed/"),
    "theverge.com": ("The Verge", "https://www.theverge.com/rss/index.xml"),
    "wired.com": ("Wired", "https://www.wired.com/feed/rss"),
    "arstechnica.com": ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
    "pcmag.com": ("PCMag", "https://www.pcmag.com/feeds/rss/latest"),
    "engadget.com": ("Engadget", "https://www.engadget.com/rss.xml"),
    "techcrunch.com": ("TechCrunch", "https://techcrunch.com/feed/"),
    "theinformation.com": ("The Information", "https://www.theinformation.com/feed"),
    "bloomberg.com": ("Bloomberg Technology", "https://feeds.bloomberg.com/technology/news.rss"),
    "technologyreview.com": ("MIT Technology Review", "https://www.technologyreview.com/feed/"),
    "spectrum.ieee.org": ("IEEE Spectrum", "https://spectrum.ieee.org/feeds/feed.rss"),
    "restofworld.org": ("Rest of World", "https://restofworld.org/feed/latest/"),
    "blog.google": ("Google AI Blog", "https://blog.google/technology/ai/rss/"),
    "news.microsoft.com": ("Microsoft News", "https://news.microsoft.com/feed/"),
    "blogs.microsoft.com": ("Microsoft Blog", "https://blogs.microsoft.com/feed/"),
    "blogs.windows.com": ("Windows Experience Blog", "https://blogs.windows.com/feed/"),
    "github.blog": ("GitHub Blog", "https://github.blog/feed/"),
    "anthropic.com": ("Anthropic", "https://www.anthropic.com/rss.xml"),
    "openai.com": ("OpenAI", "https://openai.com/news/rss.xml"),
    "windowscentral.com": ("Windows Central", "https://www.windowscentral.com/feeds/all"),
    "tomshardware.com": ("Tom's Hardware", "https://www.tomshardware.com/feeds/all"),
    "theguardian.com": ("The Guardian Technology", "https://www.theguardian.com/uk/technology/rss"),
    "bbc.com": ("BBC Technology", "https://feeds.bbci.co.uk/news/technology/rss.xml"),
    "bbc.co.uk": ("BBC Technology", "https://feeds.bbci.co.uk/news/technology/rss.xml"),
    "rthk.hk": ("香港電台", "https://rthk.hk/rthk/news/rss/c_expressnews_clocal.xml"),
    "news.mingpao.com": ("明報", "https://news.mingpao.com/rss/pns/s00004.xml"),
}


def lookup_feed(domain: str) -> tuple[str, str] | None:
    host = (domain or "").lower().strip(".")
    if host.startswith("www."):
        host = host[4:]
    if host in OUTLET_FEEDS:
        return OUTLET_FEEDS[host]
    parts = host.split(".")
    if len(parts) > 2:
        parent = ".".join(parts[-2:])
        if parent in OUTLET_FEEDS:
            return OUTLET_FEEDS[parent]
    return None
