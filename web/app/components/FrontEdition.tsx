import Link from "next/link";
import {
  formatEditionDate,
  storiesForEdition,
  storyTeaser,
  type Edition,
  type Story,
} from "@/lib/content";

function editionStories(
  a1: Story | undefined,
  a2: Story[],
  inside: { items: Story[] }[],
  more: Story[],
): Story[] {
  const seen = new Set<string>();
  const out: Story[] = [];
  for (const s of [a1, ...a2, ...inside.flatMap((r) => r.items), ...more]) {
    if (!s || seen.has(s.slug)) continue;
    seen.add(s.slug);
    out.push(s);
  }
  return out;
}

/** Dates older than `current`, newest first. */
export function previousEditionDates(
  editions: Record<string, Edition>,
  current: string,
  limit = 4,
): string[] {
  return Object.keys(editions)
    .filter((d) => d < current)
    .sort()
    .reverse()
    .slice(0, limit);
}

function shortEditionDate(iso: string): string {
  const [, m, d] = iso.split("-").map(Number);
  if (!m || !d) return iso;
  return `${m}月${d}日`;
}

export function FrontEdition({
  stories,
  edition,
  previousDates,
  isToday = true,
}: {
  stories: Story[];
  edition: Edition;
  previousDates: string[];
  isToday?: boolean;
}) {
  const { a1, a2, inside, more } = storiesForEdition(edition, stories);
  const allDay = editionStories(a1, a2, inside, more);

  const archiveLinks = (
    <nav className="prev-editions" aria-label="往期刊">
      {previousDates.length > 0 ? (
        <>
          <span className="prev-editions-label">往期</span>
          {previousDates.map((d) => (
            <Link key={d} href={`/edition/${d}`}>
              {shortEditionDate(d)}
            </Link>
          ))}
        </>
      ) : null}
      <Link href="/stories">全部往期 →</Link>
    </nav>
  );

  return (
    <main className="front">
      <div className="edition-bar">
        <div>
          <strong>{isToday ? "今日刊" : "當日刊"}</strong>
          <span>{formatEditionDate(edition.date)}</span>
          <span className="edition-count">{allDay.length} 篇</span>
        </div>
        {isToday ? (
          archiveLinks
        ) : (
          <nav className="prev-editions" aria-label="其他刊">
            <Link href="/">← 今日刊</Link>
            {previousDates[0] ? (
              <Link href={`/edition/${previousDates[0]}`}>
                {shortEditionDate(previousDates[0])}
              </Link>
            ) : null}
            <Link href="/stories">全部往期 →</Link>
          </nav>
        )}
      </div>

      {a1 ? (
        <section className="hero" aria-label="A1 頭條">
          {a1.hero ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={a1.hero} alt="" className="hero-img" />
          ) : (
            <div className="hero-img hero-img--empty" />
          )}
          <div className="hero-vignette" />
          <div className="hero-inner">
            <Link href={`/stories/${a1.slug}`} className="hero-copy">
              <span className="hero-kicker">A1 頭條 · {a1.pillar_label}</span>
              <h1>{a1.headline}</h1>
              <p className="hero-dek">{storyTeaser(a1, 90)}</p>
              <span className="hero-cta">讀全文 →</span>
            </Link>
          </div>
        </section>
      ) : (
        <p className="empty-day">
          {isToday ? "今日尚未有通過稿件。" : "呢日未有通過稿件。"}
        </p>
      )}

      {a2.length > 0 ? (
        <section className="headline-strip" aria-label="焦點">
          {a2.map((s) => (
            <Link key={s.slug} className="hl" href={`/stories/${s.slug}`}>
              {s.hero ? (
                <span className="hl-thumb">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={s.hero} alt="" />
                </span>
              ) : (
                <span className="hl-thumb hl-thumb--empty" />
              )}
              <span className="hl-body">
                <span className="hl-pillar">{s.pillar_label}</span>
                <span className="hl-title">{s.headline}</span>
                <span className="hl-dek">{storyTeaser(s, 80)}</span>
              </span>
            </Link>
          ))}
        </section>
      ) : null}

      <section className="body-grid">
        <div className="body-main">
          {inside.map((rail) => {
            const leadCount = rail.items.length >= 3 ? 2 : 1;
            const leads = rail.items.slice(0, leadCount);
            const rest = rail.items.slice(leadCount);
            return (
              <div key={rail.pillar} className="rail-block">
                <h2 className="rail-head">
                  <Link href={`/p/${rail.pillar}`}>{rail.label}</Link>
                </h2>
                {leads.map((lead) => (
                  <Link
                    key={lead.slug}
                    className="rail-lead"
                    href={`/stories/${lead.slug}`}
                  >
                    {lead.hero ? (
                      <span className="rail-lead-thumb">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img src={lead.hero} alt="" />
                      </span>
                    ) : null}
                    <span className="rail-lead-body">
                      <span className="rail-lead-title">{lead.headline}</span>
                      <span className="rail-lead-dek">
                        {storyTeaser(lead, 70)}
                      </span>
                    </span>
                  </Link>
                ))}
                {rest.length > 0 ? (
                  <ul className="rail-list">
                    {rest.map((s) => (
                      <li key={s.slug}>
                        <Link href={`/stories/${s.slug}`}>
                          <span className="rail-bullet">·</span>
                          {s.headline}
                        </Link>
                      </li>
                    ))}
                  </ul>
                ) : null}
              </div>
            );
          })}
        </div>

        <aside className="toc-side">
          <div className="toc-card">
            <div className="section-label">
              {isToday ? "今日目錄" : "當日目錄"} · {allDay.length} 篇
            </div>
            <ol>
              {allDay.map((s, i) => (
                <li key={s.slug}>
                  <Link href={`/stories/${s.slug}`}>
                    <span className="toc-num">
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <span className="toc-pillar">{s.pillar_label}</span>
                    <span className="toc-title">{s.headline}</span>
                  </Link>
                </li>
              ))}
            </ol>
            <div className="toc-archive">{archiveLinks}</div>
          </div>
        </aside>
      </section>

      {more.length > 0 ? (
        <section className="more-grid">
          <div className="section-label">{isToday ? "今日更多" : "當日更多"}</div>
          <ul>
            {more.map((s) => (
              <li key={s.slug}>
                <Link href={`/stories/${s.slug}`}>
                  <span className="more-pillar">{s.pillar_label}</span>
                  <span className="more-title">{s.headline}</span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <div className="front-foot">{archiveLinks}</div>
    </main>
  );
}
