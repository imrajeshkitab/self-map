import Link from "next/link";
import { CosmicSearch } from "@/components/CosmicSearch";

export default function HomePage() {
  return (
    <>
      <header className="my-10 text-center">
        <h1 className="text-5xl text-[var(--accent-gold)]">Cosmic Insight</h1>
        <p className="mt-3 text-base text-[var(--text-muted)]">
          Discover the wisdom of Vedic Astrology
        </p>
      </header>

      <CosmicSearch />

      <section className="mx-auto grid max-w-3xl grid-cols-1 gap-4 md:grid-cols-2">
        <Tile
          href="/ask"
          title="Ask the Moment"
          subtitle="Prashna · your question, answered from the sky at this instant"
          icon="🪔"
        />
        <Tile
          href="/today"
          title="Today's Sky"
          subtitle="A live Vedic snapshot — no birth data needed"
          icon="✨"
        />
        <Tile
          href="/browse"
          title="Browse the Cosmos"
          subtitle="Explore every house, planet, and zodiac sign"
          icon="🏛️"
        />
      </section>
    </>
  );
}

function Tile({
  href, title, subtitle, icon,
}: { href: string; title: string; subtitle: string; icon: string }) {
  return (
    <Link href={href} className="block">
      <div className="glass group h-full p-5 transition hover:-translate-y-[1px] hover:border-[rgba(212,175,55,0.35)]">
        <div className="mb-2 text-2xl">{icon}</div>
        <div className="display text-lg text-[var(--accent-gold)]">{title}</div>
        <div className="mt-1 text-sm text-[var(--text-muted)]">{subtitle}</div>
      </div>
    </Link>
  );
}
