import Link from "next/link";
import {
  edition,
  formatEditionDate,
  storiesForEdition,
  type Story,
} from "@/lib/content";

function todayStories(
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

export default function HomePage() {
  const { a1, a2, inside, more } = storiesForEdition(edition);
  const allToday = todayStories(a1, a2, inside, more);

  return (
    <main className="front">
      <div className="edition-bar">
        <div>
          <strong>今日刊</strong>
          <span>{formatEditionDate(edition.date)}</span>
          <span className="edition-count">{allToday.length} 篇</span>
        </div>
        <Link href={`/edition/${edition.date}`}>完整今日版 →</Link>
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
              <p className="hero-dek">{a1.dek}</p>
              <span className="hero-cta">讀全文 →</span>
            </Link>
          </div>
        </section>
      ) : (
        <p className="empty-day">今日尚未有通過稿件。</p>
      )}

      {a2.length > 0 ? (
        <section className="headline-strip" aria-label="今日焦點">
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
              </span>
            </Link>
          ))}
        </section>
      ) : null}

      <section className="body-grid">
        <div className="body-main">
          {inside.map((rail) => {
            const lead = rail.items[0];
            const rest = rail.items.slice(1);
            return (
              <div key={rail.pillar} className="rail-block">
                <h2 className="rail-head">
                  <Link href={`/p/${rail.pillar}`}>{rail.label}</Link>
                </h2>
                {lead ? (
                  <Link className="rail-lead" href={`/stories/${lead.slug}`}>
                    {lead.hero ? (
                      <span className="rail-lead-thumb">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img src={lead.hero} alt="" />
                      </span>
                    ) : null}
                    <span className="rail-lead-body">
                      <span className="rail-lead-title">{lead.headline}</span>
                      <span className="rail-lead-dek">{lead.dek}</span>
                    </span>
                  </Link>
                ) : null}
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
              今日目錄 · {allToday.length} 篇
            </div>
            <ol>
              {allToday.map((s, i) => (
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
            <Link className="toc-full" href={`/edition/${edition.date}`}>
              完整今日版 →
            </Link>
          </div>
        </aside>
      </section>

      {more.length > 0 ? (
        <section className="more-grid">
          <div className="section-label">今日更多</div>
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

      <p className="front-foot">
        <Link href={`/edition/${edition.date}`}>今日刊存檔</Link>
        {" · "}
        <Link href="/stories">往期</Link>
      </p>
    </main>
  );
}
