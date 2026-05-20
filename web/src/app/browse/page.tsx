// Server component — fetches all 4 reference sources in parallel, hands the
// data to the client `BrowseTabs` component for the toggle/render layer.
// Following Next.js App Router conventions: keep data-fetching on the server,
// interactivity in client components.

import { listHouses, listPlanets, listZodiac, dashaTenure } from "@/lib/api";
import type { DashaTenureResponse } from "@/lib/api";
import { BrowseTabs } from "@/components/BrowseTabs";

type RefItem = Record<string, unknown>;
type RefList = { count: number; items: RefItem[] };

export default async function BrowsePage() {
  // Fetch all 4 sources in parallel. We use Promise.allSettled so one slow or
  // failing endpoint doesn't blank the whole page — each tab can independently
  // render an "unavailable" state.
  const [housesR, planetsR, zodiacR, dashaR] = await Promise.allSettled([
    listHouses() as Promise<RefList>,
    listPlanets() as Promise<RefList>,
    listZodiac() as Promise<RefList>,
    dashaTenure(),
  ]);

  const houses  = housesR.status  === "fulfilled" ? housesR.value  : null;
  const planets = planetsR.status === "fulfilled" ? planetsR.value : null;
  const zodiac  = zodiacR.status  === "fulfilled" ? zodiacR.value  : null;
  const dasha: DashaTenureResponse | null =
    dashaR.status === "fulfilled" ? dashaR.value : null;

  const failed = [housesR, planetsR, zodiacR, dashaR].filter((r) => r.status === "rejected");

  return (
    <>
      <header className="mb-6 text-center">
        <h1 className="text-4xl text-[var(--accent-gold)]">Browse the Cosmos</h1>
        <p className="mt-1 text-sm text-[var(--text-muted)]">
          Houses, planets, signs, and the 120-year Vimshottari cycle — all in one place
        </p>
      </header>

      {failed.length > 0 && failed.length === 4 && (
        <section className="my-6 rounded-lg border border-[rgba(248,113,113,0.35)] bg-[rgba(248,113,113,0.08)] p-4 text-sm text-[#f87171]">
          Couldn&apos;t reach the backend. Is the API running at <code>{process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"}</code>?
        </section>
      )}

      <BrowseTabs houses={houses} planets={planets} zodiac={zodiac} dasha={dasha} />
    </>
  );
}
