/**
 * POST /api/admin/login   — verify the shared password, set the session cookie.
 * DELETE /api/admin/login — log out (clear the cookie).
 *
 * The password and signing secret live only in server env vars; nothing
 * sensitive is ever sent to the client.
 */

import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import {
  ADMIN_COOKIE,
  SESSION_TTL_SECONDS,
  checkPassword,
  signSession,
} from "@/lib/adminAuth";

export async function POST(request: Request) {
  const secret = process.env.ADMIN_SESSION_SECRET;
  if (!secret || !process.env.ADMIN_LOGS_PASSWORD) {
    return NextResponse.json(
      { error: "Admin auth is not configured on the server." },
      { status: 503 },
    );
  }

  let password = "";
  try {
    const body = await request.json();
    password = typeof body?.password === "string" ? body.password : "";
  } catch {
    // fall through — empty password fails below
  }

  if (!checkPassword(password)) {
    return NextResponse.json({ error: "Incorrect password." }, { status: 401 });
  }

  const token = await signSession(secret);
  const jar = await cookies();
  jar.set(ADMIN_COOKIE, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: SESSION_TTL_SECONDS,
  });

  return NextResponse.json({ ok: true });
}

export async function DELETE() {
  const jar = await cookies();
  jar.delete(ADMIN_COOKIE);
  return NextResponse.json({ ok: true });
}
