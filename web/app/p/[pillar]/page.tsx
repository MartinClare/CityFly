import Link from "next/link";
import { notFound } from "next/navigation";
import { edition, PILLAR_ORDER, stories } from "@/lib/content";

type Props = { params: Promise<{ pillar: string }> };

export function generateStaticParams() {
  return PILLAR_ORDER.map((pillar) => ({ pillar }));
}

export default async function PillarPage({ params }: Props) {
  const { pillar } = await params;
  if (!PILLAR_ORDER.includes(pillar as (typeof PILLAR_ORDER)[number])) {
    notFound();
  }
  const label = edition.pillar_labels?.[pillar] || pillar;
  const items = stories
    .filter((s) => s.pillar === pillar)
    .sort((a, b) => b.as_of.localeCompare(a.as_of));

  return (
    <main>
      <h1 className="page-title">{label}</h1>
      <ul style={{ listStyle: "none", padding: 0 }}>
        {items.map((s) => (
          <li key={s.slug} className="archive-day">
            <Link href={`/stories/${s.slug}`}>
              <div style={{ color: "var(--ink-muted)", fontSize: "0.85rem" }}>
                {s.as_of}
              </div>
              <strong>{s.headline}</strong>
              <p style={{ color: "var(--ink-muted)", margin: "0.35rem 0 0" }}>
                {s.dek}
              </p>
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
