---
name: city-fly-cover
description: >-
  Pick City Fly's daily 20 topics and write hero titles as a hook plus
  spoken-Cantonese subtitle. Use when the user asks for topics, 20 topics,
  hero titles, hooks, cover lines, or a recrawl of the Hong Kong city magazine
  desk. Also use when drafting full articles, checking article length / 字數,
  asking how hero images are made, or generating visuals with GPT Image 2.5.
---

# City Fly / City Sight cover desk

Drafts and data live under **`robot/hk_city/`**. After reading sources, form an **independent view**. Do not echo auto-rank, GIS leftovers, US stocks, crime, or officials restating policy.

## Workflow

1. Use the latest harvest (`robot/hk_city/data/raw/` + `processed/view.json`). If sources just changed, recrawl first (`cd robot && python run_daily.py hk_city --skip-report --skip-images`).
2. Editor-pick ~20 **on-brief** hook shortlist (Layer 1). Full feature drafts are capped near **12**/day (`max_article_drafts`). One topic, one story. Merge cousins instead of listing twice.
3. Write a short desk thesis (2–3 lines), then the covers.
4. For Cantonese covers, call **DeepSeek V4 Pro** (`DEEPSEEK_MODEL=deepseek/deepseek-v4-pro-0813` via `common.llm`). Do not use Flash.
5. Save to `robot/hk_city/data/reports/YYYY-MM-DD-hero-titles.md` when the user likes them.
6. Before picking or drafting, skip anything already in `robot/hk_city/data/ledger/stories.json`.

Magazine site rules: skill **city-sight-web**. Pipeline layers: skill **city-sight-robot**.

## What to pick

Prefer a number, a map, a live window, or an open rumour:

- 建造／土地：中標價、截標、賣地、上蓋、物流用地。Building.hk / Unwire 只係發現；事實對 市建局、港鐵、發展局、路政署、創科局、GIS、施政報告、HKEXnews（見 directory §3.7）
- 生活／樓：CCL、租金、回報。代理預測標「傳聞」
- 關口／軌道：開通日期、未動工嘅軌
- 科技／傳聞：改到星期二嘅嘢；未證實要寫未證實

Kill: 美股、亞運、罪案、開放數據計劃、官員講五年規劃、政府公報複讀、標題有數但拉完內文仍然空白。

Ask life / 生意 / 投資觀察 / 建造, plus threat and rumour. Official docs are evidence, not the magazine voice.

## Cover format

Hero title = **hook**. Next line = **subtitle that says what happened**.

```markdown
**1. 沙嶺燒 281 億起超級電腦中心**
新界北動工，AI 基建埋位。
```

- Hook: one spoken-Cantonese line that stops the eye. Surprise, contrast, or a scale number.
- Subtitle: one factual line. Who / where / what number. No extra thesis.
- 香港口語繁體. English only when Hong Kong actually says the English word: `AI`, `WeChat`, `CCL`, `location`, `D4`. Not tender, EOI, yield, warehouse, developer.
- No invented people, scenes, or numbers. Rumour stays labelled 未證實 / 傳聞.
- Do not paste a dek-style editorial under every item.

Approved tone: see [examples.md](examples.md).

## After the list

Ask which numbers to draft as full pieces. Do not auto-write articles.

## Article length

Facebook / web feature. One hero, one body.

**700–1000 字.** That is the piece. Not a blurb, not a long read.

How to count (same as `hk_city/reporter.py` `_cjk_len`):

- Count Chinese characters only: `[\u4e00-\u9fff]`
- Cut at `## 來源`. Do not count the source list, disclaimer, markdown, English (`CCL`, `AI`), or Arabic numbers
- Under **700** = unfinished. Rewrite once using every number / date / name / place in the source summary. If still short, fail. Never save the stub 「現有材料還不夠」
- Over **1000** = cut. Do not pad with history or “來源沒有”

After every draft, run the count before showing the user. If it fails, fix it in the same turn.

```bash
python3 -c "
import re, pathlib, sys
p = pathlib.Path(sys.argv[1])
body = re.split(r'\n## 來源', p.read_text(encoding='utf-8'), 1)[0]
n = len(re.findall(r'[\u4e00-\u9fff]', body))
print(n, 'OK' if 700 <= n <= 1000 else 'FAIL')
" path/to/draft.md
```

Code already rejects under 700 (`MIN_ARTICLE_CJK = 700`). Do not bypass it.

## Hero image

Facebook and web share **one** main picture.

**If the press already has an image, use that.** Do not generate a fake site photo on top of it.

| Source image | Do |
|---|---|
| Official map, site photo, engineering drawing, 附圖, developer rendering | Download, crop to 16:9 if needed, use as hero. Credit: 來源、日期. |
| News photo that is just a portrait / stock / unrelated | Skip. Do not use as the city story. |
| No usable image | Generate **one** GPT Image 2.5 illustration. |

Never present an AI picture as the real site, design, or progress. If both exist: source image = hero (evidence); AI only as a labelled extra diagram, and only if it explains something the photo cannot.

GPT Image 2.5 (when needed): kie.ai `gpt-image-2-5-sunburst-text-to-image`, 16:9, 2K. File: `hk_city/data/drafts/YYYY-MM-DD/images/{slug}.png`. JSON must say `source` or `ai_generated`.