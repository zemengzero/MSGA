import React, { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { Search, X, ArrowUp, ArrowDown } from "lucide-react";
import { findInNoteText } from "./noteFind.js";
import { snapshotPreview, previewRange, mergeFindRanges, scrollToPreviewRange } from "./noteFindDOM.js";

// Mounted only in reading mode and keyed by note ID by the parent.
export default function NoteFindPanel({ previewRef, contentVersion }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [snapshot, setSnapshot] = useState({ text: "", locations: [] });
  const [active, setActive] = useState(0);
  const canHighlight = Boolean(globalThis.Highlight && globalThis.CSS?.highlights);
  const inputRef = useRef(null);
  const triggerRef = useRef(null);
  useEffect(() => {
    // Passive effects run after sibling preview refs are attached.
    // Read what the preview displays, not Markdown, hrefs or HTML attributes.
    setSnapshot(snapshotPreview(previewRef.current));
    setActive(0);
  }, [previewRef, contentVersion]);
  useLayoutEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);
  useLayoutEffect(() => {
    if (open && inputRef.current) {
      inputRef.current.style.height = "auto";
      inputRef.current.style.height = Math.min(inputRef.current.scrollHeight, 90) + "px";
    }
  }, [open, query]);
  const matches = useMemo(() => findInNoteText(snapshot.text, query), [snapshot, query]);
  const current = matches.length ? Math.min(active, matches.length - 1) : 0;
  const allRanges = useMemo(() => mergeFindRanges(matches)
    .map(match => previewRange(snapshot, match)).filter(Boolean), [snapshot, matches]);
  const currentRange = useMemo(() => matches.length
    ? previewRange(snapshot, matches[current]) : null, [snapshot, matches, current]);
  useEffect(() => {
    if (!open || !canHighlight || !allRanges.length) return;
    const all = new Highlight();
    for (const range of allRanges) all.add(range);
    const selected = new Highlight();
    if (currentRange) selected.add(currentRange);
    selected.priority = 1;
    CSS.highlights.set("note-find-all", all);
    CSS.highlights.set("note-find-current", selected);
    return () => {
      if (CSS.highlights.get("note-find-all") === all) CSS.highlights.delete("note-find-all");
      if (CSS.highlights.get("note-find-current") === selected) CSS.highlights.delete("note-find-current");
    };
  }, [open, canHighlight, allRanges, currentRange]);
  useEffect(() => {
    if (open) scrollToPreviewRange(previewRef.current, currentRange);
  }, [open, currentRange, previewRef]);
  function move(delta) {
    if (!matches.length) return;
    const next = (current + delta + matches.length) % matches.length;
    setActive(next);
    if (next === current) scrollToPreviewRange(previewRef.current, currentRange);
  }
  function close() {
    setQuery("");
    setActive(0);
    setOpen(false);
    triggerRef.current?.focus();
  }
  return (
    <div className="note-find-panel" onKeyDown={(event) => {
      if (open && event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        close();
      }
    }}>
      <button type="button" className="note-find-toggle" ref={triggerRef}
        aria-expanded={open} onClick={() => open ? close() : setOpen(true)}>
        <Search size={14} />笔记内查找
      </button>
      {open && <div className="note-find-controls" role="search" aria-label="当前笔记内查找">
        <textarea ref={inputRef} rows={1} aria-label="笔记内查找关键词"
          placeholder="在这篇笔记中查找…" value={query}
          onChange={(event) => { setQuery(event.target.value); setActive(0); }}
          onKeyDown={(event) => {
            if (event.key === "Enter") { event.preventDefault(); move(event.shiftKey ? -1 : 1); }
          }}
          autoComplete="off" spellCheck={false} />
        <output aria-label="笔记内查找结果" aria-live="polite">
          {query.trim() ? `共 ${matches.length} 处` : "请输入关键词"}
        </output>
        <span className="note-find-current" aria-label="当前命中位置" aria-live="polite">
          第 {matches.length ? current + 1 : 0} 处
        </span>
        <button type="button" className="note-find-nav" aria-label="上一处匹配"
          disabled={!matches.length} onClick={() => move(-1)}><ArrowUp size={16} /></button>
        <button type="button" className="note-find-nav" aria-label="下一处匹配"
          disabled={!matches.length} onClick={() => move(1)}><ArrowDown size={16} /></button>
        <button type="button" className="note-find-close" aria-label="关闭笔记内查找"
          onClick={close}><X size={16} /></button>
      </div>}
      {open && matches.length > 0 && (!canHighlight || !currentRange) &&
        <small className="note-find-hint" role="status">当前环境无法显示正文高亮，仍可查看命中数量。</small>}
    </div>
  );
}
