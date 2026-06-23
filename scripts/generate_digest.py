import os
import json
import time
import re
from datetime import datetime
from openai import OpenAI

# ================== 配置 ==================
SEEN_JSON_PATH = "state/seen.json"
OUTPUT_PATH = "output/daily.md"

# ================== 主题关键词 ==================
TOPIC_KEYWORDS = {
    "GPlates_tectonic": [
        "gplates", "gplately", "pygplates",
        "plate reconstruction", "plate tectonic reconstruction",
        "deep-time reconstruction", "full-plate model",
        "paleogeographic reconstruction", "continental drift",
        "tectonic evolution", "plate boundary", "kinematic reconstruction",
    ],
    "ML_in_geology": [
        "machine learning", "deep learning", "neural network",
        "random forest", "xgboost", "gradient boosting",
        "support vector", "gaussian process",
        "geochemistry", "geophysical", "seismic", "earthquake",
        "lithology", "mineral prospecting", "ore prediction",
        "petrophysics", "gravity anomaly", "magnetotelluric",
        "remote sensing", "hyperspectral", "landslide susceptibility",
    ],
    "LLM_in_geology": [
        "large language model", "llm", "foundation model", "gpt",
        "chatgpt", "generative ai",
        "knowledge graph", "information extraction",
        "geoscience", "geological", "geology", "earth science",
        "field note", "geological report",
    ],
    "AntarcticPeninsula_magma": [
        "antarctic peninsula", "west antarctica",
        "south shetland islands", "bransfield strait",
        "graham land", "palmer land", "trinity peninsula",
        "scotia arc", "tectonomagmatic", "arc magmatism",
        "subduction", "back-arc", "cretaceous magmatism",
        "zircon u-pb", "hf isotope",
    ],
}

HIGH_QUALITY_JOURNALS = (
    "nature", "science", "geology", "eps", "epslets", "epsl",
    "geochronology", "ggg", "jgr", "grl", "tectonics",
    "lithos", "chemical geology", "cmp", "antarctic science",
    "geosphere", "gsa bulletin", "reviews of geophysics",
)

TAG_ZH = {
    "GPlates_tectonic": "🟢 GPlates / 板块构造模拟",
    "ML_in_geology": "🔵 机器学习 × 地质",
    "LLM_in_geology": "🟣 大模型 × 地质",
    "AntarcticPeninsula_magma": "🔴 南极半岛构造岩浆",
}

# ================== 工具函数 ==================
def norm(text: str) -> str:
    return (text or "").lower().replace("-", " ").strip()

def contains(tokens, text):
    return any(tok in text for tok in tokens)

def classify_paper(p: dict) -> dict:
    blob = norm(f"{p.get('title','')} {p.get('summary','')}")
    src = norm(p.get('source',''))

    tags, score = [], 0

    # GPlates
    if contains(TOPIC_KEYWORDS["GPlates_tectonic"], blob):
        tags.append("GPlates_tectonic")
        score += 3

    # ML（必须同时出现ML词+地学对象）
    ml_core = ["machine learning", "deep learning", "neural network",
               "random forest", "xgboost", "gradient boosting"]
    geo_obj = [k for k in TOPIC_KEYWORDS["ML_in_geology"]
               if k not in ml_core]
    if contains(ml_core, blob) and contains(geo_obj, blob):
        tags.append("ML_in_geology")
        score += 2

    # LLM
    if contains(TOPIC_KEYWORDS["LLM_in_geology"], blob) and \
       contains(["geology", "geoscience", "earth science"], blob):
        tags.append("LLM_in_geology")
        score += 2

    # Antarctic Peninsula
    if contains(TOPIC_KEYWORDS["AntarcticPeninsula_magma"], blob):
        tags.append("AntarcticPeninsula_magma")
        score += 3

    # Journal bonus
    if any(j in src for j in HIGH_QUALITY_JOURNALS):
        score += 1

    if score >= 3:
        pri = "high"
    elif score >= 1:
        pri = "medium"
    else:
        pri = "low"

    return {"tags": tags, "score": score, "priority": pri}


# ================== 主流程 ==================
today = datetime.now().strftime("%Y-%m-%d")

