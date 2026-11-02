import { useEffect, useMemo, useState } from "react";
import {
  FileText,
  Plus,
  Orbit,
  LayoutGrid,
  Star,
  Trash2,
  Settings2,
  Database,
  Download,
  Save,
  Hash,
} from "lucide-react";
import { Dialog, DialogContent, DialogTitle } from "./components/ui/dialog";
import {
  Command,
  CommandInput,
  CommandList,
  CommandGroup,
  CommandItem,
} from "./components/ui/command";

const ACTIONS = [
  {
    id: "new",
    label: "新建笔记",
    hint: "N",
    icon: Plus,
    keywords: "xinjian new",
  },
  {
    id: "save",
    label: "保存当前笔记",
    hint: "Ctrl S",
    icon: Save,
    keywords: "baocun save",
  },
  { id: "graph", label: "前往知识星图", icon: Orbit, keywords: "xingtu graph" },
  {
    id: "notes",
    label: "前往全部笔记",
    icon: LayoutGrid,
    keywords: "biji notes",
  },
  {
    id: "favorites",
    label: "前往我的收藏",
    icon: Star,
    keywords: "shoucang favorites",
  },
  {
    id: "trash",
    label: "前往回收站",
    icon: Trash2,
    keywords: "huishouzhan trash",
  },
  {
    id: "settings",
    label: "偏好设置",
    icon: Settings2,
    keywords: "pianhao settings",
  },
  {
    id: "tools",
    label: "数据与备份",
    icon: Database,
    keywords: "beifen backup",
  },
  {
    id: "backup",
    label: "创建完整备份",
    icon: Download,
    keywords: "beifen backup",
  },
];

const lower = (value) => String(value ?? "").toLowerCase();
const includes = (value, needle) => lower(value).includes(lower(needle));

function excerptOf(note) {
  let text = String(note.excerpt || "");
  text = text.replace(/\[\[note:[^\]]+\]\]/g, " ");
  text = text.replace(/!\[[^\]]*\]\([^)]*\)/g, " ");
  text = text.replace(/\[([^\]]*)\]\([^)]*\)/g, "$1");
  text = text.replace(/^[#>\s*\-…·›]+/, "");
  text = text.replace(/#{1,6}\s+/g, "");
  text = text.replace(/[*_`~]{1,3}/g, "");
  text = text.replace(/\s+/g, " ").trim();
  const title = String(note.title || "").trim();
  if (title && text.startsWith(title)) {
    text = text
      .slice(title.length)
      .replace(/^[\s:：,，.。;；·\-]+/, "")
      .trim();
  }
  return text || "空白笔记";
}

export default function CommandPalette({
  open,
  onClose,
  notes,
  loading,
  search,
  onOpenNote,
  onAction,
}) {
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState(null);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    if (open) {
      setQuery("");
      setHits(null);
    }
  }, [open]);

  const trimmed = query.trim();

  useEffect(() => {
    if (!open) return;
    if (!trimmed) {
      setHits(null);
      setSearching(false);
      return;
    }
    let alive = true;
    setSearching(true);
    const timer = setTimeout(() => {
      search(trimmed)
        .then((result) => {
          if (!alive) return;
          setHits(result);
          setSearching(false);
        })
        .catch(() => {
          if (!alive) return;
          setHits([]);
          setSearching(false);
        });
    }, 160);
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, [open, trimmed, search]);

  const noteHits = useMemo(() => {
    if (!trimmed) return notes.slice(0, 5);
    return (hits || []).slice(0, 12);
  }, [notes, hits, trimmed]);

  const actionHits = useMemo(() => {
    if (!trimmed) return ACTIONS;
    return ACTIONS.filter((a) => includes(`${a.label} ${a.keywords}`, trimmed));
  }, [trimmed]);

  return (
    <Dialog open={open} onOpenChange={(value) => !value && onClose()}>
      <DialogContent
        showClose={false}
        className="top-[14%] w-full max-w-[560px] translate-y-0 gap-0 overflow-hidden p-0"
      >
        <DialogTitle className="sr-only">命令面板</DialogTitle>
        <Command shouldFilter={false} loop className="rounded-xl border-0">
          <CommandInput
            autoFocus
            aria-label="命令面板搜索"
            value={query}
            onValueChange={setQuery}
            placeholder="Search notes or run a command…"
          />
          <CommandList>
            {loading && (
              <p className="py-10 text-center text-[14px] text-subtle">
                正在读取本地知识库…
              </p>
            )}

            {!loading && noteHits.length > 0 && (
              <CommandGroup heading={trimmed ? "Matches" : "Recent"}>
                {noteHits.map((note) => (
                  <CommandItem
                    key={note.id}
                    value={`note-${note.id}`}
                    onSelect={() => onOpenNote(note.id)}
                    className="gap-3 py-2.5"
                  >
                    <span
                      className="grid size-7 shrink-0 place-items-center rounded-md border border-border bg-white/[0.03]"
                      style={{ color: note.color || "#a1a1aa" }}
                    >
                      <FileText className="size-3.5" strokeWidth={1.7} />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-[14px] text-foreground">
                        {note.title}
                      </span>
                      <span className="mt-0.5 block truncate text-[14px] text-subtle">
                        {excerptOf(note)}
                      </span>
                    </span>
                  </CommandItem>
                ))}
              </CommandGroup>
            )}

            {!loading && actionHits.length > 0 && (
              <CommandGroup heading="Actions">
                {actionHits.map((action) => {
                  const Icon = action.icon;
                  return (
                    <CommandItem
                      key={action.id}
                      value={`action-${action.id}`}
                      onSelect={() => onAction(action.id)}
                    >
                      <Icon className="size-4 shrink-0" />
                      <span className="flex-1 text-[14px]">{action.label}</span>
                      {action.hint && (
                        <kbd className="rounded border border-border px-1 py-[1px] text-[14px] text-subtle">
                          {action.hint}
                        </kbd>
                      )}
                    </CommandItem>
                  );
                })}
              </CommandGroup>
            )}

            {!loading &&
              !searching &&
              noteHits.length === 0 &&
              actionHits.length === 0 && (
                <p className="py-10 text-center text-[14px] text-subtle">
                  没有找到「{trimmed}」
                </p>
              )}

            {trimmed && searching && noteHits.length === 0 && (
              <p className="py-10 text-center text-[14px] text-subtle">
                搜索中…
              </p>
            )}
          </CommandList>

          <div className="flex items-center gap-4 border-t border-border px-3 py-2 text-[14px] text-subtle">
            <span className="flex items-center gap-1">
              <kbd className="rounded border border-border px-1">↑</kbd>
              <kbd className="rounded border border-border px-1">↓</kbd>
              选择
            </span>
            <span className="flex items-center gap-1">
              <kbd className="rounded border border-border px-1">↵</kbd>
              打开
            </span>
            <span className="flex items-center gap-1">
              <kbd className="rounded border border-border px-1">esc</kbd>
              关闭
            </span>
            <span className="ml-auto tabular-nums">
              {trimmed
                ? searching
                  ? "搜索中…"
                  : (hits || []).length > 12
                    ? `前 12 / 共 ${hits.length} 条`
                    : `${(hits || []).length} 条结果`
                : `${notes.length} 篇`}
            </span>
          </div>
        </Command>
      </DialogContent>
    </Dialog>
  );
}
