# City Sight

Hong Kong city-change magazine monorepo.

| Folder | Role |
|--------|------|
| [`robot/`](robot/) | Collectors, desk review portal, cron, publish export |
| [`web/`](web/) | Public magazine (Next.js) — CS Magazine / City Sight |
| [`plan/`](plan/) | Editorial playbooks |

## Robot (desk + drafts)

```bash
cd robot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill keys + DESK_PASSWORD
python run_daily.py hk_city
python scripts/desk.py
python scripts/publish_site.py   # → web/content + web/public/heroes
```

Full feature drafts: **`max_article_drafts: 12`**. Shortlist hooks separately (~20–30). See skill `city-sight-robot`.

Desk: https://desk.citysight.net — user `editor`, password in `robot/.env`.

ECS sync still pushes **`robot/` contents** → `/opt/cityfly-robot/`:

```bash
bash robot/scripts/alibaba/sync.sh
```

## Web (magazine)

```bash
cd robot && source venv/bin/activate && python scripts/publish_site.py
cd ../web
npm install
npm run dev
```

Daily edition front page (A1 / A2 / Inside / 今日更多). See skill `city-sight-web`.

Production target: `www.citysight.net` on Vercel (project root `web/`). DNS cutover when ready — desk stays on ECS.

## Phase notes

- **Facebook:** On ECS, approved stories can auto-post as link teasers after publish (`robot/hk_city/facebook_publish.py`, cron via `scripts/post_facebook.py`). Needs `FACEBOOK_PAGE_ID` and `FACEBOOK_PAGE_ACCESS_TOKEN` in `robot/.env`; skipped when unset. Default **2 posts per run** (`FACEBOOK_MAX_PER_RUN`; set `0` for no cap). Short hook + comment invite — not full dek.
- Human approve only — never auto-publish drafts to the public site.
