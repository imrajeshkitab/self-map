// Server component — fetches the three reference lists in parallel.
import { listHouses, listPlanets, listZodiac } from "@/lib/api";

type ReferenceItem = Record<string, unknown> & { keywords?: string };

type RefList = { count: number; items: ReferenceItem[] };

export default async function BrowsePage() {
  let houses: RefList | null = null;
  let planets: RefList | null = null;
  let zodiac: RefList | null = null;
  let error: string | null = null;
  try {
    [houses, planets, zodiac] = await Promise.all([
      listHouses() as Promise<RefList>,
      listPlanets() as Promise<RefList>,
      listZodiac() as Promise<RefList>,
    ]);
  } catch (e) {
    error = e instanceof Error ? e.message : "Could not load reference data.";
  }

  return (
    <>
      <header className="mb-6 text-center">
        <h1 className="text-4xl text-[var(--accent-gold)]">Browse the Cosmos</h1>
        <p className="mt-1 text-sm text-[var(--text-muted)]">
          Every Bhava, Graha, and Rashi — with significance and keywords
        </p>
      </header>

      {error && (
        <section className="my-6 rounded-lg border border-[rgba(248,113,113,0.35)] bg-[rgba(248,113,113,0.08)] p-4 text-sm text-[#f87171]">
          {error}
        </section>
      )}

      {houses && (
        <Section title={`12 Houses (Bhavas)`} count={houses.count}>
          {houses.items.map((h) => (
            <ItemCard
              key={String(h.house_number)}
              title={`${h.house_number}. ${h.english_name} (${h.sanskrit_name})`}
              accent={`Ruling sign: ${h.ruling_sign} · Ruling planet: ${h.ruling_planet}`}
              body={String(h.significance ?? "")}
              keywords={String(h.keywords ?? "")}
            />
          ))}
        </Section>
      )}

      {planets && (
        <Section title="9 Planets (Grahas)" count={planets.count}>
          {planets.items.map((p) => (
            <ItemCard
              key={String(p.english_name)}
              title={`${p.symbol ?? ""} ${p.english_name} (${p.sanskrit_name})`}
              accent={`Rules: ${p.rules_sign} · Exalted in ${p.exalted_in} · Debilitated in ${p.debilitated_in}`}
              body={String(p.significance ?? "")}
              keywords={String(p.keywords ?? "")}
            />
          ))}
        </Section>
      )}

      {zodiac && (
        <Section title="12 Zodiac Signs (Rashis)" count={zodiac.count}>
          {zodiac.items.map((z) => (
            <ItemCard
              key={String(z.sign_number)}
              title={`${z.sign_number}. ${z.english_name} (${z.sanskrit_name})`}
              accent={`Lord: ${z.ruling_planet} · ${z.element} · ${z.quality}`}
              body={String(z.significance ?? "")}
              keywords={String(z.keywords ?? "")}
            />
          ))}
        </Section>
      )}
    </>
  );
}

function Section({
  title, count, children,
}: { title: string; count: number; children: React.ReactNode }) {
  return (
    <section className="mb-10">
      <h2 className="display mb-3 text-2xl text-[var(--accent-gold)]">
        {title} <span className="ml-2 text-sm font-normal text-[var(--text-muted)]">· {count} entries</span>
      </h2>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">{children}</div>
    </section>
  );
}

function ItemCard({
  title, accent, body, keywords,
}: { title: string; accent: string; body: string; keywords: string }) {
  return (
    <article className="glass p-4">
      <h3 className="display text-base text-[var(--accent-gold)]">{title}</h3>
      <p className="mt-1 text-xs text-[var(--text-muted)]">{accent}</p>
      {body && <p className="mt-2 text-sm leading-relaxed text-[var(--text-main)]">{body}</p>}
      {keywords && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {keywords.split(/[,;]\s*/).filter(Boolean).slice(0, 12).map((k) => (
            <span
              key={k}
              className="rounded-full border border-[var(--border-glass)] bg-[rgba(15,17,35,0.6)] px-2 py-[2px] text-[0.7rem] text-[var(--text-muted)]"
            >
              {k}
            </span>
          ))}
        </div>
      )}
    </article>
  );
}
