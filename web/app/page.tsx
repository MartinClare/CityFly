import {
  FrontEdition,
  previousEditionDates,
} from "./components/FrontEdition";
import { loadMagazine } from "@/lib/content";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const { stories, edition, editions } = await loadMagazine();
  return (
    <FrontEdition
      stories={stories}
      edition={edition}
      previousDates={previousEditionDates(editions, edition.date)}
      isToday
    />
  );
}
