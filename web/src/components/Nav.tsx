import Link from "next/link";

const links = [
  { href: "/",        label: "Search" },
  { href: "/today",   label: "Today's Sky" },
  { href: "/ask",     label: "Ask the Moment" },
  { href: "/browse",  label: "Browse" },
  { href: "/admin/audit", label: "Logs" },
];

export function Nav() {
  return (
    <nav className="mb-8 flex flex-wrap items-center justify-center gap-x-3 gap-y-2 text-sm text-[var(--text-muted)]">
      {links.map((l, i) => (
        <span key={l.href} className="flex items-center gap-x-3">
          <Link
            href={l.href}
            className="transition-colors hover:text-[var(--accent-gold)]"
          >
            {l.label}
          </Link>
          {i < links.length - 1 && <span>·</span>}
        </span>
      ))}
    </nav>
  );
}
