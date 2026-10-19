import {
  FrontEdition,
  previousEditionDates,
} from "./components/FrontEdition";
import { loadMagazine } from "@/lib/content";

export const revalidate = 30;

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
