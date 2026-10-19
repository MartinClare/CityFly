export type Source = {
  title?: string;
  url?: string;
  source?: string;
};

export type Story = {
  slug: string;
  as_of: string;
  pillar: string;
  pillar_label: string;
  headline: string;
  dek: string;
  placement?: string;
  hero?: string | null;
  body_md: string;
  og_title: string;
  og_description: string;
  disclaimer_required?: boolean;
  sources: Source[];
};

export type Edition = {
  date: string;
  a1: string | null;
  a2: string[];
  inside: Record<string, string[]>;
  more: string[];
  pillar_labels: Record<string, string>;
};

export const PILLAR_ORDER = [
  "property",
  "tech",
  "city",
  "mobility",
  "economy",
] as const;

import storiesJson from "@/content/stories.json";
import editionJson from "@/content/edition.json";
import editionsJson from "@/content/editions.json";

const bundled = {
  stories: storiesJson as Story[],
  edition: editionJson as Edition,
  editions: editionsJson as Record<string, Edition>,
};

const DESK = (process.env.DESK_CONTENT_URL || "https://desk.citysight.net").replace(/\/$/, "");
const MODEL_COMMENT = /<!--\s*model:[^>]*-->\s*/g;

function withoutModelComment(text: string | undefined): string {
  return (text || "").replace(MODEL_COMMENT, "").trim();
}

/** Body packs start with # title + dek and end with ## 來源; the story page already renders those. */
function bodyWithoutChrome(body: string, headline: string, dek: string): string {
  let text = withoutModelComment(body);
  // Drop leading H1 (same as page <h1>)
  text = text.replace(/^#\s+.+\n+/, "");
  const dekLine = (dek || "").trim();
  if (dekLine && text.startsWith(dekLine)) {
    text = text.slice(dekLine.length).replace(/^\n+/, "");
  }
  // Drop trailing source block + disclaimer (page template repeats them)
  text = text.replace(/\n##\s*來源[\s\S]*$/u, "").trim();
  text = text.replace(/\n本文只作新聞、教育及一般資訊用途[\s\S]*$/u, "").trim();
  // If the first paragraph still equals the headline, drop it
  const head = (headline || "").trim();
  if (head && text.startsWith(head)) {
    text = text.slice(head.length).replace(/^\n+/, "");
  }
  return text;
}

function cleanStory(story: Story): Story {
  const headline = withoutModelComment(story.headline);
  const dek = withoutModelComment(story.dek);
  return {
    ...story,
    headline,
    dek,
    body_md: bodyWithoutChrome(story.body_md, headline, dek),
    og_title: withoutModelComment(story.og_title),
    og_description: withoutModelComment(story.og_description),
  };
}

export type Magazine = {
  stories: Story[];
  edition: Edition;
  editions: Record<string, Edition>;
};

/** Approved stories from the desk. A desk delete drops the story within about 30 seconds. */
export async function loadMagazine(): Promise<Magazine> {
  try {
    const res = await fetch(`${DESK}/published/magazine.json`, { next: { revalidate: 30 } });
    if (!res.ok) return { ...bundled, stories: bundled.stories.map(cleanStory) };
    const data = (await res.json()) as Magazine;
    if (!data?.edition || !Array.isArray(data.stories)) {
      return { ...bundled, stories: bundled.stories.map(cleanStory) };
    }
    return {
      stories: data.stories.map(cleanStory),
      edition: data.edition,
      editions: data.editions || {},
    };
  } catch {
    return {
      ...bundled,
      stories: bundled.stories.map(cleanStory),
    };
  }
}

export function storyBySlug(stories: Story[], slug: string): Story | undefined {
  return stories.find((s) => s.slug === slug);
}

export function storiesForEdition(ed: Edition, stories: Story[]): {
  a1?: Story;
  a2: Story[];
  inside: { pillar: string; label: string; items: Story[] }[];
  more: Story[];
} {
  const a1 = ed.a1 ? storyBySlug(stories, ed.a1) : undefined;
  const a2 = (ed.a2 || []).map((slug) => storyBySlug(stories, slug)).filter(Boolean) as Story[];
  const inside = PILLAR_ORDER.filter((p) => (ed.inside?.[p] || []).length > 0).map(
    (pillar) => ({
      pillar,
      label: ed.pillar_labels?.[pillar] || pillar,
      items: (ed.inside[pillar] || [])
        .map((slug) => storyBySlug(stories, slug))
        .filter(Boolean) as Story[],
    }),
  );
  const more = (ed.more || []).map((slug) => storyBySlug(stories, slug)).filter(Boolean) as Story[];
  return { a1, a2, inside, more };
}

export function formatEditionDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  if (!y || !m || !d) return iso;
  return `${y}年${m}月${d}日`;
}

/** Longer article teaser from body (dek alone is often one short line). */
export function storyTeaser(story: Story, maxCjk = 110): string {
  const raw = story.body_md || "";
  let text = raw.replace(/<!--[\s\S]*?-->/g, "");
  text = text.replace(/^#+\s+.+$/gm, "");
  text = text.replace(/!\[[^\]]*\]\([^)]*\)/g, "");
  text = text.replace(/\[([^\]]*)\]\([^)]*\)/g, "$1");
  text = text.replace(/[*_`>#]/g, "");

  const paras = text
    .split(/\n+/)
    .map((p) => p.trim())
    .filter(Boolean)
    .filter((p) => p !== story.headline && p !== story.dek && !p.startsWith("來源"));

  let out = "";
  let cjk = 0;
  for (const p of paras) {
    for (const ch of p) {
      out += ch;
      if (/[\u4e00-\u9fff]/.test(ch)) cjk += 1;
      if (cjk >= maxCjk) {
        return out.replace(/\s+$/u, "") + "……";
      }
    }
  }

  const trimmed = out.trim();
  if (trimmed.length >= 20) return trimmed;
  return (story.dek || "").trim();
}
