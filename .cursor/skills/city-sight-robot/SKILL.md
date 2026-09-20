---
name: city-sight-robot
description: >-
  City Sight desk/robot pipeline: multi-layer drafting, daily editions, A1
  placement, publish-to-web gates, and Facebook link posts only after www is
  live. Use when working on robot/, hk_city desk, drafts, max_article_drafts,
  cron, Caddy, or desk approve/publish flows.
---

# City Sight robot & desk

Repo layout: pipeline lives under **`robot/`**. ECS still receives **`robot/` contents** at `/opt/cityfly-robot/` (flat).

## Multi-layer funnel

Do not draft 30 full features for an ~8–12 story homepage.

| Layer | Count | Cost | Output |
|-------|------:|------|--------|
| 0 Harvest | 100+ | Cheap | Ranked candidates |
| 1 Shortlist | ~20–30 | Light | Hooks + subtitle only (cover desk) |
| 2 Full drafts | **~12** | Costly | 700–1000 字 + hero (`max_article_drafts: 12`) |
| 3 Web | all 通過 | — | Front ~8–12 + 今日更多 overflow |
| 4 Facebook | A1 (optional A2) | — | Link teaser to www URL only |

Bump full drafts to **~15** only if rejection rate is high — not back to 30.

## Desk rules

- Publish only `status: approved` — never cron → www or Facebook
- Placement: `placement: a1` / `a2` (one A1 per edition day)
- Buttons (when built): 上 A1 / 上 A2 / 發佈到網站 / 發佈並分享到 Facebook
- Portal: `https://desk.citysight.net` — user `editor`, password `DESK_PASSWORD` in `robot/.env`

## Day edition

- Stories keyed by HKT date `YYYY-MM-DD`
- One edition per day; next day replaces the front; yesterday goes to archive
- Every 通過 story that day goes live (front or 今日更多) — not wasted

## Facebook (after www)

- Never post raw `.md` from robot/cron
- After story URL returns 200: Graph `POST /{page-id}/feed` with `link` + short hook `message`
- Save `facebook_post_id` on draft meta; no double-post
- Token only on ECS `robot/.env`, never on Vercel

## Commands

```bash
cd robot
source venv/bin/activate
python run_daily.py hk_city
python scripts/desk.py
python scripts/publish_site.py
```

Cover / hero titles: use skill **city-fly-cover**.
