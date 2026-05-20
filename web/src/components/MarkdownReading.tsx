import { marked } from "marked";

/**
 * Renders the Gemini-produced markdown reading (six labelled sections).
 * Markdown parsing happens at render time; we don't need a client component
 * because `marked` runs fine on the server.
 */
export function MarkdownReading({
  markdown,
  source,
}: {
  markdown: string;
  source: "gemini" | "template";
}) {
  const html = marked.parse(markdown ?? "", { async: false }) as string;
  const tag = source === "gemini" ? "AI" : "Template";

  return (
    <div className="glass border-l-[3px] border-[var(--accent-purple)] p-5 leading-relaxed text-[var(--text-main)]">
      <div className="mb-2 inline-block text-xs font-semibold uppercase tracking-widest text-[var(--accent-purple)]">
        The Reading
        <span className="ml-2 inline-block rounded-full bg-[rgba(139,92,246,0.15)] px-2 py-[1px] text-[0.65rem] text-[var(--accent-purple)]">
          {tag}
        </span>
      </div>
      <div
        className="markdown-reading"
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </div>
  );
}
