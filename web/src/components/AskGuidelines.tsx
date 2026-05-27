/**
 * AskGuidelines — a "?" help button that opens an accessible popover with
 * guidance on how to ask a good Prashna question.
 *
 * Click/tap to open (not hover) so it works on touch devices. Closes on
 * outside-click, on Escape, and toggles via the button. The button is a
 * real <button> with aria-expanded / aria-controls for screen readers.
 */

"use client";

import { useEffect, useId, useRef, useState } from "react";

export function AskGuidelines() {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const panelId = useId();

  // Close on outside click + Escape while open.
  useEffect(() => {
    if (!open) return;
    function onPointerDown(e: PointerEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  return (
    <div ref={rootRef} className="relative inline-block align-middle">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-controls={panelId}
        aria-label="How to ask a good question"
        className="inline-flex h-6 w-6 items-center justify-center rounded-full border border-[var(--border-glass)] bg-[rgba(15,17,35,0.7)] text-sm text-[var(--text-muted)] transition hover:border-[rgba(212,175,55,0.5)] hover:text-[var(--accent-gold)] focus:outline-none focus:ring-2 focus:ring-[rgba(139,92,246,0.3)]"
      >
        ?
      </button>

      {open && (
        <div
          id={panelId}
          role="dialog"
          aria-label="How to ask a good question"
          className="absolute left-1/2 top-8 z-50 max-h-[80vh] w-[min(92vw,26rem)] -translate-x-1/2 overflow-y-auto rounded-xl border border-[rgba(212,175,55,0.25)] bg-[#0c0e1c] p-5 text-left text-sm leading-relaxed text-[var(--text-main)] shadow-[0_18px_50px_rgba(0,0,0,0.7)]"
        >
          <h3 className="display mb-2 text-base text-[var(--accent-gold)]">
            How to ask a good question
          </h3>
          <p className="mb-3 text-[var(--text-muted)]">
            Prashna reads the sky at the moment you ask, so a clear, focused
            question gets a clear answer.
          </p>

          <p className="mb-1 font-medium text-[#86efac]">✅ Do</p>
          <ul className="mb-3 list-disc space-y-1 pl-5 text-[var(--text-muted)]">
            <li>
              <span className="text-[var(--text-main)]">Ask about one thing.</span>{" "}
              A single life area per question — career, marriage, money, health,
              a specific decision.
            </li>
            <li>
              <span className="text-[var(--text-main)]">Be specific.</span>{" "}
              &ldquo;Should I accept the offer from this company?&rdquo; beats
              &ldquo;What about work?&rdquo;
            </li>
            <li>
              <span className="text-[var(--text-main)]">
                Make your intent clear.
              </span>{" "}
              Are you trying to achieve something, avoid something, decide
              yes/no, or know when? e.g. &ldquo;Will…&rdquo;, &ldquo;Should
              I…&rdquo;, &ldquo;Is this the right time to…&rdquo;, &ldquo;Should I
              avoid…&rdquo;
            </li>
            <li>
              <span className="text-[var(--text-main)]">
                Ask what&apos;s genuinely on your mind right now.
              </span>{" "}
              Prashna works best for a question you actually care about at this
              moment.
            </li>
          </ul>

          <p className="mb-1 font-medium text-[#f87171]">🚫 Avoid</p>
          <ul className="mb-3 list-disc space-y-1 pl-5 text-[var(--text-muted)]">
            <li>
              <span className="text-[var(--text-main)]">
                Vague or open-ended questions
              </span>{" "}
              — &ldquo;What is my life?&rdquo;, &ldquo;Tell me about
              myself.&rdquo; There&apos;s no house to map them to.
            </li>
            <li>
              <span className="text-[var(--text-main)]">
                Multiple questions at once
              </span>{" "}
              — &ldquo;Will I get the job and should I marry and buy a
              house?&rdquo; Ask them one at a time.
            </li>
            <li>
              <span className="text-[var(--text-main)]">
                Yes/no questions about others&apos; private matters
              </span>{" "}
              or anything you wouldn&apos;t ask sincerely.
            </li>
            <li>
              <span className="text-[var(--text-main)]">
                Re-asking the same question repeatedly
              </span>{" "}
              hoping for a different answer — the moment has already spoken.
            </li>
          </ul>

          <p className="mb-1 font-medium text-[var(--accent-gold)]">
            Good examples
          </p>
          <ul className="list-disc space-y-1 pl-5 text-[var(--text-muted)]">
            <li>&ldquo;Will my career grow this year?&rdquo;</li>
            <li>&ldquo;Is this the right time to marry?&rdquo;</li>
            <li>&ldquo;Should I take this new job?&rdquo;</li>
            <li>&ldquo;Should I avoid this business partnership?&rdquo;</li>
            <li>&ldquo;When will I recover from this illness?&rdquo;</li>
          </ul>
        </div>
      )}
    </div>
  );
}
