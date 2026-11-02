import React from "react";

export default function HighlightedSnippet({ text = "", ranges = [] }) {
  // Python ranges count Unicode code points, unlike JS UTF-16 string offsets.
  const chars = Array.from(text);
  const parts = [];
  let cursor = 0;
  for (const range of Array.isArray(ranges) ? ranges : []) {
    if (!Array.isArray(range) || range.length !== 2) continue;
    const [start, end] = range;
    if (!Number.isInteger(start) || !Number.isInteger(end) ||
        start < cursor || end <= start || end > chars.length) continue;
    parts.push(chars.slice(cursor, start).join(""));
    parts.push(<mark className="search-hit" key={`${start}-${end}`}>
      {chars.slice(start, end).join("")}
    </mark>);
    cursor = end;
  }
  parts.push(chars.slice(cursor).join(""));
  return <>{parts}</>;
}
