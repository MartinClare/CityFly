import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import ReactMarkdown from "react-markdown";
import { stories, storyBySlug } from "@/lib/content";

type Props = { params: Promise<{ slug: string }> };

export function generateStaticParams() {
  return stories.map((s) => ({ slug: s.slug }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const story = storyBySlug(slug);
  if (!story) return {};
  return {
    title: story.og_title || story.headline,
    description: story.og_description || story.dek,
    openGraph: {
      title: story.og_title || story.headline,
      description: story.og_description || story.dek,
      images: story.hero ? [story.hero] : undefined,
    },
  };
}

export default async function StoryPage({ params }: Props) {
  const { slug } = await params;
  const story = storyBySlug(slug);
  if (!story) notFound();

  const shareUrl = `https://www.citysight.net/stories/${story.slug}`;
  const fb = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(shareUrl)}`;
  const wa = `https://wa.me/?text=${encodeURIComponent(`${story.headline} ${shareUrl}`)}`;

  return (
    <article className="article">
      <div className="kicker" style={{ color: "var(--accent)", fontSize: "0.8rem" }}>
        <Link href={`/p/${story.pillar}`}>{story.pillar_label}</Link>
        {" · "}
        {story.as_of}
      </div>
      <h1>{story.headline}</h1>
      <p className="dek">{story.dek}</p>
      {story.hero ? (
        <div className="article-hero">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={story.hero} alt="" />
        </div>
      ) : null}

      <div className="share">
        <a href={fb} target="_blank" rel="noreferrer">
          Facebook
        </a>
        <a href={wa} target="_blank" rel="noreferrer">
          WhatsApp
        </a>
        <a href={shareUrl}>複製連結用網址</a>
      </div>

      <div className="prose">
        <ReactMarkdown>{story.body_md}</ReactMarkdown>
      </div>

      {story.sources?.length ? (
        <section className="sources">
          <h2>來源</h2>
          <ul>
            {story.sources.map((src, i) => (
              <li key={`${src.url}-${i}`}>
                {src.url ? (
                  <a href={src.url} target="_blank" rel="noreferrer">
                    {src.source ? `${src.source}：` : ""}
                    {src.title || src.url}
                  </a>
                ) : (
                  <span>
                    {src.source ? `${src.source}：` : ""}
                    {src.title}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <p className="disclaimer">
        本文只作新聞、教育及一般資訊用途，不構成投資、置業、法律、按揭或財務建議。
      </p>
    </article>
  );
}
