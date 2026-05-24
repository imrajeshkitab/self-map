"use client";

import { useState, useEffect, type Dispatch, type SetStateAction } from "react";

/**
 * Drop-in replacement for `useState` that persists to `sessionStorage`.
 *
 * - SSR-safe: first render always uses `fallback`; the stored value is
 *   restored in a post-mount effect (prevents hydration mismatch).
 * - Returns `[value, setValue, hydrated]`.  `hydrated` flips to `true`
 *   once the sessionStorage read is done — use it to gate effects that
 *   should wait for restored state (e.g. "set default moment only if
 *   nothing was cached").
 * - After hydration, every state change is written back to sessionStorage.
 * - Clears naturally when the browser tab/window closes (sessionStorage
 *   semantics) — so state is preserved across in-app navigations but NOT
 *   across page refreshes that open a new session.
 *
 * NOTE: `sessionStorage` actually *does* survive same-tab refreshes in all
 * modern browsers. If truly "clear on refresh" is desired, call
 * `sessionStorage.clear()` in a beforeunload handler or use a custom key
 * prefix with a per-session nonce.
 */
export function useSessionState<T>(
  key: string,
  fallback: T | (() => T),
): [T, Dispatch<SetStateAction<T>>, boolean] {
  const [value, setValue] = useState<T>(fallback);
  const [hydrated, setHydrated] = useState(false);

  // Phase 1: restore from sessionStorage (runs once after mount)
  useEffect(() => {
    try {
      const raw = sessionStorage.getItem(key);
      if (raw !== null) {
        setValue(JSON.parse(raw));
      }
    } catch {
      /* corrupt data or storage unavailable — use fallback */
    }
    setHydrated(true);
  }, [key]);

  // Phase 2: persist every change (only after hydration, so we never
  // overwrite the stored value with the SSR fallback)
  useEffect(() => {
    if (!hydrated) return;
    try {
      sessionStorage.setItem(key, JSON.stringify(value));
    } catch {
      /* storage full — silently drop */
    }
  }, [key, value, hydrated]);

  return [value, setValue, hydrated];
}
