import Link from "next/link";
import { edition, storiesForEdition } from "@/lib/content";

export default function HomePage() {
  const { a1, a2, inside, more } = storiesForEdition(edition);

  return (
    <main>
      {a1 ? (
        <article className="a1">
          <Link href={`/stories/${a1.slug}`}>
            <div className="kicker">A1 · {a1.pillar_label}</div>
            <h1>{a1.headline}</h1>
            <p className="dek">{a1.dek}</p>
          </Link>
          {a1.hero ? (
            <Link href={`/stories/${a1.slug}`} className="a1-hero" aria-label={a1.headline}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={a1.hero} alt="" />
            </Link>
          ) : null}
        </article>
      ) : (
        <p style={{ padding: "2rem 0", color: "var(--ink-muted)" }}>
          今日尚未有通過稿件。
        </p>
      )}

      {a2.length > 0 ? (
        <section className="a2" aria-label="A2">
          {a2.map((s) => (
            <Link key={s.slug} href={`/stories/${s.slug}`} className="a2-item">
              <div className="pillar">{s.pillar_label}</div>
              <h2>{s.headline}</h2>
              <p>{s.dek}</p>
            </Link>
          ))}
        </section>
      ) : null}

      {inside.map((rail) => (
        <section key={rail.pillar} className="rail">
          <h2>
            <Link href={`/p/${rail.pillar}`}>{rail.label}</Link>
          </h2>
          <ul>
            {rail.items.map((s) => (
              <li key={s.slug}>
                <Link href={`/stories/${s.slug}`}>{s.headline}</Link>
              </li>
            ))}
          </ul>
        </section>
      ))}

      {more.length > 0 ? (
        <section className="more">
          <h2>今日更多</h2>
          <ul className="rail" style={{ listStyle: "none", padding: 0 }}>
            {more.map((s) => (
              <li key={s.slug}>
                <Link href={`/stories/${s.slug}`}>
                  {s.pillar_label} · {s.headline}
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </main>
  );
}
