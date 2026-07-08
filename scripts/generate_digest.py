import os
import re
import json
import time
import html
from datetime import datetime
from openai import OpenAI

SEEN_JSON_PATH = "state/seen.json"
OUTPUT_PATH = "output/daily.md"
MAX_DISPLAY_COUNT = 40

today = datetime.now().strftime("%Y-%m-%d")


EARTH_KEYWORDS = [
    "geology", "geological", "geoscience", "geodynamic", "geodynamics",
    "tectonic", "tectonics", "plate", "subduction", "orogen", "orogenic",
    "crust", "mantle", "lithosphere", "seismic", "earthquake", "fault",
    "volcan", "magma", "magmatic", "igneous", "petrology", "geochemistry",
    "isotope", "zircon", "mineral", "ore", "deposit", "metallogen",
    "hydrothermal", "porphyry", "sediment", "sedimentary", "basin",
    "paleomag", "paleomagnetic", "antarctic", "antarctica", "andes",
    "and Central Andes".lower(), "patagonia", "scotia", "drake passage",
    "glacier", "rock glacier", "ice sheet", "cryosphere", "greenland",
    "paleoclimate", "landscape evolution", "erosion", "weathering",
    "remote sensing", "geophysical", "tomography", "gravity anomaly",
    "magnetic anomaly", "geochronology", "u-pb", "ar-ar", "thermochronology"
]

BROAD_EARTH_KEYWORDS = [
    "earth", "climate", "environment", "landscape", "mountain",
    "river", "delta", "ocean", "sea level", "paleo", "fossil"
]

ML_KEYWORDS = [
    "machine learning", "deep learning", "neural network",
    "random forest", "artificial intelligence"
]

EXCLUDE_KEYWORDS = [
    "cancer", "tumor", "immune", "protein", "gene", "genome", "rna", "dna",
    "brain", "neuron", "synaptic", "arabidopsis", "butterfly", "bacteria",
    "microbiome", "coral", "surgery", "therapeutics", "bloodstream",
    "infection", "vaccine", "drug", "photovoltaic", "quantum communication",
    "photonic", "antenna", "battery", "catalyst", "semiconductor",
    "robotic surgery", "molecular", "cellular", "enzyme"
]

GEOSCIENCE_JOURNALS = [
    "geology", "tectonophysics", "gondwana research",
    "earth and planetary science letters", "earth-science reviews",
    "geophysical research letters", "journal of geophysical research",
    "journal of structural geology", "lithos", "chemical geology",
    "ore geology reviews", "mineralium deposita", "precambrian research",
    "quaternary science reviews", "the cryosphere", "climate of the past",
    "geochemistry, geophysics, geosystems", "solid earth"
]


def clean_text(value):
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return " ".join(clean_text(v) for v in value)
    if isinstance(value, dict):
        return " ".join(clean_text(v) for v in value.values())

    text = str(value)
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def paper_text(paper):
    return " ".join([
        clean_text(paper.get("title", "")),
        clean_text(paper.get("summary", "")),
        clean_text(paper.get("source", "")),
        clean_text(paper.get("authors", "")),
    ]).lower()


def keyword_hits(text, keywords):
    return [kw for kw in keywords if kw in text]


def is_relevant_paper(paper):
    text = paper_text(paper)
    source = clean_text(paper.get("source", "")).lower()

    journal_hits = keyword_hits(source, GEOSCIENCE_JOURNALS)
    earth_hits = keyword_hits(text, EARTH_KEYWORDS)
    broad_hits = keyword_hits(text, BROAD_EARTH_KEYWORDS)
    ml_hits = keyword_hits(text, ML_KEYWORDS)
    exclude_hits = keyword_hits(text, EXCLUDE_KEYWORDS)

    if journal_hits:
        return True

    if earth_hits:
        if len(exclude_hits) >= 2 and not any(
            kw in text for kw in ["antarctic", "geology", "tectonic", "glacier", "climate"]
        ):
            return False
        return True

    if ml_hits and broad_hits and not exclude_hits:
        return True

    if len(broad_hits) >= 2 and not exclude_hits:
        return True

    return False


