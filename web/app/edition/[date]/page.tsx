import { notFound } from "next/navigation";
import {
  FrontEdition,
  previousEditionDates,
} from "@/app/components/FrontEdition";
import { formatEditionDate, loadMagazine } from "@/lib/content";

type Props = { params: Promise<{ date: string }> };

export const dynamic = "force-dynamic";
export const dynamicParams = true;

export async function generateMetadata({ params }: Props) {
  const { date } = await params;
  return { title: `${formatEditionDate(date)}刊` };
}

export default async function EditionPage({ params }: Props) {
  const { date } = await params;
  const { stories, edition: latest, editions } = await loadMagazine();
  const ed = editions[date];
  if (!ed) notFound();
  return (
    <FrontEdition
      stories={stories}
      edition={ed}
      previousDates={previousEditionDates(editions, date)}
      isToday={date === latest.date}
    />
  );
}
