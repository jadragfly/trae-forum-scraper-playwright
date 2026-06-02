#!/usr/bin/env python3
"""
Trae Forum Skill-Article Scraper (Standard Playwright)
======================================================
Scrapes skill-creation articles from https://forum.trae.cn/c/37-category/37/l/hot
and saves each article as a structured markdown file.

Features:
- Auto-scrolls ~22+ times to bypass lazy-loading and load ALL topics
- Correctly extracts vote count from a.list-vote-count.vote-count-N elements
- Filters out non-competition articles (announcements, guides, prize notices)
- Generates combined ranking (votes*3 + replies*2 + views*0.1)
- Predicts prize-winning Top 30 with reasoning

Requirements: pip install playwright && playwright install chromium
Usage: python scrape_trae.py
"""

import os
import re
import sys
import time
import json
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
FORUM_URL = "https://forum.trae.cn/c/37-category/37/l/hot"
OUTPUT_DIR = "trae_skills"
MAX_SCROLLS = 30
MAX_ARTICLES = 50
PAGE_TIMEOUT = 60000
ARTICLE_TIMEOUT = 15000

DEBUG = False


def debug(*args, **kwargs):
    if DEBUG:
        print("[DEBUG]", *args, **kwargs)


# ---------------------------------------------------------------------------
# Filter: exclude non-competition articles
# ---------------------------------------------------------------------------
def is_competition_article(topic):
    """Return True if the topic is a competition skill article (not announcement/guide)."""
    title = topic.get("title", "")
    title_lower = title.lower()

    # Exclusion patterns for non-competition posts
    exclusion_patterns = [
        r'^【公告】', r'^公告[：:]',
        r'必看.*指南', r'投稿指南', r'参赛指引',
        r'参与奖', r'抽奖',
        r'赛事速递', r'DAY \d+',
        r'关于.*类别', r'关于.*分类',
        r'规则奖励', r'参赛说明',
        r'一切皆可 Skill',
        r'SOLO 技能创作赛专区',
        r'Skill 大赛',
    ]

    for pattern in exclusion_patterns:
        if re.search(pattern, title):
            debug(f"  Filtered out: {title[:60]}")
            return False

    # Must have "skill" or "创作" in title (competition category posts)
    has_keyword = bool(re.search(r'[Ss]kill|创作|测评', title))
    if not has_keyword and (title.startswith('【') or title.startswith('[')):
        debug(f"  No skill keyword, excluded: {title[:60]}")
        return False

    return True


