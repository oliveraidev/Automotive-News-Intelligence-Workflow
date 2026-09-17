"""Optional live RSS collection. Default output never replaces the audited snapshot."""
import argparse
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]

RSS_FEEDS = {
    "BYD News": "https://news.google.com/rss/search?q=BYD%20electric%20vehicle&hl=en-US&gl=US&ceid=US:en",
    "Geely News": "https://news.google.com/rss/search?q=Geely%20electric%20vehicle&hl=en-US&gl=US&ceid=US:en",
    "Zeekr News": "https://news.google.com/rss/search?q=Zeekr%20electric%20vehicle&hl=en-US&gl=US&ceid=US:en",
    "NIO News": "https://news.google.com/rss/search?q=NIO%20electric%20vehicle&hl=en-US&gl=US&ceid=US:en",
    "XPeng News": "https://news.google.com/rss/search?q=XPeng%20electric%20vehicle&hl=en-US&gl=US&ceid=US:en",
    "Li Auto News": "https://news.google.com/rss/search?q=Li%20Auto%20electric%20vehicle&hl=en-US&gl=US&ceid=US:en",
    "Xiaomi Auto News": "https://news.google.com/rss/search?q=Xiaomi%20EV&hl=en-US&gl=US&ceid=US:en",
}


def fetch_feed(feed_url):
    response = requests.get(feed_url, headers={"User-Agent": "AutomotiveNewsWorkflow/1.0"}, timeout=15)
    response.raise_for_status()  # requests performs normal TLS certificate validation.
    feed = feedparser.parse(response.content)
    if feed.get("bozo") or not feed.entries:
        raise ValueError("Malformed or empty feed; snapshot not safe to replace")
    return feed


def collect_news():
    articles, failures = [], []
    for source, feed_url in RSS_FEEDS.items():
        try:
            feed = fetch_feed(feed_url)
            collected_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
            for entry in feed.entries:
                publisher = entry.get("source", {})
                articles.append({
                    "source": source,  # query/feed name, not publisher
                    "feed_url": feed_url,
                    "publisher": publisher.get("title", ""),
                    "publisher_url": publisher.get("href", ""),  # source website, not article URL
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "published": entry.get("published", ""),
                    "summary": entry.get("summary", ""),
                    "collected_at": collected_at,
                })
            print(f"{source}: {len(feed.entries)} records")
        except (requests.RequestException, ValueError) as error:
            failures.append(source)
            print(f"Feed failed: {source}: {error}")
    if failures:
        raise RuntimeError(f"Collection incomplete ({len(failures)}/{len(RSS_FEEDS)} feeds failed). No output saved.")
    return pd.DataFrame(articles)


def save_collection(output_path, overwrite=False):
    output_path = Path(output_path)
    if not output_path.is_absolute():
        output_path = ROOT / output_path
    if output_path.resolve() == (ROOT / "data/raw/automotive_news.csv").resolve():
        raise ValueError("The bundled historical snapshot is protected. Choose a different output path.")
    if output_path.exists() and not overwrite:
        raise FileExistsError(f"{output_path} exists; select a new path or explicitly use --overwrite")
    df = collect_news()  # Any feed failure prevents writing, including partial data.
    if df.empty:
        raise ValueError("No records collected; no output saved")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8", lineterminator="\n")
    print(f"Saved {len(df)} records to {output_path}. Offline artifacts were not changed.")
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "data/raw/live/automotive_news.csv")
    parser.add_argument("--overwrite", action="store_true", help="Allow replacing a separate live output, never the bundled snapshot")
    args = parser.parse_args()
    save_collection(args.output, args.overwrite)
