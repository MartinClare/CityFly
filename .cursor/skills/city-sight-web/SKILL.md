---
name: city-sight-web
description: >-
  City Sight magazine website: CS Magazine masthead, daily A1 newspaper front,
  pillar rails, mobile-first layout, edition archive, and OG for Facebook.
  Use when building or editing web/, homepage, stories, edition pages, or
  publish manifests.
---

# City Sight magazine (web/)

Brand: **City Sight** (full name). Logo short form: **CS Magazine**.

Public site: `www.citysight.net` (Vercel). Desk stays on `desk.citysight.net` (ECS).

## Publishing model

**Day-by-day editions**, not an endless feed.

- `/` — latest edition only (masthead date + A1 / A2 / Inside / 今日更多)
- `/edition/[date]` — that day’s issue layout
- `/stories` — archive by day
- `/stories/[slug]` — permanent article URL
- `/p/[pillar]` — continuous section across days
- `/about` — positioning

## Homepage package (~8–12)

1. Masthead: **CS Magazine** + pillar chip nav (horizontal scroll on phone)
2. **A1 ×1** — first viewport only (hook, dek, full-bleed hero)
3. **A2 ×3** — different pillars; avoid repeating A1’s pillar
4. **Inside rails** (fixed order): property → tech → city → mobility → economy
5. **今日更多** — approved overflow that day
6. Hide empty rails

### Pillar labels

| id | Label |
|----|--------|
| property | 樓市與生活 |
| tech | 科技改變生活 |
| city | 城市大變身 |
| mobility | 基建與交通 |
| economy | 經濟、錢與機會 |

A1 prefers tech/city when tied; property A1 only for true city-life stories.

## Mobile-first

- One column; first screen = masthead + A1 only
- Hero crops ~4:5 or 3:4 on phone
- Thumb-sized taps; body ~17–19px; share links on story
- No card grid in first viewport; no hover-only UI

## Content source

- Build from `web/content/stories.json` + `edition.json` produced by `robot/scripts/publish_site.py`
- Heroes in `web/public/heroes/`
- Only `status: approved`

## Design

- Expressive fonts (not Inter); HK-capable body (e.g. Noto Sans TC + display serif)
- HK dusk / harbour atmosphere — not purple-on-white or cream+terracotta
- 2–3 intentional motions (masthead, A1 rise, hero fade)

## Facebook preview

Story pages need correct OG title / description / image. FB posts are teasers linking here — not full article reprints.
