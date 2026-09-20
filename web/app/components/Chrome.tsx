import Link from "next/link";
import { edition, formatEditionDate, PILLAR_ORDER } from "@/lib/content";

const labels = edition.pillar_labels || {
  property: "樓市與生活",
  tech: "科技改變生活",
  city: "城市大變身",
  mobility: "基建與交通",
  economy: "經濟、錢與機會",
};

export function Masthead({
  date,
  showDate = true,
}: {
  date?: string;
  showDate?: boolean;
}) {
  const d = date || edition.date;
  return (
    <header className="masthead">
      <Link href="/" className="logo">
        CS Magazine
        <span>City Sight</span>
      </Link>
      {showDate ? (
        <div className="edition-date">{formatEditionDate(d)} · 香港城市變化</div>
      ) : null}
      <nav className="pillar-nav" aria-label="主題">
        {PILLAR_ORDER.map((id) => (
          <Link key={id} href={`/p/${id}`}>
            {labels[id] || id}
          </Link>
        ))}
        <Link href="/stories">往期</Link>
        <Link href="/about">關於</Link>
      </nav>
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="site-footer site-shell">
      <nav>
        <Link href="/">今日</Link>
        <Link href="/stories">往期</Link>
        <Link href="/about">關於 City Sight</Link>
      </nav>
      <p>City Sight · CS Magazine · 香港城市變化雜誌</p>
    </footer>
  );
}
