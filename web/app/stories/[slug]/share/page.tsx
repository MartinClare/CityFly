import type { Metadata } from "next";
import { redirect, notFound } from "next/navigation";
import { loadMagazine, storyBySlug } from "@/lib/content";

type Props = { params: Promise<{ slug: string }> };

export const revalidate = 30;
export const dynamicParams = true;

/**
 * Thin share landing for Facebook link posts.
 * OG image prefers the FB-only callout; humans redirect to the real story.
 */
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const { stories } = await loadMagazine();
  const story = storyBySlug(stories, slug);
  if (!story) return {};
  const image = story.fb_hero || story.hero;
  return {
    title: story.og_title || story.headline,
    description: story.og_description || story.dek,
    openGraph: {
      title: story.og_title || story.headline,
      description: story.og_description || story.dek,
      url: `https://www.citysight.net/stories/${story.slug}`,
      images: image ? [image] : undefined,
    },
  };
}

export default async function StorySharePage({ params }: Props) {
  const { slug } = await params;
  const { stories } = await loadMagazine();
  const story = storyBySlug(stories, slug);
  if (!story) notFound();
  redirect(`/stories/${story.slug}`);
}
