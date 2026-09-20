import Link from "next/link";
import { editions, formatEditionDate, stories } from "@/lib/content";

export const metadata = { title: "往期" };

export default function StoriesIndexPage() {
  const byDay = Object.keys(editions).sort().reverse();

  return (
    <main>
      <h1 className="page-title">往期</h1>
      {byDay.map((date) => {
        const dayStories = stories.filter((s) => s.as_of === date);
        return (
          <section key={date} className="archive-day">
            <h2>
              <Link href={`/edition/${date}`}>{formatEditionDate(date)}</Link>
            </h2>
            <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
              {dayStories.map((s) => (
                <li key={s.slug} style={{ padding: "0.4rem 0" }}>
                  <Link href={`/stories/${s.slug}`}>
                    {s.pillar_label} · {s.headline}
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        );
      })}
    </main>
  );
}