def normalize_authors(authors):
    if not authors:
        return "未知"

    if isinstance(authors, str):
        return authors.strip() or "未知"

    if not isinstance(authors, list):
        return clean_text(authors) or "未知"

    names = []
    for author in authors:
        if isinstance(author, dict):
            name = author.get("name") or author.get("full_name") or author.get("title")
            if not name:
                given = author.get("given", "")
                family = author.get("family", "")
                name = f"{given} {family}".strip()
            if name:
                names.append(clean_text(name))
        else:
            name = clean_text(author)
            if name:
                names.append(name)

    if not names:
        return "未知"

    out = ", ".join(names[:3])
    if len(names) > 3:
        out += " 等"
    return out


def get_paper_link(paper):
    return (
        paper.get("link")
        or paper.get("url")
        or paper.get("doi")
        or paper.get("id")
        or ""
    )


def build_papers_brief(papers):
    chunks = []
    for i, p in enumerate(papers, 1):
        title = clean_text(p.get("title", "未知标题"))
        source = clean_text(p.get("source", "未知期刊"))
        summary = clean_text(p.get("summary", ""))[:600]
        chunks.append(
            f"{i}. 标题：{title}\n"
            f"来源：{source}\n"
            f"摘要：{summary}"
        )
    return "\n\n".join(chunks)


def call_deepseek_summary(papers_to_process, total_raw_count, excluded_count):
    if not papers_to_process:
        return (
            f"今日共抓取 {total_raw_count} 篇论文，但经关键词过滤后没有发现明显地学相关论文。"
            f"已自动排除 {excluded_count} 篇明显不相关论文。"
        )

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        return "警告：未设置 DEEPSEEK_API_KEY，无法生成 AI 摘要。下方仅保留筛选后的原始论文列表。"

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-reasoner")

    system_prompt = """
你是一位专业的地球科学论文晨报助手。
请只基于用户提供的筛选后论文列表生成中文晨报。

用户重点关注：
1. 固体地球动力学模拟
2. 构造地质、板块运动、俯冲、造山带
3. 岩浆作用、地球化学、同位素、锆石年代学
4. 矿产预测、成矿作用、矿床学
5. 南极、安第斯、Scotia Arc、Patagonia、Drake Passage 相关研究
6. 地球科学中的机器学习应用
7. 冰川、古气候、地貌演化等表生地球科学可简要保留

输出结构：
1. 今日概览
2. 核心趋势
3. 热点主题分类
4. 值得重点阅读的论文，最多 5 篇

不要编造没有出现在列表中的论文。
不要总结医学、生物、纯计算机、纯材料、纯工程论文。
输出适合邮件阅读，不要使用代码块。
""".strip()

    user_prompt = (
        f"今天日期：{today}\n"
        f"原始抓取论文数：{total_raw_count}\n"
        f"已排除明显不相关论文数：{excluded_count}\n"
        f"筛选后论文数：{len(papers_to_process)}\n\n"
        f"筛选后论文列表：\n{build_papers_brief(papers_to_process)}"
    )

    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                stream=False,
            )
            content = resp.choices[0].message.content
            return content.strip() if content else "AI 摘要为空，请检查模型返回。"
        except Exception as e:
            print(f"AI 调用失败，第 {attempt + 1} 次：{e}")
            time.sleep(2 * (2 ** attempt))

    return "AI 摘要生成失败，请检查 DeepSeek API、网络或模型名称。"


def build_appendix(papers_to_process):
    lines = []
    if not papers_to_process:
        lines.append("今日没有筛选出的地学相关论文。")
        return lines

    for i, p in enumerate(papers_to_process, 1):
        title = clean_text(p.get("title", "未知标题"))
        source = clean_text(p.get("source", "未知"))
        authors = normalize_authors(p.get("authors", []))
        link = get_paper_link(p)
        summary = clean_text(p.get("summary", ""))

        if len(summary) > 350:
            summary = summary[:350] + "..."

        lines.append(f"### {i}. {title}")
        lines.append(f"- 期刊：{source}")
        lines.append(f"- 作者：{authors}")
        if link:
            lines.append(f"- 链接：{link}")
        if summary:
            lines.append(f"- 摘要：{summary}")
        lines.append("")

    return lines


