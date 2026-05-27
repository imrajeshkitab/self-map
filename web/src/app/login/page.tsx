/**
 * /login — password gate for the admin logs.
 *
 * Posts the typed password to /api/admin/login, which verifies it against the
 * server-only ADMIN_LOGS_PASSWORD and sets an httpOnly session cookie. On
 * success we navigate to the originally-requested /admin page (or /admin/audit).
 */

"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const from = params.get("from");
  const configError = params.get("error") === "unconfigured";

  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!password || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch("/api/admin/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setError(body?.error ?? "Login failed.");
        setSubmitting(false);
        return;
      }
      // Full navigation so the server layout re-reads the fresh cookie.
      const target =
        from && from.startsWith("/admin") ? from : "/admin/audit";
      router.replace(target);
      router.refresh();
    } catch {
      setError("Network error — is the app running?");
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto mt-20 max-w-sm">
      <header className="mb-6 text-center">
        <h1 className="text-3xl text-[var(--accent-gold)]">Logs access</h1>
        <p className="mt-1 text-sm text-[var(--text-muted)]">
          Enter the admin password to view the query logs.
        </p>
      </header>

      {configError && (
        <div className="mb-4 rounded-lg border border-[rgba(248,113,113,0.35)] bg-[rgba(248,113,113,0.08)] p-3 text-xs text-[#f87171]">
          Admin auth is not configured on the server (missing
          ADMIN_LOGS_PASSWORD / ADMIN_SESSION_SECRET).
        </div>
      )}

      <form onSubmit={submit} className="glass flex flex-col gap-3 p-5">
        <label className="text-xs uppercase tracking-widest text-[var(--text-muted)]">
          Password
        </label>
        <input
          type="password"
          autoFocus
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full rounded-lg border border-[var(--border-glass)] bg-[rgba(10,11,22,0.7)] p-3 text-[var(--text-main)] focus:border-[var(--accent-purple)] focus:outline-none focus:ring-2 focus:ring-[rgba(139,92,246,0.2)]"
          placeholder="••••••••"
        />
        {error && <p className="text-sm text-[#f87171]">{error}</p>}
        <button
          type="submit"
          disabled={submitting || !password}
          className="rounded-lg border border-[rgba(212,175,55,0.4)] bg-gradient-to-br from-[rgba(139,92,246,0.4)] to-[rgba(212,175,55,0.25)] px-5 py-2 text-sm font-medium text-white transition hover:shadow-[0_4px_18px_rgba(139,92,246,0.3)] disabled:cursor-not-allowed disabled:opacity-60"
        >
          {submitting ? "Checking…" : "Unlock logs →"}
        </button>
      </form>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}
