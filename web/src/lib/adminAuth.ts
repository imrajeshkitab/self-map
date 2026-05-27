/**
 * Admin-logs auth — a tiny stateless session built on a signed cookie.
 *
 * Two server-only secrets (set in .env / Vercel env, NEVER prefixed
 * NEXT_PUBLIC so they don't leak to the browser):
 *   - ADMIN_LOGS_PASSWORD   the shared password a viewer types to get in
 *   - ADMIN_SESSION_SECRET  HMAC key used to sign the session cookie
 *
 * The cookie holds `${expiryEpochSeconds}.${hmac}`. No DB, no server state —
 * verification just re-computes the HMAC. Uses Web Crypto so the same code
 * runs in the Node server runtime AND the proxy (edge) runtime.
 */

export const ADMIN_COOKIE = "kitab_admin_session";
export const SESSION_TTL_SECONDS = 60 * 60 * 12; // 12 hours

const enc = new TextEncoder();

function toHex(buf: ArrayBuffer): string {
  return Array.from(new Uint8Array(buf))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

/** Constant-time string compare (avoids leaking match length via timing). */
function timingSafeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let mismatch = 0;
  for (let i = 0; i < a.length; i++) {
    mismatch |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return mismatch === 0;
}

async function hmacHex(secret: string, message: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const sig = await crypto.subtle.sign("HMAC", key, enc.encode(message));
  return toHex(sig);
}

/** Build a signed session token valid for SESSION_TTL_SECONDS. */
export async function signSession(secret: string): Promise<string> {
  const exp = Math.floor(Date.now() / 1000) + SESSION_TTL_SECONDS;
  const payload = String(exp);
  const sig = await hmacHex(secret, payload);
  return `${payload}.${sig}`;
}

/** True iff the token is well-formed, unexpired, and signed by `secret`. */
export async function verifySession(
  secret: string,
  token: string | undefined | null,
): Promise<boolean> {
  if (!token) return false;
  const dot = token.indexOf(".");
  if (dot <= 0) return false;
  const payload = token.slice(0, dot);
  const sig = token.slice(dot + 1);

  const exp = Number(payload);
  if (!Number.isFinite(exp) || exp * 1000 < Date.now()) return false;

  const expected = await hmacHex(secret, payload);
  return timingSafeEqual(sig, expected);
}

/** Validate a typed password against ADMIN_LOGS_PASSWORD (constant-time). */
export function checkPassword(input: string): boolean {
  const expected = process.env.ADMIN_LOGS_PASSWORD ?? "";
  if (!expected) return false; // misconfigured → deny everyone
  return timingSafeEqual(input, expected);
}
