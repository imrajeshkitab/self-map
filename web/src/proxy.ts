/**
 * Proxy (Next.js 16's renamed Middleware) — optimistic gate for /admin/*.
 *
 * This does an EARLY redirect to /login when the session cookie is missing,
 * expired, or forged, so unauthenticated users never even start loading the
 * logs pages. The authoritative check still lives in app/admin/layout.tsx
 * (per the Next.js guidance that proxy is for optimistic checks, not the
 * sole auth boundary).
 */

import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { ADMIN_COOKIE, verifySession } from "@/lib/adminAuth";

export async function proxy(request: NextRequest) {
  const secret = process.env.ADMIN_SESSION_SECRET;
  const token = request.cookies.get(ADMIN_COOKIE)?.value;

  const ok = secret ? await verifySession(secret, token) : false;
  if (ok) return NextResponse.next();

  const loginUrl = new URL("/login", request.url);
  loginUrl.searchParams.set("from", request.nextUrl.pathname);
  if (!secret || !process.env.ADMIN_LOGS_PASSWORD) {
    loginUrl.searchParams.set("error", "unconfigured");
  }
  return NextResponse.redirect(loginUrl);
}

export const config = {
  // Gate every /admin route. /login and /api/admin/login stay open.
  matcher: "/admin/:path*",
};
