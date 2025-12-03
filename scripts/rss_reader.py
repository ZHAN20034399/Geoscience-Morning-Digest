# rss_reader.py
import feedparser
import json
import os
from datetime import datetime

RSS_FEEDS = [
    "http://www.nature.com/nature/current_issue/rss",
    "https://www.science.org/action/showFeed?type=etoc&feed=rss&jc=science",
    "https://www.science.org/action/showFeed?type=etoc&feed=rss&jc=sciadv",
    "https://www.nature.com/ngeo.rss",
    "https://www.nature.com/ncomms.rss",
    "https://www.nature.com/natrevearthenviron.rss",
    "https://www.pnas.org/action/showFeed?type=searchTopic&taxonomyCode=topic&tagCode=earth-sci",
    "https://www.annualreviews.org/rss/content/journals/earth/latestarticles?fmt=rss",
    "https://rss.sciencedirect.com/publication/science/00128252",
    "https://rss.sciencedirect.com/publication/science/0012821X",
    "https://agupubs.onlinelibrary.wiley.com/feed/19448007/most-recent",
    "https://agupubs.onlinelibrary.wiley.com/feed/21699356/most-recent",
    "https://agupubs.onlinelibrary.wiley.com/feed/15252027/most-recent",
    "https://rss.sciencedirect.com/publication/science/00167037"
]

SEEN_FILE = "state/seen.json"

def load_seen():
    if not os.path.exists(SEEN_FILE):
        return {}
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # 用 uid 做 key，快速去重
            return {p.get("uid"): p for p in data if "uid" in p}
    except:
        return {}

def save_seen(seen_dict):
    os.makedirs(os.path.dirname(SEEN_FILE), exist_ok=True)
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen_dict.values()), f, ensure_ascii=False, indent=2)

def fetch_feeds():
    today = datetime.now().strftime("%Y-%m-%d")
    seen = load_seen()
    new_count = 0

    for url in RSS_FEEDS:
        feed = feedparser.parse(url)
        source_name = feed.feed.get("title", "未知来源")
        for entry in feed.entries:
            uid = entry.get("id") or entry.get("link")
            if not uid or uid in seen:
                continue
            paper = {
                "uid": uid,
                "title": entry.get("title", "未知标题"),
                "link": entry.get("link", ""),
                "summary": entry.get("summary", ""),
                "source": source_name,
                "authors": [a.get("name") for a in entry.get("authors", [])] if entry.get("authors") else [],
                "date": today
            }
            seen[uid] = paper
            new_count += 1

    save_seen(seen)
    print(f"抓取完成，新文章 {new_count} 条，总计 {len(seen)} 条")

if __name__ == "__main__":
    fetch_feeds()
