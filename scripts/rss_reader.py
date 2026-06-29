import feedparser
import json
import os
from datetime import datetime, timezone
import time

# -------------------
# Configuration
# -------------------
SEEN_JSON_PATH = "state/seen.json"
PAPERS_JSON_PATH = "output/papers.json"

# 地球科学相关 RSS 源列表
RSS_URLS = [
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
    "https://agupubs.onlinelibrary.wiley.com/feed/15252027/most-recent", 
    "https://agupubs.onlinelibrary.wiley.com/feed/21699356/most-recent",
    "https://rss.sciencedirect.com/publication/science/00167037",
    "https://www.nature.com/natrevearthenviron.rss",
    "https://pubs.geoscienceworld.org/rss/site_119/60.xml",
    "https://pubs.geoscienceworld.org/rss/site_69/35.xml",
    "https://pubs.geoscienceworld.org/rss/site_65/33.xml"
]

def load_seen_papers():
    """Load the list of seen paper IDs from a JSON file."""
    if os.path.exists(SEEN_JSON_PATH):
        with open(SEEN_JSON_PATH, "r", encoding="utf-8") as f:
            try:
                # 尝试加载整个列表，然后提取 ID 集合
                seen_list = json.load(f)
                return {p.get("id") for p in seen_list if isinstance(p, dict) and p.get("id")}, seen_list
            except json.JSONDecodeError:
                print("Warning: seen.json is corrupted or empty. Starting fresh.")
                return set(), []
    return set(), []

def save_seen_papers(seen_list):
    """Save the updated list of seen papers to a JSON file."""
    os.makedirs(os.path.dirname(SEEN_JSON_PATH), exist_ok=True)
    with open(SEEN_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(seen_list, f, indent=2, ensure_ascii=False)

def parse_date(entry):
    """
    Attempts to parse the publication date from the RSS entry.
    
    Prioritizes published_parsed/updated_parsed, falls back to today's date.
    Returns date in 'YYYY-MM-DD' format.
    """
    try:
        # Use updated_parsed or published_parsed (struct_time format)
        date_struct = entry.get('updated_parsed') or entry.get('published_parsed')
        if date_struct:
            # Convert struct_time to datetime object and then format
            date_dt = datetime(*date_struct[:6], tzinfo=timezone.utc)
            return date_dt.strftime("%Y-%m-%d")
    except Exception as e:
        # If parsing fails, print a warning and fall back to today
        print(f"Warning: Failed to parse date for entry '{entry.get('title', 'Unknown')}'. Error: {e}")
        pass

    # Fallback to today's date (Local time zone)
    return datetime.now().strftime("%Y-%m-%d")

def fetch_new_entries():
    """Fetches new entries from all RSS feeds."""
    
    seen_ids, seen_list = load_seen_papers()
    new_entries_list = []
    
    print(f"Loaded {len(seen_ids)} existing paper IDs.")
    
    for url in RSS_URLS:
        print(f"解析 RSS: {url}")
        try:
            feed = feedparser.parse(url, request_headers={
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) RSS-Mailer/1.0"
})
            source_name = feed.feed.get('title', url.split('/')[2])
            
            for entry in feed.entries:
                # Use 'id' or 'link' as a unique identifier (ID is usually better)
                uid = entry.get("id") or entry.get("link")
                
                if not uid:
                    continue # Skip entries without a usable ID
                
                # 1. 检查是否已存在
                if uid in seen_ids:
                    continue # Skip if already seen

                # 2. 如果是新文章，则记录
                
                # Clean up summary (remove HTML/CDATA tags often left by feedparser)
                summary_raw = entry.get('summary', entry.get('content', [{}])[0].get('value'))
                summary_text = summary_raw.replace('<p>', '').replace('</p>', '').replace('<br>', '').strip() if summary_raw else ""
                
                # Extract authors
                authors_list = [author.get('name') for author in entry.get('authors', [])]
                
                new_entry = {
                    "id": uid,
                    "title": entry.get('title', 'Unknown Title'),
                    "link": entry.get('link', ''),
                    "authors": authors_list,
                    "summary": summary_text,
                    "source": source_name,
                    # 🚀 【关键修复】使用文章本身的发布日期
                    "date": parse_date(entry) 
                }
                
                new_entries_list.append(new_entry)
                seen_ids.add(uid) # Add to the seen set immediately

        except Exception as e:
            print(f"Error processing RSS feed {url}: {e}")
            
    # Combine old seen list with new entries
    # Note: We must update the seen list to include the newly fetched data structure
    
    # 重新构建 seen_list: 确保只包含唯一的、最新的条目
    # 因为我们只用新的 entry 对象填充 new_entries_list，所以只需将新旧列表合并
    
    # 🚨 注意：为了保证 seen_list 不会无限增长，我们可能需要限制其大小。
    # 假设我们保留 500000 篇历史文章。
    MAX_HISTORY = 500000000
    
    # 过滤掉旧列表中重复的 ID，然后合并
    # 确保 seen_list 只包含那些 ID 不在 new_entries_list 中的旧条目
    current_seen_ids = {p['id'] for p in new_entries_list}
    filtered_old_seen = [p for p in seen_list if p.get('id') not in current_seen_ids]
    
    updated_seen_list = new_entries_list + filtered_old_seen
    
    # 裁剪列表以限制大小
    updated_seen_list = updated_seen_list[:MAX_HISTORY]
    
    save_seen_papers(updated_seen_list)
    
    return new_entries_list

if __name__ == "__main__":
    new_papers = fetch_new_entries()
    
    print(f"共抓取 {len(new_papers)} 篇新论文")

    if new_papers:
        # Save new papers to a separate file (optional, but helpful for debugging/future features)
        os.makedirs(os.path.dirname(PAPERS_JSON_PATH), exist_ok=True)
        with open(PAPERS_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(new_papers, f, indent=2, ensure_ascii=False)
        print(f"新论文详情已保存至 {PAPERS_JSON_PATH}")
    else:
        print("今日无新增论文。")