# ---------------------------------------------------------------------------
# Phase 1 & 2: Open forum, lazy-load scroll, extract topic metadata
# ---------------------------------------------------------------------------
def scroll_to_load_all(page):
    """
    Scroll to bottom repeatedly to trigger lazy-loading.
    Returns when no new topics appear after a full scroll cycle.
    """
    print("Loading forum page (with lazy-load scroll)...")
    page.goto(FORUM_URL, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
    page.wait_for_timeout(5000)

    prev_count = 0
    for i in range(1, MAX_SCROLLS + 1):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(1500)

        current_count = page.evaluate("document.querySelectorAll('tr.topic-list-item').length")

        if current_count > prev_count:
            print(f"  Scroll {i:2d}/{MAX_SCROLLS}: {current_count} topics loaded (+{current_count - prev_count})")
            prev_count = current_count
        else:
            page.wait_for_timeout(2000)
            current_count = page.evaluate("document.querySelectorAll('tr.topic-list-item').length")
            if current_count <= prev_count:
                print(f"  Scroll {i:2d}/{MAX_SCROLLS}: no more topics (total: {current_count})")
                break
            print(f"  Scroll {i:2d}/{MAX_SCROLLS}: {current_count} topics loaded (delayed)")

    print(f"\n  Done scrolling. Total topics: {prev_count}")
    return prev_count


def extract_topics(page):
    """
    Extract topic metadata including votes from a.list-vote-count elements.
    Vote count is embedded in CSS class: vote-count-N
    """
    topics = page.evaluate("""
        () => {
            const rows = document.querySelectorAll('tr.topic-list-item');
            const results = [];
            rows.forEach(tr => {
                const link = tr.querySelector('a[href*="/t/"]');
                const titleEl = tr.querySelector('.link-top-line');
                if (!link || !titleEl) return;

                const title = titleEl.innerText.trim();
                if (!title) return;

                // Extract vote count from a.list-vote-count.vote-count-N
                const voteEl = tr.querySelector('a.list-vote-count');
                let votes = 0;
                if (voteEl) {
                    const match = voteEl.className.match(/vote-count-(\\d+)/);
                    if (match) votes = parseInt(match[1]) || 0;
                }

                const getNum = (sel) => {
                    const el = tr.querySelector(sel + ' .number') || tr.querySelector(sel);
                    return el ? el.innerText.trim() : '0';
                };

                results.push({
                    href: link.href,
                    title: title,
                    votes: votes,
                    replies: parseInt(getNum('.posts')) || 0,
                    views: parseInt(getNum('.views')) || 0
                });
            });
            return results;
        }
    """)

    debug(f"Extracted {len(topics)} topics")
    return topics


# ---------------------------------------------------------------------------
# Scoring: combine votes, replies, views with weighted formula
# ---------------------------------------------------------------------------
def compute_score(topic):
    """Combined score: votes * 3 + replies * 0.4 + views * 0.1"""
    votes = topic.get("votes", 0)
    replies = topic.get("replies", 0)
    views = topic.get("views", 0)
    score = votes * 3 + replies * 0.4 + views * 0.1
    # Chart generation logic (placeholder for actual plotting)
    if DEBUG:
        print(f"Score for {topic.get('title', '')[:30]}: {score:.1f}")
    return score


# ---------------------------------------------------------------------------
# Ranking file generator
# ---------------------------------------------------------------------------
def write_ranking_file(all_topics, output_dir):
    """Generate RANKING.md with vote-based ranking + predicted prize winners."""

    # Filter out non-competition articles
    filtered = [t for t in all_topics if is_competition_article(t)]
    filtered_out = len(all_topics) - len(filtered)

    print(f"Filtered: {len(filtered)} competition articles (+{filtered_out} excluded)")

    # Sort by votes descending, then replies, then views
    sorted_topics = sorted(filtered, key=lambda t: (-t.get("votes", 0), -t.get("replies", 0), -t.get("views", 0)))

    filename = os.path.join(output_dir, "RANKING.md")
    lines = []

    # ===== Main Ranking =====
    lines.append("# Trae 论坛技能热度排行榜")
    lines.append("")
    lines.append(f"共 {len(sorted_topics)} 个竞赛技能 | 按投票数降序排列 | 同票按回复数 | 抓取时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append(f"> 已排除 {filtered_out} 条非竞赛帖子（公告、指南、抽奖等）")
    lines.append("")
    lines.append("| 排名 | 技能名称 | 投票数 | 回复数 | 浏览数 | 综合分 |")
    lines.append("|------|----------|--------|--------|--------|--------|")

    for i, t in enumerate(sorted_topics):
        rank = i + 1
        title = t["title"][:80]
        votes = t.get("votes", 0)
        replies = t.get("replies", 0)
        views = t.get("views", 0)
        score = round(compute_score(t), 1)
        link = t.get("href", "")
        lines.append(f"| {rank} | [{title}]({link}) | {votes} | {replies} | {views} | {score} |")

    lines.append("")
    lines.append("---")
    lines.append(f"_数据来源: [Trae 论坛 - 技能创建分类]({FORUM_URL})_")
    lines.append("")

    # ===== Predicted Prize Winners Top 30 =====
    lines.append("## 预测可能获奖的 Top 30")
    lines.append("")

    # Sort by combined score descending for prediction
    prediction_pool = sorted(filtered, key=lambda t: -compute_score(t))

    lines.append("| 排名 | 技能名称 | 投票 | 回复 | 浏览 | 综合分 | 预测理由 |")
    lines.append("|------|----------|------|------|------|--------|----------|")

    for i, t in enumerate(prediction_pool[:30]):
        rank = i + 1
        title = t["title"][:80]
        votes = t.get("votes", 0)
        replies = t.get("replies", 0)
        views = t.get("views", 0)
        score = round(compute_score(t), 1)
        link = t.get("href", "")
        reason = generate_prediction_reason(t, rank)
        lines.append(f"| {rank} | [{title}]({link}) | {votes} | {replies} | {views} | {score} | {reason} |")

    lines.append("")
    lines.append("### 评分算法说明")
    lines.append("")
    lines.append("综合分 = **投票数 × 3 + 回复数 × 0.4 + 浏览数 × 0.1**")
    lines.append("")
    lines.append("- **投票数**权重最高（×3）：反映社区认可度，是获奖的最强指标")
    lines.append("- **回复数**权重次之（×0.4）：反映讨论热度，说明技能引起了关注")
    lines.append("- **浏览数**权重最低（×0.1）：反映曝光量，但容易被首页推荐影响")
    lines.append("")
    lines.append("> 预测基于公开数据估算，实际获奖结果以论坛官方评选为准。")
    lines.append("> 部分高质量技能可能因为发布较晚而数据偏低，实际竞争力可能被低估。")

    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\n  Ranking saved: {filename}")
    return filename


def generate_prediction_reason(topic, rank):
    """Generate a brief reason why this skill might win."""
    votes = topic.get("votes", 0)
    replies = topic.get("replies", 0)
    views = topic.get("views", 0)
    title = topic.get("title", "")

    reasons = []

    if votes >= 30:
        reasons.append(f"高票{votes}票")
    elif votes >= 15:
        reasons.append(f"{votes}票不错")
    elif votes >= 5:
        reasons.append(f"有{votes}票基础")

    if replies >= 20:
        reasons.append(f"讨论热烈({replies}回复)")
    elif replies >= 10:
        reasons.append(f"活跃讨论({replies}回复)")

    if views >= 500:
        reasons.append(f"高曝光({views}浏览)")

    # Content-based hints
    if "量化" in title or "股票" in title or "基金" in title or "金融" in title:
        reasons.append("金融类热门话题")
    if "游戏" in title or "精灵" in title or "3D" in title or "物理" in title:
        reasons.append("技术类硬核技能")
    if "文案" in title or "小红书" in title or "写作" in title:
        reasons.append("内容创作热门")
    if "科研" in title or "论文" in title or "综述" in title:
        reasons.append("科研工具需求大")
    if "保险" in title or "医疗" in title or "健康" in title:
        reasons.append("实用生活类")
    if "宠物" in title or "桌面" in title:
        reasons.append("趣味创意类")

    if not reasons:
        if views > 100:
            reasons.append("有一定曝光")
        else:
            reasons.append("潜力作品")

    return "，".join(reasons[:3])


# ---------------------------------------------------------------------------
# Phase 3: Fetch full article content from each topic detail page
# ---------------------------------------------------------------------------
def fetch_article(page, topic, index, total):
    """Navigate to a single topic page and extract its full content."""
    url = topic["href"]
    title = topic["title"]
    print(f"  [{index}/{total}] Fetching: {title[:60]}...")

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=ARTICLE_TIMEOUT)
        page.wait_for_timeout(1000)

        content = page.evaluate("""
            () => {
                const cooked = document.querySelector('.cooked');
                if (!cooked) return null;

                const authorEl = document.querySelector('.username a, .first-name, .name');
                const author = authorEl ? authorEl.innerText.trim() : 'Unknown';

                const timeEl = document.querySelector('.topic-map .topic-created-at, .relative-date');
                const postTime = timeEl ? timeEl.innerText.trim() : '';

                const clone = cooked.cloneNode(true);
                clone.querySelectorAll('script, style, .nav, .sidebar, img.avatar').forEach(el => el.remove());
                clone.querySelectorAll('img[src]').forEach(img => {
                    if (img.src.startsWith('/') || !img.src.startsWith('http')) {
                        img.src = new URL(img.getAttribute('src'), window.location.origin).href;
                    }
                });

                return {
                    bodyHTML: clone.innerHTML.trim(),
                    author: author,
                    time: postTime
                };
            }
        """)

        if not content or not content.get("bodyHTML"):
            print(f"    No content found")
            return None

        topic["author"] = content.get("author", "Unknown")
        topic["time"] = content.get("time", "")
        topic["body_html"] = content.get("bodyHTML", "")
        return topic

    except PWTimeout:
        print(f"    Timeout")
        return None
    except Exception as e:
        print(f"    Error: {e}")
        return None


# ---------------------------------------------------------------------------
# Phase 4: Convert HTML to markdown and write files
# ---------------------------------------------------------------------------
def html_to_markdown(html):
    """Simple HTML-to-markdown converter for the typical Discourse content."""
    code_blocks = []

    def save_code(m):
        code_blocks.append(m.group(0))
        return f"__CODE_BLOCK_{len(code_blocks) - 1}__"

    text = re.sub(r'<pre[^>]*>[\s\S]*?</pre>', save_code, html)
    text = re.sub(r'<code[^>]*>[\s\S]*?</code>', save_code, text)

    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'</p>\s*<p[^>]*>', '\n\n', text)
    text = re.sub(r'<p[^>]*>', '', text)
    text = re.sub(r'</p>', '', text)

    text = re.sub(r'<h1[^>]*>(.*?)</h1>', r'\n# \1\n', text, flags=re.DOTALL)
    text = re.sub(r'<h2[^>]*>(.*?)</h2>', r'\n## \1\n', text, flags=re.DOTALL)
    text = re.sub(r'<h3[^>]*>(.*?)</h3>', r'\n### \1\n', text, flags=re.DOTALL)
    text = re.sub(r'<h4[^>]*>(.*?)</h4>', r'\n#### \1\n', text, flags=re.DOTALL)

    text = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', text, flags=re.DOTALL)
    text = re.sub(r'<b[^>]*>(.*?)</b>', r'**\1**', text, flags=re.DOTALL)
    text = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', text, flags=re.DOTALL)
    text = re.sub(r'<i[^>]*>(.*?)</i>', r'*\1*', text, flags=re.DOTALL)

    text = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r'[\2](\1)', text, flags=re.DOTALL)

    text = re.sub(r'<ul[^>]*>', '', text)
    text = re.sub(r'</ul>', '', text)
    text = re.sub(r'<ol[^>]*>', '', text)
    text = re.sub(r'</ol>', '', text)
    text = re.sub(r'<li[^>]*>', '- ', text)
    text = re.sub(r'</li>', '\n', text)

    text = re.sub(r'<blockquote[^>]*>', '\n> ', text)
    text = re.sub(r'</blockquote>', '\n', text)

    text = re.sub(r'<img[^>]*src="([^"]*)"[^>]*/?>', r'![](\1)', text)
    text = re.sub(r'<hr[^>]*/?>', '\n---\n', text)

    text = re.sub(r'<[^>]+>', '', text)

    for i, block in enumerate(code_blocks):
        placeholder = f"__CODE_BLOCK_{i}__"
        inner = re.sub(r'</?pre[^>]*>', '', block)
        inner = re.sub(r'</?code[^>]*>', '', inner)
        inner = inner.strip()
        text = text.replace(placeholder, f"\n```\n{inner}\n```\n")

    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    return text


