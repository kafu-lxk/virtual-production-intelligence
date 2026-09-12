import json
import re
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import quote

import feedparser


ROOT = Path(__file__).parent
DATA_FILE = ROOT / "data" / "articles.json"

KEYWORDS = [
    "virtual production",
    "in-camera VFX",
    "ICVFX",
    "screen process",
    "LED volume",
    "LED wall",
    "XR stage",
    "virtual studio",
    "camera tracking",
    "real-time rendering",
    "Unreal Engine virtual production",
    "virtual production stage",
]

TECHNOLOGIES = [
    "Unreal Engine",
    "Disguise",
    "Brompton",
    "ROE Visual",
    "Mo-Sys",
    "stYpe",
    "Vicon",
    "Pixotope",
    "Aximmetry",
    "NVIDIA",
    "Notch",
    "Sony",
    "ARRI",
    "RED",
]

CATEGORIES = {
    "Virtual Production": [
        "virtual production",
        "virtual studio",
        "virtual production stage",
    ],
    "In-Camera VFX": [
        "in-camera vfx",
        "icvfx",
        "in camera vfx",
    ],
    "Screen Process": [
        "screen process",
        "rear projection",
        "front projection",
        "projection",
    ],
    "LED Volume": [
        "led volume",
        "led wall",
        "led stage",
        "led screen",
    ],
    "Camera Tracking": [
        "camera tracking",
        "camera track",
        "lens tracking",
        "camera tracking system",
    ],
    "Real-time Rendering": [
        "real-time rendering",
        "real time rendering",
        "unreal engine",
        "realtime rendering",
    ],
}


def clean_text(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def classify(text):
    text = text.lower()

    categories = []

    for category, words in CATEGORIES.items():
        if any(word.lower() in text for word in words):
            categories.append(category)

    technologies = [
        tech for tech in TECHNOLOGIES
        if tech.lower() in text
    ]

    if not categories:
        categories = ["Virtual Production"]

    return categories, technologies


def source_name(entry):
    if getattr(entry, "source", None):
        return clean_text(
            getattr(entry.source, "title", "")
        )

    if getattr(entry, "author", None):
        return clean_text(entry.author)

    return "Unknown source"


def published_date(entry):
    value = getattr(entry, "published", "")
    if value:
        return clean_text(value)

    value = getattr(entry, "updated", "")
    if value:
        return clean_text(value)

    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def make_google_news_url(keyword):
    query = quote(keyword)
    return (
        "https://news.google.com/rss/search?"
        f"q={query}&hl=en-US&gl=US&ceid=US:en"
    )


def load_articles():
    if not DATA_FILE.exists():
        return []

    try:
        return json.loads(
            DATA_FILE.read_text(encoding="utf-8")
        )
    except Exception:
        return []


def save_articles(articles):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    DATA_FILE.write_text(
        json.dumps(
            articles,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


def collect():
    existing = load_articles()

    existing_urls = {
        item.get("url", "").strip()
        for item in existing
    }

    new_articles = []

    for keyword in KEYWORDS:
        feed_url = make_google_news_url(keyword)

        try:
            feed = feedparser.parse(feed_url)
        except Exception as e:
            print(f"Feed error: {keyword} / {e}")
            continue

        for entry in feed.entries:
            url = getattr(entry, "link", "").strip()

            if not url:
                continue

            if url in existing_urls:
                continue

            title = clean_text(
                getattr(entry, "title", "")
            )

            description = clean_text(
                getattr(entry, "description", "")
            )

            text = f"{title} {description}"

            categories, technologies = classify(text)

            article = {
                "title": title,
                "date": published_date(entry),
                "country": "Worldwide",
                "source": source_name(entry),
                "categories": categories,
                "technologies": technologies,
                "summary": (
                    "公開RSSで検出された関連情報。"
                    "詳細は元記事を確認してください。"
                ),
                "url": url,
                "collected_at": datetime.now(
                    timezone.utc
                ).isoformat(),
                "search_keyword": keyword
            }

            new_articles.append(article)
            existing_urls.add(url)

    # 新しい記事を先頭に追加
    articles = new_articles + existing

    # 最大3000件まで保存
    articles = articles[:3000]

    save_articles(articles)

    print(
        f"Collected: {len(new_articles)} new articles"
    )
    print(
        f"Total: {len(articles)} articles"
    )


if __name__ == "__main__":
    collect()
