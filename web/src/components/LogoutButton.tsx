/**
 * LogoutButton — clears the admin session cookie and returns to /login.
 * Used on the logs pages so a viewer can end their session.
 */

"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export function LogoutButton() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  async function logout() {
    if (busy) return;
    setBusy(true);
    try {
      await fetch("/api/admin/login", { method: "DELETE" });
    } catch {
      // ignore — we redirect regardless
    }
    router.replace("/login");
    router.refresh();
  }

  return (
    <button
      type="button"
      onClick={logout}
      disabled={busy}
      className="rounded-full border border-[var(--border-glass)] bg-[rgba(15,17,35,0.7)] px-3 py-1 text-xs text-[var(--text-muted)] transition hover:border-[rgba(248,113,113,0.4)] hover:text-[#f87171] disabled:opacity-60"
    >
      {busy ? "Signing out…" : "Sign out"}
    </button>
  );
}
