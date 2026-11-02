import React, { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { Search, X } from "lucide-react";
import { findInNoteText } from "./noteFind.js";

// Mounted only in reading mode and keyed by note ID by the parent.
export default function NoteFindPanel({ previewRef, contentVersion }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [text, setText] = useState("");
  const inputRef = useRef(null);
  const triggerRef = useRef(null);
  useEffect(() => {
    // Passive effects run after sibling preview refs are attached.
    // Read what the preview displays, not Markdown, hrefs or HTML attributes.
    setText(previewRef.current?.innerText ?? "");
  }, [previewRef, contentVersion]);
  useLayoutEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);
  const matches = useMemo(() => findInNoteText(text, query), [text, query]);
  function close() {
    setQuery("");
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
        <input ref={inputRef} type="search" aria-label="笔记内查找关键词"
          placeholder="在这篇笔记中查找…" value={query}
          onChange={(event) => setQuery(event.target.value)}
          autoComplete="off" spellCheck={false} />
        <output aria-label="笔记内查找结果" aria-live="polite">
          {query.trim() ? `共 ${matches.length} 处` : "请输入关键词"}
        </output>
        <button type="button" className="note-find-close" aria-label="关闭笔记内查找"
          onClick={close}><X size={16} /></button>
      </div>}
    </div>
  );
}
