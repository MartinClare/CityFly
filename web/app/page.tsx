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

      {allToday.length > 0 ? (
        <nav className="today-toc" aria-label="今日目錄">
          <div className="section-label">今日目錄</div>
          <ol>
            {allToday.map((s, i) => (
              <li key={s.slug}>
                <Link href={`/stories/${s.slug}`}>
                  <span className="toc-num">{String(i + 1).padStart(2, "0")}</span>
                  <span className="toc-pillar">{s.pillar_label}</span>
                  <span className="toc-title">{s.headline}</span>
                </Link>
              </li>
            ))}
          </ol>
        </nav>
      ) : null}

      {a1 ? (
        <section className="a1-section" aria-label="A1 頭條">
          <Link href={`/stories/${a1.slug}`} className="a1-block">
            {a1.hero ? (
              <div className="a1-media">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={a1.hero} alt="" />
              </div>
            ) : null}
            <div className="a1-copy">
              <div className="kicker">A1 頭條 · {a1.pillar_label}</div>
              <h1>{a1.headline}</h1>
              <p className="dek">{a1.dek}</p>
              <span className="read-cta">讀全文 →</span>
            </div>
          </Link>
        </section>
      ) : (
        <p className="empty-day">今日尚未有通過稿件。</p>
      )}

      {a2.length > 0 ? (
        <section className="a2" aria-label="今日焦點">
          <div className="section-label">今日焦點</div>
          <div className="a2-grid">
            {a2.map((s) => (
              <Link key={s.slug} href={`/stories/${s.slug}`} className="a2-card">
                {s.hero ? (
                  <div className="a2-thumb">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={s.hero} alt="" />
                  </div>
                ) : null}
                <div className="pillar">{s.pillar_label}</div>
                <h2>{s.headline}</h2>
                <p>{s.dek}</p>
              </Link>
            ))}
          </div>
        </section>
      ) : null}

      {inside.length > 0 ? (
        <section className="inside" aria-label="分類">
          <div className="section-label">今日分類</div>
          <div className="inside-grid">
            {inside.map((rail) => (
              <div key={rail.pillar} className="rail-block">
                <h2>
                  <Link href={`/p/${rail.pillar}`}>{rail.label}</Link>
                </h2>
                <ul>
                  {rail.items.map((s) => (
                    <li key={s.slug}>
                      <Link
                        href={`/stories/${s.slug}`}
                        className={s.hero ? "rail-row" : "rail-row rail-row--text"}
                      >
                        {s.hero ? (
                          <span className="rail-thumb">
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img src={s.hero} alt="" />
                          </span>
                        ) : null}
                        <span className="rail-text">{s.headline}</span>
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {more.length > 0 ? (
        <section className="more">
          <div className="section-label">今日更多</div>
          <ul className="more-list">
            {more.map((s) => (
              <li key={s.slug}>
                <Link href={`/stories/${s.slug}`}>
                  <span className="more-pillar">{s.pillar_label}</span>
                  <span>{s.headline}</span>
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
