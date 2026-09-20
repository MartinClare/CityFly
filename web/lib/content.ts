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

export const stories = storiesJson as Story[];
export const edition = editionJson as Edition;
export const editions = editionsJson as Record<string, Edition>;

export function storyBySlug(slug: string): Story | undefined {
  return stories.find((s) => s.slug === slug);
}

export function storiesForEdition(ed: Edition): {
  a1?: Story;
  a2: Story[];
  inside: { pillar: string; label: string; items: Story[] }[];
  more: Story[];
} {
  const a1 = ed.a1 ? storyBySlug(ed.a1) : undefined;
  const a2 = (ed.a2 || []).map(storyBySlug).filter(Boolean) as Story[];
  const inside = PILLAR_ORDER.filter((p) => (ed.inside?.[p] || []).length > 0).map(
    (pillar) => ({
      pillar,
      label: ed.pillar_labels?.[pillar] || pillar,
      items: (ed.inside[pillar] || [])
        .map(storyBySlug)
        .filter(Boolean) as Story[],
    }),
  );
  const more = (ed.more || []).map(storyBySlug).filter(Boolean) as Story[];
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
