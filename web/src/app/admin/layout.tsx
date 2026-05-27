/**
 * /admin/* gate
 * =============
 * Authoritative auth check for everything under /admin (the logs pages).
 * Server component: reads the session cookie, verifies the HMAC signature
 * against ADMIN_SESSION_SECRET, and redirects to /login if it's missing,
 * expired, or forged. This runs before any child page renders — including
 * the client-side detail page — so the gate can't be bypassed from the
 * browser. proxy.ts does an earlier optimistic redirect; this is the real
 * lock.
 */

import { redirect } from "next/navigation";
import { cookies } from "next/headers";
import { ADMIN_COOKIE, verifySession } from "@/lib/adminAuth";

export const dynamic = "force-dynamic";

export default async function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const secret = process.env.ADMIN_SESSION_SECRET;
  // Misconfigured server → deny rather than expose the logs.
  if (!secret || !process.env.ADMIN_LOGS_PASSWORD) {
    redirect("/login?error=unconfigured");
  }

  const jar = await cookies();
  const token = jar.get(ADMIN_COOKIE)?.value;
  const ok = await verifySession(secret, token);
  if (!ok) {
    redirect("/login");
  }

  return <>{children}</>;
}