def write_daily_report(daily_text):
    output_dir = os.path.dirname(OUTPUT_PATH)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(daily_text)


def load_seen():
    if not os.path.exists(SEEN_JSON_PATH):
        raise FileNotFoundError("seen.json 不存在，请先运行 RSS 抓取脚本。")

    with open(SEEN_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("seen.json 格式错误：最外层应该是论文列表。")

    return data


def save_seen(seen):
    with open(SEEN_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(seen, f, indent=2, ensure_ascii=False)


def main():
    try:
        seen = load_seen()
    except Exception as e:
        print(f"读取 seen.json 出错：{e}")
        raise SystemExit(1)

    papers_unsent = [
        p for p in seen
        if isinstance(p, dict) and not p.get("sent", False)
    ]

    if not papers_unsent:
        daily_content = [
            f"Daily Paper Digest - {today}",
            "",
            "今日没有新增论文。",
            f"已累计收录：{len(seen)} 篇",
        ]
        daily_text = "\n".join(daily_content)
        write_daily_report(daily_text)
        print(f"日报已生成：{OUTPUT_PATH}")
        print("本次没有未发送论文，无需更新 seen.json。")
        return

    papers_relevant = [p for p in papers_unsent if is_relevant_paper(p)]
    total_raw_count = len(papers_unsent)
    total_relevant_count = len(papers_relevant)
    excluded_count = total_raw_count - total_relevant_count

    if total_relevant_count > MAX_DISPLAY_COUNT:
        papers_to_process = papers_relevant[:MAX_DISPLAY_COUNT]
        hidden_count = total_relevant_count - MAX_DISPLAY_COUNT
    else:
        papers_to_process = papers_relevant
        hidden_count = 0

    ai_summary = call_deepseek_summary(
        papers_to_process=papers_to_process,
        total_raw_count=total_raw_count,
        excluded_count=excluded_count,
    )

    daily_content = []
    daily_content.append(f"Daily Paper Digest - {today}")
    daily_content.append("")
    daily_content.append(f"今日抓取论文：{total_raw_count} 篇")
    daily_content.append(f"筛选后地学相关论文：{total_relevant_count} 篇")
    daily_content.append(f"已排除明显不相关论文：{excluded_count} 篇")
    if hidden_count > 0:
        daily_content.append(
            f"注：筛选后论文仍较多，本邮件仅展示前 {MAX_DISPLAY_COUNT} 篇，"
            f"其余 {hidden_count} 篇已自动归档。"
        )
    daily_content.append(f"已累计收录：{len(seen)} 篇")
    daily_content.append("")
    daily_content.append("---")
    daily_content.append("")
    daily_content.append("【AI 摘要整理】")
    daily_content.append("")
    daily_content.append(ai_summary)
    daily_content.append("")
    daily_content.append("---")
    daily_content.append("")
    daily_content.append(f"【附录：筛选后的 {len(papers_to_process)} 篇原始论文】")
    daily_content.append("")
    daily_content.append(
        "说明：附录只输出通过关键词规则筛选后的地学相关论文；"
        "医学、生物、纯工程、纯材料、纯计算机等明显不相关论文不再附在邮件后部。"
    )
    daily_content.append("")
    daily_content.extend(build_appendix(papers_to_process))

    daily_text = "\n".join(daily_content)
    write_daily_report(daily_text)
    print(f"日报已生成：{OUTPUT_PATH}")

    print(f"正在更新 {len(papers_unsent)} 篇论文的状态为 sent=True...")
    for p in papers_unsent:
        p["sent"] = True

    try:
        save_seen(seen)
        print("成功更新 seen.json。本次抓取到的论文均已标记为 sent=True。")
    except Exception as e:
        print(f"严重错误：日报已生成，但无法保存 seen.json 状态：{e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