def sanitize_filename(title):
    """Convert a title to a safe filename."""
    name = re.sub(r'[^\w\u4e00-\u9fff\-]', '_', title)
    name = re.sub(r'_+', '_', name).strip('_')
    if len(name) > 60:
        name = name[:60]
    return name or "untitled"


def write_markdown(topic, index, output_dir):
    """Write a single article as a markdown file."""
    title = topic["title"]
    filename = f"{index:02d}_{sanitize_filename(title)}.md"
    filepath = os.path.join(output_dir, filename)

    body_md = html_to_markdown(topic.get("body_html", ""))

    lines = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"> Source: {topic['href']}")
    lines.append(f"> Author: {topic.get('author', 'Unknown')}")
    lines.append(f"> Votes: {topic.get('votes', 0)} | Replies: {topic.get('replies', 0)} | Views: {topic.get('views', 0)} | Score: {round(compute_score(topic), 1)}")
    if topic.get("time"):
        lines.append(f"> Posted: {topic['time']}")
    lines.append("")
    lines.append(body_md)
    lines.append("")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"    Saved: {filename}")
    return filepath


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Scrape Trae Forum skill articles")
    parser.add_argument("--url", default=FORUM_URL, help="Forum category URL")
    parser.add_argument("--output", default=OUTPUT_DIR, help="Output directory")
    parser.add_argument("--max-scrolls", type=int, default=MAX_SCROLLS, help="Max lazy-load scrolls")
    parser.add_argument("--max", type=int, default=MAX_ARTICLES, help="Max articles to fetch content for")
    parser.add_argument("--no-headless", action="store_true", help="Show browser window")
    parser.add_argument("--ranking-only", action="store_true", help="Only generate ranking, skip article fetch")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    args = parser.parse_args()

    global DEBUG
    DEBUG = args.debug

    headless = not args.no_headless
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== Trae Forum Skill Scraper ===")
    print(f"URL:     {args.url}")
    print(f"Output:  {output_dir}")
    print(f"Max scrolls: {args.max_scrolls}")
    print(f"Max articles: {args.max}")
    print(f"Ranking only: {args.ranking_only}")
    print(f"Headless: {headless}")
    print(f"DEBUG: {DEBUG}")
    print()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            locale="zh-CN",
            timezone_id="Asia/Shanghai"
        )
        page = context.new_page()

        try:
            total_loaded = scroll_to_load_all(page)
            if total_loaded == 0:
                print("ERROR: No topics found.")
                return

            all_topics = extract_topics(page)
            if not all_topics:
                print("ERROR: Topic extraction returned empty.")
                return

            print(f"\nExtracted {len(all_topics)} topics total")

            # Generate ranking file (with filtering + prediction)
            write_ranking_file(all_topics, output_dir)

            if args.ranking_only:
                print(f"\nRanking-only mode. Done!")
                return

            # Get filtered topics for article fetch
            filtered = [t for t in all_topics if is_competition_article(t)]
            selected = sorted(filtered, key=lambda t: -compute_score(t))[:args.max]

            print(f"\nSelected {len(selected)} articles for content fetch:")
            for i, t in enumerate(selected):
                print(f"  {i+1:2d}. [{t['votes']} votes, score={round(compute_score(t),1)}] {t['title'][:70]}")
            print()

            saved_count = 0
            for i, topic in enumerate(selected):
                result = fetch_article(page, topic, i + 1, len(selected))
                if result and result.get("body_html"):
                    write_markdown(result, saved_count + 1, output_dir)
                    saved_count += 1
                time.sleep(1)

            print(f"\nDone! {saved_count} articles saved to '{output_dir}/'")

        finally:
            browser.close()


if __name__ == "__main__":
    main()