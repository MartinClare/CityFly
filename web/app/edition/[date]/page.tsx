import Link from "next/link";
import { notFound } from "next/navigation";
import { formatEditionDate, loadMagazine, storiesForEdition } from "@/lib/content";

type Props = { params: Promise<{ date: string }> };

export const revalidate = 30;
export const dynamicParams = true;

export async function generateStaticParams() {
  const { editions } = await loadMagazine();
  return Object.keys(editions).map((date) => ({ date }));
}

export default async function EditionPage({ params }: Props) {
  const { date } = await params;
  const { stories, editions } = await loadMagazine();
  const ed = editions[date];
  if (!ed) notFound();
  const { a1, a2, inside, more } = storiesForEdition(ed, stories);

  return (
    <main>
      <h1 className="page-title">{formatEditionDate(date)} 刊</h1>
      {a1 ? (
        <section className="a1">
          <Link href={`/stories/${a1.slug}`}>
            <div className="kicker">A1 · {a1.pillar_label}</div>
            <h1>{a1.headline}</h1>
            <p className="dek">{a1.dek}</p>
          </Link>
        </section>
      ) : null}
      <section className="a2">
        {a2.map((s) => (
          <Link key={s.slug} href={`/stories/${s.slug}`} className="a2-item">
            <div className="pillar">{s.pillar_label}</div>
            <h2>{s.headline}</h2>
          </Link>
        ))}
      </section>
      {inside.map((rail) => (
        <section key={rail.pillar} className="rail">
          <h2>{rail.label}</h2>
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
          <h2>當日更多</h2>
          <ul style={{ listStyle: "none", padding: 0 }}>
            {more.map((s) => (
              <li key={s.slug}>
                <Link href={`/stories/${s.slug}`}>{s.headline}</Link>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </main>
  );
}