if not os.path.exists(SEEN_JSON_PATH):
    print("seen.json 不存在，请先运行 RSS 抓取脚本。")
    exit(1)

with open(SEEN_JSON_PATH, "r", encoding="utf-8") as f:
    seen = json.load(f)

papers_today = [p for p in seen if isinstance(p, dict) and p.get("date") == today]

if not papers_today:
    print("今日没有新增论文。")
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(f"# Daily Geoscience Digest — {today}\n\n今日没有新增论文。\n")
    exit(0)

# ---------- 分类 ----------
for p in papers_today:
    c = classify_paper(p)
    p["_tags"] = c["tags"]
    p["_pri"] = c["priority"]
    p["_score"] = c["score"]

highlighted = [p for p in papers_today if p["_pri"] == "high"]
medium = [p for p in papers_today if p["_pri"] == "medium"]
low = [p for p in papers_today if p["_pri"] == "low"]

print(f"分类完成 → 重点:{len(highlighted)}  相关:{len(medium)}  其他:{len(low)}")

# ---------- AI 摘要 ----------
ai_summary = "（未生成 AI 摘要）"
papers_for_ai = highlighted if highlighted else medium

if papers_for_ai:
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    if not DEEPSEEK_API_KEY:
        ai_summary = "⚠️ 未设置 DEEPSEEK_API_KEY，跳过 AI 摘要。"
    else:
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
        if len(papers_for_ai) > 40:
            papers_for_ai = papers_for_ai[:40]

        papers_brief = "\n".join(
            f"[{TAG_ZH.get(t,'')}] {p.get('title','')} ({p.get('source','')})"
            for p in papers_for_ai
            for t in p.get("_tags",[])
        )

        system_prompt = """你是地球科学学术编辑，专注以下方向：
1) GPlates / 深时板块构造模拟
2) 机器学习在地学中的应用
3) 大模型(LLM)在地学中的应用
4) 南极半岛构造–岩浆演化

请基于【已标注主题】的论文：
- 重点解读高价值论文（为什么重要、方法亮点、潜在影响）
- 按主题分组输出
- 其余论文仅用一段话概括，不必逐条展开
- 使用 Markdown，语气专业但简洁
"""

        user_prompt = f"日期：{today}\n论文列表：\n{papers_brief}"

        def retry_api_call(max_retries=3):
            for i in range(max_retries):
                try:
                    r = client.chat.completions.create(
                        model="deepseek-reasoner",
                        messages=[
                            {"role":"system","content":system_prompt},
                            {"role":"user","content":user_prompt}
                        ],
                        stream=False
                    )
                    return r.choices[0].message.content.strip()
                except Exception as e:
                    time.sleep(2 ** i)
            return "⚠️ AI 摘要生成失败（多次重试后仍不可用）。"

        ai_summary = retry_api_call()

# ---------- 写日报 ----------
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
lines = []
lines.append(f"# Daily Geoscience Digest — {today}")
lines.append(f"- 今日新增：**{len(papers_today)}** 篇")
lines.append(f"- 重点推荐：**{len(highlighted)}** 篇\n")
lines.append("---\n")
lines.append("## 🤖 AI 精选摘要\n")
lines.append(ai_summary)
lines.append("\n---\n")

# 重点论文
if highlighted:
    lines.append("## ⭐ 重点推荐论文")
    for p in highlighted:
        lines.append(f"\n### {p.get('title')}")
        lines.append(f"- 标签：{' / '.join(TAG_ZH[t] for t in p.get('_tags',[]))}")
        lines.append(f"- 期刊：{p.get('source','')}")
        lines.append(f"- 链接：{p.get('link','')}")
        if p.get("summary"):
            lines.append(f"> {p['summary'][:400]}...")

# 相关论文
if medium:
    lines.append("\n## 📌 相关论文（未展开）")
    for p in medium:
        lines.append(f"- [{p.get('title')}]({p.get('link','')})")

# 其他
if low:
    lines.append("\n## 📄 其余新增")
    lines.append(f"> 共 {len(low)} 篇，未展开。")

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"✅ 日报已生成：{OUTPUT_PATH}")
