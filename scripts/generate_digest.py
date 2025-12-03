# scripts/generate_digest.py
import os
import json
from datetime import datetime
from openai import OpenAI

# -------------------
DAILY_OUTPUT_PATH = "output/daily.txt"
SEEN_JSON_PATH = "state/seen.json"

today = datetime.now().strftime("%Y-%m-%d")

# -------------------
# 读取 seen.json
if not os.path.exists(SEEN_JSON_PATH):
    print("seen.json 不存在，请先抓取 RSS。")
    exit(1)

with open(SEEN_JSON_PATH, "r", encoding="utf-8") as f:
    seen = json.load(f)

# 筛选今日新增论文
papers_data = [p for p in seen if isinstance(p, dict) and p.get("date") == today]

if not papers_data:
    print("今日没有新增论文。")
    digest_text = "今日没有新增论文。"
else:
    # -------------------
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    if not DEEPSEEK_API_KEY:
        raise ValueError("请设置环境变量 DEEPSEEK_API_KEY")
    
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

    # 构建简要论文列表
    papers_brief = "\n".join([
        f"{p.get('title','未知标题')} ({p.get('source','未知期刊')})"
        for p in papers_data
    ])
    
    print("准备发送给 AI 的论文列表（前1000字符）：")
    print(papers_brief[:1000])

    system_prompt = (
        "你是一名地球科学领域科研助手。\n"
        "请根据以下论文列表生成科研日报。\n"
        "要求：\n"
        "1. 整体趋势提炼，6-8点。\n"
        "2. 按主题自动分类，表格形式：主题 | 代表论文 | 备注。\n"
        "3. 每篇论文一句话核心贡献。\n"
        "4. 输出清晰文本格式，不要截断内容。\n"
        "5. 不包含原始条目列表，附录单独保留。"
    )
    user_prompt = f"今天日期：{today}\n新增论文列表：\n{papers_brief}"

    try:
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            stream=False
        )
        print("AI 返回完整内容对象（用于调试）：")
        print(resp)
        ai_content = resp.choices[0].message.content.strip()
        print("AI 摘要内容预览：", ai_content[:500])
    except Exception as e:
        ai_content = f"摘要生成失败: {e}"

    digest_text = ai_content

# -------------------
# 构建最终输出
output_text = f"Daily Paper Digest — {today}\n\n"
output_text += f"今日新增论文：{len(papers_data)}\n"
output_text += f"已累计收录：{len(seen)} 篇\n\n"
output_text += "=== 摘要整理 ===\n\n"
output_text += f"{digest_text}\n\n"

# -------------------
# 附录：原始文章信息
if papers_data:
    output_text += "=== 附录：原始文章信息 ===\n\n"
    for i, p in enumerate(papers_data, 1):
        authors = p.get('authors', [])
        # 处理 None 或空值
        authors_clean = [a for a in authors if isinstance(a, str)]
        authors_str = ", ".join(authors_clean) if authors_clean else "未知"
        
        output_text += f"{i}. {p.get('title','未知标题')}\n"
        output_text += f"   作者：{authors_str}\n"
        output_text += f"   期刊/来源：{p.get('source','未知')}\n"
        output_text += f"   链接：{p.get('link','')}\n"
        if p.get("summary"):
            output_text += f"   摘要：{p['summary']}\n"
        output_text += "\n"

# -------------------
# 写入文件
os.makedirs(os.path.dirname(DAILY_OUTPUT_PATH), exist_ok=True)
with open(DAILY_OUTPUT_PATH, "w", encoding="utf-8") as f:
    f.write(output_text)

print("日报已生成，输出路径：", DAILY_OUTPUT_PATH)
