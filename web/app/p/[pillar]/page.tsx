import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import {
  edition,
  formatEditionDate,
  PILLAR_ORDER,
  stories,
} from "@/lib/content";

type Props = { params: Promise<{ pillar: string }> };

export function generateStaticParams() {
  return PILLAR_ORDER.map((pillar) => ({ pillar }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { pillar } = await params;
  const label = edition.pillar_labels?.[pillar] || pillar;
  return {
    title: label,
    description: `City Sight · ${label}`,
  };
}

export default async function PillarPage({ params }: Props) {
  const { pillar } = await params;
  if (!PILLAR_ORDER.includes(pillar as (typeof PILLAR_ORDER)[number])) {
    notFound();
  }
  const label = edition.pillar_labels?.[pillar] || pillar;
  const items = stories
    .filter((s) => s.pillar === pillar)
    .sort((a, b) => b.as_of.localeCompare(a.as_of) || a.slug.localeCompare(b.slug));

  const lead = items[0];
  const focus = items.slice(1, 4);
  const rest = items.slice(4);

  return (
    <main className="front pillar-front">
      <div className="edition-bar">
        <div>
          <strong>{label}</strong>
          <span>{items.length} 篇</span>
        </div>
        <Link href="/">← 今日刊</Link>
      </div>

      {lead ? (
        <section className="hero" aria-label={`${label} 頭條`}>
          {lead.hero ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={lead.hero} alt="" className="hero-img" />
          ) : (
            <div className="hero-img hero-img--empty" />
          )}
          <div className="hero-vignette" />
          <div className="hero-inner">
            <Link href={`/stories/${lead.slug}`} className="hero-copy">
              <span className="hero-kicker">
                {label} · {formatEditionDate(lead.as_of)}
              </span>
              <h1>{lead.headline}</h1>
              {lead.dek ? <p className="hero-dek">{lead.dek}</p> : null}
              <span className="hero-cta">讀全文 →</span>
            </Link>
          </div>
        </section>
      ) : (
        <p className="empty-day">呢個主題暫時未有通過稿件。</p>
      )}

      {focus.length > 0 ? (
        <section className="headline-strip" aria-label={`${label} 焦點`}>
          {focus.map((s) => (
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
                <span className="hl-pillar">{formatEditionDate(s.as_of)}</span>
                <span className="hl-title">{s.headline}</span>
                {s.dek ? <span className="hl-dek">{s.dek}</span> : null}
              </span>
            </Link>
          ))}
        </section>
      ) : null}

      {rest.length > 0 ? (
        <section className="pillar-more">
          <div className="section-label">更多{label}</div>
          <div className="pillar-more-grid">
            {rest.map((s) => (
              <Link key={s.slug} className="pillar-card" href={`/stories/${s.slug}`}>
                {s.hero ? (
                  <span className="pillar-card-thumb">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={s.hero} alt="" />
                  </span>
                ) : (
                  <span className="pillar-card-thumb pillar-card-thumb--empty" />
                )}
                <span className="pillar-card-body">
                  <span className="pillar-card-date">
                    {formatEditionDate(s.as_of)}
                  </span>
                  <span className="pillar-card-title">{s.headline}</span>
                  {s.dek ? (
                    <span className="pillar-card-dek">{s.dek}</span>
                  ) : null}
                </span>
              </Link>
            ))}
          </div>
        </section>
      ) : null}

      <p className="front-foot">
        <Link href="/">今日刊</Link>
        {" · "}
        <Link href="/stories">往期</Link>
      </p>
    </main>
  );
}
