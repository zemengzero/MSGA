// Pure matching only: callers supply visible preview text, never HTML markup.
const foldAscii = (text) => text.replace(/[A-Z]/g, (char) => char.toLowerCase());

/**
 * Find every literal query occurrence, including overlaps, in visible text.
 * Return sorted [start, end) Unicode code-point ranges. The query is a single
 * literal phrase, not the global search's whitespace-separated AND expression.
 * Meaningful whitespace and newlines are preserved; blank queries return [].
 * Does not read the DOM, mutate notes, render HTML, or normalize Unicode.
 */
export function findInNoteText(text, query) {
  if (typeof text !== "string" || typeof query !== "string") {
    throw new TypeError("text and query must be strings");
  }
  if (!query.trim() || !text) return [];
  const haystack = Array.from(foldAscii(text));
  const needle = Array.from(foldAscii(query));
  if (needle.length > haystack.length) return [];

  // KMP keeps long notes with repeated prefixes linear rather than quadratic.
  const prefix = new Uint32Array(needle.length);
  for (let i = 1, matched = 0; i < needle.length; i++) {
    while (matched > 0 && needle[i] !== needle[matched]) {
      matched = prefix[matched - 1];
    }
    if (needle[i] === needle[matched]) matched++;
    prefix[i] = matched;
  }

  const ranges = [];
  for (let i = 0, matched = 0; i < haystack.length; i++) {
    while (matched > 0 && haystack[i] !== needle[matched]) {
      matched = prefix[matched - 1];
    }
    if (haystack[i] === needle[matched]) matched++;
    if (matched === needle.length) {
      ranges.push([i + 1 - needle.length, i + 1]);
      matched = prefix[matched - 1]; // Preserve overlapping occurrences.
    }
  }
  return ranges;
}
