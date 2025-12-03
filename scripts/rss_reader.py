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

today = datetime.now().strftime("%Y-%m-%d")

# -------------------------
# 加载已抓取条目
# -------------------------
if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE, "r", encoding="utf-8") as f:
        try:
            seen = json.load(f)
        except:
            seen = []
else:
    seen = []

# 生成已有 uid 集合，防止重复
seen_uids = set(entry.get("uid") for entry in seen if "uid" in entry)

# -------------------------
# 抓取新条目
# -------------------------
new_entries = []

for feed_url in RSS_FEEDS:
    print(f"Parsing feed: {feed_url}")
    feed = feedparser.parse(feed_url)
    source_name = feed.feed.get("title", "Unknown Source")
    
    for entry in feed.entries:
        uid = entry.get("id") or entry.get("link")
        if not uid:
            continue
        if uid in seen_uids:
            continue  # 已抓取过
        
        paper = {
            "uid": uid,
            "source": source_name,
            "title": entry.get("title", "No title"),
            "link": entry.get("link", ""),
            "summary": entry.get("summary", "").strip(),
            "date": today
        }
        new_entries.append(paper)
        seen_uids.add(uid)

# -------------------------
# 更新 seen.json
# -------------------------
if new_entries:
    print(f"新增条目: {len(new_entries)}")
    seen.extend(new_entries)
    os.makedirs(os.path.dirname(SEEN_FILE), exist_ok=True)
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(seen, f, indent=2, ensure_ascii=False)
else:
    print("今天没有新增条目。")

# -------------------------
# 可选：更新 Markdown 文件（简易版）
# -------------------------
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(f"# Daily Paper Digest — {today}\n")
    f.write(f"今日新增论文：{len(new_entries)}\n")
    f.write(f"已累计收录：{len(seen)} 篇\n")
    f.write("---\n\n")
    if new_entries:
        for p in new_entries:
            f.write(f"- **{p['title']}**  \n")
            f.write(f"  🔗 {p['link']}\n")
            if p['summary']:
                f.write(f"  📝 {p['summary']}\n")
            f.write("\n")
    else:
        f.write("今天没有新增内容。\n")

print("RSS抓取与 seen.json 更新完成。")
