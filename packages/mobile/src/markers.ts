/** Coworker replies embed tool chips and cards as `:::cw {json}` lines (same format as the web app). */
export type Segment =
  | { kind: "text"; text: string }
  | { kind: "tool"; summary: string }
  | { kind: "action"; id: number }
  | { kind: "meeting"; id: number };

export function marker(data: Record<string, unknown>): string {
  return `\n:::cw ${JSON.stringify(data)}\n`;
}

export function parseSegments(content: string): Segment[] {
  const out: Segment[] = [];
  let text: string[] = [];
  const flush = () => {
    const joined = text.join("\n").replace(/\*\*/g, "").trim();
    if (joined) out.push({ kind: "text", text: joined });
    text = [];
  };
  for (const line of content.split("\n")) {
    if (line.startsWith(":::cw ")) {
      try {
        const d = JSON.parse(line.slice(6));
        flush();
        if (d.t === "tool") out.push({ kind: "tool", summary: d.summary || "" });
        else if (d.t === "action") out.push({ kind: "action", id: Number(d.id) });
        else if (d.t === "meeting") out.push({ kind: "meeting", id: Number(d.id) });
        continue;
      } catch {}
    }
    text.push(line);
  }
  flush();
  return out;
}
