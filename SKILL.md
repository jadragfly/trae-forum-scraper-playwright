---
name: trae-forum-scraper-playwright
description: 使用标准 Playwright 抓取 Trae 论坛技能创作赛文章，自动滚动加载、提取投票数、过滤非竞赛帖子、生成热度排行榜 + ECharts 可视化图表 + Top 30 技能文章存档。
---

# Trae Forum Skill-Article Scraper (Standard Playwright)

Scrapes skill-creation articles from the Trae forum hot category and generates ranking/prediction/chart.

## Features

- **Auto-scroll lazy load** — scrolls ~22+ times to load ALL topics
- **Vote extraction** — correctly extracts vote count from `a.list-vote-count.vote-count-N` CSS class
- **Competition filter** — excludes announcements, guides, prize notices, etc.
- **Combined ranking** — `votes*3 + replies*0.4 + views*0.1`
- **Prize prediction** — predicts Top 30 winners with reason
- **ECharts visualization** — generates interactive HTML chart (3 views: bar comparison, score ranking, scatter plot)
- **Full article fetch** — saves Top 30 as structured markdown files

## Requirements

```bash
pip install playwright
playwright install chromium
```

## Usage

```bash
# Full run: rank + fetch Top 30
python scrape_trae.py --max 30

# Ranking only (skip article fetch)
python scrape_trae.py --ranking-only

# Show browser window
python scrape_trae.py --no-headless

# Generate chart only (after ranking exists)
python generate_chart.py

# Debug mode
python scrape_trae.py --max 30 --debug
```

## Output

```
trae_skills/
├── RANKING.md                    # Full ranking (700+ skills) + predicted Top 30
├── top30_chart.html              # ECharts interactive visualization
├── 01_xxx.md                     # Top 1 article
├── 02_xxx.md                     # Top 2 article
└── ...                           # Top 3-30 articles
```

## Scoring Algorithm

```
Combined Score = Votes × 3 + Replies × 0.4 + Views × 0.1
```

- **Votes** (×3): highest weight, reflects community approval
- **Replies** (×0.4): medium weight, reflects discussion activity
- **Views** (×0.1): lowest weight, reflects exposure

## Git 提交方式

**推荐使用 SSH 方式**提交代码到 GitHub，更安全且无需重复输入密码：

```bash
# 初始化仓库
git init

# 配置用户信息
git config user.name "jadragfly"
git config user.email "331936128@qq.com"

# 添加远程仓库（SSH 方式）
git remote add origin git@github.com:jadragfly/trae-forum-scraper-playwright.git

# 添加文件并提交
git add .
git commit -m "Commit message"

# 推送到远程仓库
git push -u origin master
```

**注意**：使用 SSH 方式前需确保 GitHub 账户已配置 SSH 密钥。