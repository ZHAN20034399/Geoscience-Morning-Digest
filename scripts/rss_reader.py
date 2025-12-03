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
OUTPUT_FILE = "output/daily.md"


# -------------------------
# Load / Save Seen IDs
# -------------------------

def load_seen():
    print("Loading seen.json...")
    if not os.path.exists(SEEN_FILE):
        print("seen.json does not exist, starting fresh.")
        return set()
    try:
        with open(SEEN_FILE, "r") as f:
            data = f.read().strip()
            if not data:
                print("seen.json is empty.")
                return set()
            seen = set(json.loads(data))
            print(f"Loaded {len(seen)} seen entries.")
            return seen
    except Exception as e:
        print(f"Error reading seen.json: {e}")
        return set()


def save_seen(seen):
    print(f"Saving seen.json... (total {len(seen)} IDs)")
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f, indent=2)


# -------------------------
# Fetch New RSS Entries
# -------------------------

def fetch_new_entries():
    print("Fetching RSS feeds...")
    seen = load_seen()
    new_entries = []
    total_fetched = 0

    for url in RSS_FEEDS:
        print(f"\nParsing feed: {url}")
        feed = feedparser.parse(url)
        source_name = feed.feed.get("title", "Unknown Source")

        entries = feed.entries
        print(f"  -> Found {len(entries)} entries from {source_name}")
        total_fetched += len(entries)

        for entry in entries:
            uid = entry.get("id") or entry.get("link")
            if not uid:
                continue

            if uid in seen:
                continue  # 已经抓过

            new_entries.append({
                "source": source_name,
                "title": entry.get("title", "No title"),
                "link": entry.get("link", ""),
                "summary": entry.get("summary", "").strip()
            })

            seen.add(uid)

    print(f"\n=== Summary ===")
    print(f"Total entries fetched: {total_fetched}")
    print(f"New entries found: {len(new_entries)}")

    save_seen(seen)
    return new_entries, len(seen)   # 返回累计数量


# -------------------------
# Group by Source
# -------------------------

def group_by_source(entries):
    groups = {}
    for item in entries:
        source = item["source"]
        groups.setdefault(source, []).append(item)
    return groups


# -------------------------
# Write Markdown with Stats
# -------------------------

def write_markdown(entries, total_seen):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    new_count = len(entries)

    print(f"Writing markdown to {OUTPUT_FILE} ...")

    md = ""
    md += f"# Daily Paper Digest — {today}\n"
    md += f"今日新增论文：{new_count}\n"
    md += f"已累计收录：{total_seen} 篇\n\n"
    md += "---\n\n"

    if not entries:
        md += "今天没有新增内容。\n"
        print("No new entries today.")
    else:
        grouped = group_by_source(entries)
        print(f"Writing {len(entries)} entries grouped into {len(grouped)} sources.")

        for source, items in grouped.items():
            md += f"## {source}\n\n"
            for item in items:
                md += f"- **{item['title']}**  \n"
                md += f"  🔗 {item['link']}\n"
                if item['summary']:
                    clean_sum = item["summary"].replace("\n", " ").strip()
                    md += f"  📝 {clean_sum}\n"
                md += "\n"

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(md)

    print("Markdown file updated.")


# -------------------------
# Main
# -------------------------

if __name__ == "__main__":
    entries, total_seen = fetch_new_entries()
    write_markdown(entries, total_seen)
    print("\nDone.")
