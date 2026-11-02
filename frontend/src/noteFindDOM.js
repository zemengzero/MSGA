// Map the exact rendered innerText snapshot to original DOM text nodes.
// No wrappers or HTML replacement: Markdown elements and links stay intact.
export function snapshotPreview(root) {
  if (!root) return { text: "", locations: [] };
  const text = root.innerText;
  const chars = Array.from(text);
  const locations = new Array(chars.length).fill(null);
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  let index = 0;
  let node;
  while ((node = walker.nextNode())) {
    const parent = node.parentElement;
    if (!parent || parent.closest("script,style,noscript,[hidden]")) continue;
    const style = getComputedStyle(parent);
    if (style.visibility === "hidden" || style.visibility === "collapse") continue;
    const visible = document.createRange();
    visible.selectNodeContents(node);
    if (!visible.getClientRects().length) continue;
    let offset = 0;
    for (const char of node.data) {
      const end = offset + char.length; // DOM Range offsets use UTF-16.
      if (!/\s/u.test(char)) {
        while (index < chars.length && /\s/u.test(chars[index])) index++;
        if (chars[index] !== char) {
          // Fail closed if future CSS transforms text in an unmappable way.
          return { text, locations: [] };
        }
        locations[index++] = { node, start: offset, end };
      }
      offset = end;
    }
  }
  while (index < chars.length && /\s/u.test(chars[index])) index++;
  return { text, locations: index === chars.length ? locations : [] };
}

export function previewRange(snapshot, [start, end]) {
  let first = start;
  let last = end - 1;
  while (first < end && !snapshot.locations[first]) first++;
  while (last >= first && !snapshot.locations[last]) last--;
  if (first > last) return null;
  const from = snapshot.locations[first];
  const to = snapshot.locations[last];
  const range = document.createRange();
  range.setStart(from.node, from.start);
  range.setEnd(to.node, to.end);
  return range;
}

export function mergeFindRanges(matches) {
  const merged = [];
  for (const [start, end] of matches) {
    if (merged.length && start <= merged.at(-1)[1]) {
      merged.at(-1)[1] = Math.max(merged.at(-1)[1], end);
    } else merged.push([start, end]);
  }
  return merged;
}

export function scrollToPreviewRange(root, range) {
  const container = root?.closest(".drawer-content");
  const rect = range?.getClientRects()[0];
  if (!container || !rect) return;
  const box = container.getBoundingClientRect();
  container.scrollTo({
    top: Math.max(0, container.scrollTop + rect.top - box.top - (box.height - rect.height) / 2),
    behavior: "auto",
  });
}
