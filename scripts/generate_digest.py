# scripts/generate_digest.py
import os
import json
from datetime import datetime
from openai import OpenAI  # 使用 DeepSeek 兼容 OpenAI SDK
import sys

# 路径设置
DAILY_MD_PATH = "output/daily.md"
SEEN_JSON_PATH = "state/seen.json"

# 从 seen.json 里读取已有记录
with open(SEEN_JSON_PATH, "r", encoding="utf-8") as f:
    seen = json.load(f)

# 收集还没有生成摘要的论文
papers = []
papers_idx = []  # 保存索引用于标记 digest_generated
for idx, paper in enumerate(seen):
    if not paper.get("digest_generated", False):
        papers.append(f"- {paper['title']} ({paper['source']})")
        papers_idx.append(idx)

today = datetime.now().strftime("%Y-%m-%d")

if not papers:
    print("No new entries to summarize.")
    digest = "今日没有新增论文。"
else:
    print(f"Generating digest for {len(papers)} papers...")

    # DeepSeek API 配置
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    if not DEEPSEEK_API_KEY:
        raise ValueError("请设置环境变量 DEEPSEEK_API_KEY")

    client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com"
    )

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": "你是一名地球科学领域的专业科研助手。"
                },
                {
                    "role": "user",
                    "content": (
                        f"下面是今天抓取的新增论文列表，请完成以下任务：\n\n"
                        "1）提炼整体趋势\n"
                        "2）生成“今日论文晨报”，适合科研工作者快速阅读\n"
                        "3）按主题自动分类（如构造、地球化学、地球动力学等）\n"
                        "4）每篇论文总结一句话核心贡献\n"
                        "5）最后附上原始条目列表\n\n"
                        f"今天日期：{today}\n\n"
                        "以下是新增论文条目：\n\n" +
                        "\n".join(papers) +
                        "\n\n请严格输出 Markdown 格式。"
                    )
                }
            ],
            stream=False
        )
        digest = response.choices[0].message.content

        # 标记生成摘要
        for idx in papers_idx:
            seen[idx]['digest_generated'] = True

        # 保存回 seen.json
        with open(SEEN_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(seen, f, ensure_ascii=False, indent=2)

    except Exception as e:
        digest = f"摘要生成失败: {e}"

# 写入 daily.md
if os.path.exists(DAILY_MD_PATH):
    with open(DAILY_MD_PATH, "r", encoding="utf-8") as f:
        daily_md = f.read()
else:
    daily_md = ""

# 在 markdown 顶部加摘要
new_content = f"# Daily Paper Digest — {today}\n\n**今日新增论文**：{len(papers)}\n\n**摘要整理**：\n{digest}\n\n---\n\n"
new_content += daily_md

with open(DAILY_MD_PATH, "w", encoding="utf-8") as f:
    f.write(new_content)

print("Markdown file updated.")
