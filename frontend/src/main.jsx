import React, {
  useState,
  useEffect,
  useRef,
  useCallback,
  useMemo,
} from "react";
import { createRoot } from "react-dom/client";
import ForceGraph3D from "react-force-graph-3d";
import * as THREE from "three";
import { toast } from "sonner";
import {
  Orbit,
  Search,
  Plus,
  LayoutGrid,
  Star,
  Trash2,
  Settings2,
  Database,
  Download,
  Upload,
  RotateCcw,
  FileText,
  ChevronRight,
  MoreHorizontal,
  FolderOpen,
  ShieldCheck,
  Save,
  Pencil,
  Eye,
  Link2,
  History,
  X,
  Loader2,
  Hash,
  BookOpen,
  Check,
  AlertCircle,
  Circle,
  Maximize2,
  ArrowUpRight,
} from "lucide-react";
import "./app.css";
import { cn } from "./lib/utils";
import { Button } from "./components/ui/button";
import { Input } from "./components/ui/input";
import { Textarea } from "./components/ui/textarea";
import { Badge } from "./components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogDescription,
} from "./components/ui/dialog";
import { Toaster } from "./components/ui/sonner";
import CommandPalette from "./CommandPalette";
import NoteFindPanel from "./NoteFindPanel.jsx";
import HighlightedSnippet from "./HighlightedSnippet.jsx";

export async function api(action, payload = {}) {
  const response = await fetch("/api/" + action, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Zhiye-Token": window.ZHIYE_TOKEN,
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error("本地连接中断，请保留当前编辑内容并重试");
  const result = await response.json();
  if (!result.ok) {
    const error = new Error(result.error || "操作未完成");
    error.kind = result.type;
    throw error;
  }
  return result.data;
}

const escapeHtml = (s) =>
  String(s).replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );

const dateLabel = (s) =>
  new Date(s).toLocaleDateString("zh-CN", { month: "2-digit", day: "2-digit" });

const uidEqual = (a, b) =>
  a.title === b.title && a.body === b.body && a.tagText === b.tagText;

const cleanExcerpt = (text = "", title = "") => {
  // The server snippet is whitespace-collapsed, so the leading "# title" and
  // any later "## heading" have to be removed by marker + known title.
  let raw = String(text)
    .replace(/\[\[note:[^\]]+\]\]/g, "")
    .replace(/!\[[^\]]*\]\([^)]*\)/g, "")
    .replace(/\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/^\s*#{1,6}\s*/, "");
  const head = String(title || "").trim();
  if (head && raw.startsWith(head)) raw = raw.slice(head.length);
  const prose = raw.split(/#{1,6}\s/)[0];
  return prose
    .replace(/[*_`~]{2,}/g, "")
    .replace(/^[#>\s·›]+/, "")
    .replace(/\s+/g, " ")
    .trim();
};

function IconButton({ icon: Icon, label, className, ...props }) {
  return (
    <Button
      variant="ghost"
      size="icon"
      aria-label={label}
      title={label}
      className={className}
      {...props}
    >
      <Icon />
    </Button>
  );
}

/* ------------------------------------------------------------------ galaxy */

function Galaxy({ graph, matched, query, onOpen, paused }) {
  const ref = useRef();
  const host = useRef();
  const [size, setSize] = useState({ width: 700, height: 470 });
  const [hover, setHover] = useState(null);
  const [failed, setFailed] = useState(false);
  const data = useMemo(
    () => ({
      nodes: graph.nodes.map((n, i) => ({ ...n, featured: i % 5 === 0 })),
      links: graph.links.map((l) => ({ ...l })),
    }),
    [graph],
  );
  const hits = useMemo(() => new Set(matched), [matched]);

  useEffect(() => {
    if (!ref.current) return;
    if (paused) ref.current.pauseAnimation();
    else ref.current.resumeAnimation();
  }, [paused, data]);

  const neighbours = useMemo(() => {
    const s = new Set(hover ? [hover] : []);
    if (hover)
      for (const l of data.links) {
        const a = l.source.id || l.source,
          b = l.target.id || l.target;
        if (a === hover) s.add(b);
        if (b === hover) s.add(a);
      }
    return s;
  }, [hover, data]);

  useEffect(() => {
    const observer = new ResizeObserver(([e]) =>
      setSize({
        width: Math.floor(e.contentRect.width),
        height: Math.floor(e.contentRect.height),
      }),
    );
    observer.observe(host.current);
    return () => observer.disconnect();
  }, []);

  // Fit then push the camera closer: a 3D force graph has depth, so a plain
  // zoomToFit leaves the cloud floating in a lot of empty canvas.
  const fitGraph = useCallback(() => {
    const graph = ref.current;
    if (!graph) return;
    graph.zoomToFit(0, 48);
    const camera = graph.camera();
    const controls = graph.controls?.();
    const target = controls?.target?.clone?.() ?? new THREE.Vector3();
    camera.position.sub(target).multiplyScalar(0.72).add(target);
    camera.updateProjectionMatrix();
    controls?.update?.();
  }, []);

  useEffect(() => {
    const t = setTimeout(fitGraph, 1600);
    return () => clearTimeout(t);
  }, [data, fitGraph]);

  // keep the graph fitted when the plate resizes (layout changes)
  useEffect(() => {
    if (!size.width) return;
    const t = setTimeout(fitGraph, 160);
    return () => clearTimeout(t);
  }, [size.width, size.height, fitGraph]);

  const sphere = useCallback(
    (n) => {
      const group = new THREE.Group();
      const lit =
        (!query || hits.has(n.id)) && (!hover || neighbours.has(n.id));
      const r = 2.6 + Math.min(n.degree, 8) * 0.34;
      const orb = new THREE.Mesh(
        new THREE.SphereGeometry(r, 18, 14),
        new THREE.MeshBasicMaterial({
          color: lit ? n.color : "#d8cfb8",
          transparent: true,
          opacity: lit ? 0.92 : 0.3,
        }),
      );
      group.add(orb);
      if (n.featured || n.id === hover) {
        const canvas = document.createElement("canvas");
        canvas.width = 640;
        canvas.height = 100;
        const ctx = canvas.getContext("2d");
        ctx.font = '44px "Geist Variable", "Microsoft YaHei UI", sans-serif';
        ctx.textAlign = "center";
        ctx.fillStyle = lit ? "#15140f" : "#8b8676";
        ctx.fillText(n.title.slice(0, 16), 320, 55);
        const texture = new THREE.CanvasTexture(canvas);
        const sprite = new THREE.Sprite(
          new THREE.SpriteMaterial({
            map: texture,
            transparent: true,
            depthWrite: false,
          }),
        );
        sprite.scale.set(96, 16, 1);
        sprite.position.y = -r - 7;
        group.add(sprite);
      }
      return group;
    },
    [hover, neighbours, hits, query],
  );

  return (
    <div
      className="relative h-full w-full overflow-hidden bg-[#efe7d2]"
      ref={host}
      data-testid="graph-stage"
    >
      {!failed && data.nodes.length > 0 ? (
        <ForceGraph3D
          ref={ref}
          graphData={data}
          width={size.width}
          height={size.height}
          backgroundColor="#efe7d2"
          showNavInfo={false}
          nodeThreeObject={sphere}
          nodeLabel={(n) => escapeHtml(n.title)}
          nodeRelSize={5}
          linkColor={(l) =>
            hover &&
            neighbours.has(l.source.id || l.source) &&
            neighbours.has(l.target.id || l.target)
              ? "rgba(21,20,15,0.5)"
              : "rgba(21,20,15,0.13)"
          }
          linkWidth={(l) =>
            hover && (l.source.id === hover || l.target.id === hover) ? 1 : 0.3
          }
          linkOpacity={0.7}
          linkDirectionalParticles={(l) =>
            hover && (l.source.id === hover || l.target.id === hover) ? 2 : 0
          }
          linkDirectionalParticleWidth={1}
          onNodeHover={(n) => setHover(n?.id || null)}
          onNodeClick={(n) => onOpen(n.id)}
          enableNodeDrag={true}
          cooldownTicks={120}
          warmupTicks={60}
          onEngineStop={() => {
            window.__graphRendered = true;
          }}
          rendererConfig={{ antialias: true, alpha: true }}
        />
      ) : (
        <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
          <Orbit className="size-8 text-subtle" strokeWidth={1.4} />
          <p className="text-[14px] font-medium">
            {failed ? "当前设备未能加载 3D 图谱" : "让第一条灵感，成为起点"}
          </p>
          <p className="text-[14px] text-subtle">
            {failed
              ? "笔记仍可在「全部笔记」中正常使用"
              : "新建笔记，再用关联把想法连接起来"}
          </p>
        </div>
      )}

      <div className="pointer-events-none absolute inset-x-0 bottom-0 flex items-center justify-between border-t border-[#15140f1f] bg-[#efe7d2]/92 px-3.5 py-2 text-[14px] font-semibold uppercase tracking-[0.16em] text-[#8b8676]">
        <span>拖动旋转 · 滚轮缩放 · 点击阅读</span>
        <span className="tabular-nums">
          {data.nodes.length} 节点 · {data.links.length} 关联
        </span>
      </div>

      <div className="absolute right-3 top-3">
        <Button
          variant="secondary"
          size="icon-sm"
          aria-label="图谱居中"
          title="图谱居中"
          onClick={fitGraph}
        >
          <Maximize2 />
        </Button>
      </div>
    </div>
  );
}

class GraphBoundary extends React.Component {
  constructor(p) {
    super(p);
    this.state = { failed: false };
  }
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? (
      <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
        <Orbit className="size-8 text-subtle" strokeWidth={1.4} />
        <p className="text-[14px] font-medium">3D 视图暂不可用</p>
        <p className="text-[14px] text-subtle">
          当前图形环境不支持，请从右侧列表或「全部笔记」打开内容。
        </p>
      </div>
    ) : (
      this.props.children
    );
  }
}

/* --------------------------------------------------------------------- app */

function App() {
  const [snapshot, setSnapshot] = useState(null);
  const [route, setRoute] = useState("graph");
  const [query, setQuery] = useState("");
  const [tag, setTag] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [selected, setSelected] = useState(null);
  const [draft, setDraft] = useState(null);
  const draftRef = useRef(null);
  const previewRef = useRef(null);
  const selectedRef = useRef(null);
  const [dirty, setDirty] = useState(false);
  const dirtyRef = useRef(false);
  const [saving, setSaving] = useState(false);
  const saveTask = useRef(null);
  const [saveError, setSaveError] = useState("");
  const [edit, setEdit] = useState(false);
  const [modal, setModal] = useState(null);
  const [confirm, setConfirm] = useState(null);
  const [fontSize, setFontSize] = useState(14);
  const [versions, setVersions] = useState([]);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [paletteNotes, setPaletteNotes] = useState([]);
  const [paletteLoading, setPaletteLoading] = useState(false);
  const queryRef = useRef();
  const request = useRef(0);
  const openRequest = useRef(0);
  const initialised = useRef(false);

  const notify = useCallback((message, bad = false) => {
    if (bad) toast.error(message);
    else toast.success(message);
  }, []);

  useEffect(() => {
    if (!paletteOpen) return;
    let alive = true;
    setPaletteLoading(true);
    api("snapshot", {})
      .then((data) => {
        if (!alive) return;
        setPaletteNotes(data.notes || []);
        setPaletteLoading(false);
      })
      .catch((e) => {
        if (!alive) return;
        setPaletteLoading(false);
        notify(e.message, true);
      });
    return () => {
      alive = false;
    };
  }, [paletteOpen, notify]);

  const refresh = useCallback(async () => {
    const sequence = ++request.current;
    const data = await api("snapshot", {
      query,
      tags: tag ? [tag] : [],
      deleted: route === "trash",
      date_from: dateFrom,
      date_to: dateTo,
    });
    if (sequence === request.current) {
      setSnapshot(data);
      if (!initialised.current) {
        setFontSize(data.font_size);
        initialised.current = true;
      }
      window.__appReady = true;
    }
    return data;
  }, [query, tag, route, dateFrom, dateTo]);

  useEffect(() => {
    const t = setTimeout(
      () => refresh().catch((e) => notify(e.message, true)),
      query ? 220 : 0,
    );
    return () => clearTimeout(t);
  }, [refresh, notify]);

  function assignDraft(value) {
    draftRef.current = value;
    setDraft(value);
  }
  function markDirty(value) {
    dirtyRef.current = value;
    setDirty(value);
    window.__hasUnsavedChanges = value || Boolean(saveTask.current);
  }
  function changeDraft(field, value) {
    assignDraft({ ...draftRef.current, [field]: value });
    markDirty(true);
    setSaveError("");
  }
  async function saveDraft() {
    if (saveTask.current) return saveTask.current;
    if (!dirtyRef.current || !draftRef.current) return true;
    const submitted = { ...draftRef.current };
    setSaving(true);
    window.__hasUnsavedChanges = true;
    const task = (async () => {
      try {
        const saved = await api("save", {
          id: submitted.id,
          title: submitted.title,
          body: submitted.body,
          tags: submitted.tagText,
          revision: submitted.revision,
        });
        if (draftRef.current?.id === saved.id) {
          const same = uidEqual(draftRef.current, submitted);
          assignDraft({ ...draftRef.current, revision: saved.revision });
          selectedRef.current = { ...selectedRef.current, ...saved };
          setSelected(selectedRef.current);
          markDirty(!same);
          setSaveError("");
        }
        await refresh();
        return true;
      } catch (e) {
        setSaveError(e.message);
        return false;
      } finally {
        setSaving(false);
        saveTask.current = null;
        window.__hasUnsavedChanges = dirtyRef.current;
      }
    })();
    saveTask.current = task;
    return task;
  }

  useEffect(() => {
    if (!dirty || saveError || saving) return;
    const timer = setTimeout(() => {
      if (!modal && !confirm) saveDraft();
    }, 1400);
    return () => clearTimeout(timer);
  }, [draft, dirty, saveError, modal, confirm, saving]);

  function ask(text, mode = "normal") {
    return new Promise((resolve) => setConfirm({ text, mode, resolve }));
  }
  function answer(value) {
    const c = confirm;
    setConfirm(null);
    c?.resolve(value);
  }
  async function allowLeave() {
    if (saveTask.current) await saveTask.current;
    if (!dirtyRef.current) return true;
    const choice = await ask(
      "这篇笔记还有未保存的修改。你想如何继续？",
      "unsaved",
    );
    if (choice === "save") {
      const ok = await saveDraft();
      return ok && !dirtyRef.current;
    }
    if (choice === "discard") {
      markDirty(false);
      setSaveError("");
      return true;
    }
    return false;
  }
  async function openNote(id) {
    if (id === selectedRef.current?.id) return;
    if (!(await allowLeave())) return;
    const seq = ++openRequest.current;
    try {
      const n = await api("note", { id });
      if (seq !== openRequest.current) return;
      selectedRef.current = n;
      setSelected(n);
      assignDraft({ ...n, tagText: n.tags.join("，") });
      markDirty(false);
      setSaveError("");
      setEdit(false);
    } catch (e) {
      notify(e.message, true);
    }
  }
  async function closeDrawer() {
    if (!(await allowLeave())) return;
    openRequest.current++;
    selectedRef.current = null;
    setSelected(null);
    assignDraft(null);
    markDirty(false);
  }
  async function newNote() {
    if (!(await allowLeave())) return;
    try {
      const n = await api("create", {
        title: "未命名的灵感",
        body: "# 新的想法\n\n从这里开始记录……",
        tags: tag ? [tag] : [],
      });
      await refresh();
      selectedRef.current = null;
      await openNote(n.id);
      setEdit(true);
    } catch (e) {
      notify(e.message, true);
    }
  }
  async function navigate(next) {
    if (!(await allowLeave())) return;
    selectedRef.current = null;
    setSelected(null);
    assignDraft(null);
    markDirty(false);
    setRoute(next);
    setQuery("");
    setTag("");
  }
  async function togglePin(note) {
    try {
      await api("pin", { id: note.id });
      await refresh();
      notify(note.pinned ? "已取消收藏" : "已加入收藏");
    } catch (e) {
      notify(e.message, true);
    }
  }
  async function deleteOrRestore() {
    if (!selected) return;
    if (!(await allowLeave())) return;
    if (
      !(await ask(
        selected.deleted
          ? "将这篇笔记恢复到知识库？"
          : "移入回收站后可以恢复，是否继续？",
      ))
    )
      return;
    try {
      await api("trash", { id: selected.id, deleted: !selected.deleted });
      selectedRef.current = null;
      setSelected(null);
      assignDraft(null);
      markDirty(false);
      await refresh();
      notify(selected.deleted ? "笔记已恢复" : "已移入回收站");
    } catch (e) {
      notify(e.message, true);
    }
  }
  async function history() {
    if (!selected || !(await allowLeave())) return;
    try {
      setVersions(await api("history", { id: selected.id }));
      setModal("history");
    } catch (e) {
      notify(e.message, true);
    }
  }
  async function restoreVersion(v) {
    if (
      !(await ask(
        `将当前内容恢复到 v${v.revision}？这会生成一个新版本，现有历史仍保留。`,
      ))
    )
      return;
    try {
      const n = await api("restore_version", {
        id: selected.id,
        history_id: v.id,
        revision: draftRef.current.revision,
      });
      setModal(null);
      selectedRef.current = null;
      await openNote(n.id);
      await refresh();
      notify("已恢复内容，并保留为新版本");
    } catch (e) {
      notify(e.message, true);
    }
  }
  async function fileAction(action, payload = {}) {
    if (!(await allowLeave())) return;
    try {
      let result;
      if (action === "pick_restore") {
        const choice = await api(action);
        if (choice.cancelled) return;
        if (
          !(await ask(
            `备份“${choice.name}”含 ${choice.notes} 篇笔记。将完整替换当前库，并先保留保护副本。确定恢复？`,
          ))
        )
          return;
        result = await api("restore", { token: choice.token });
        selectedRef.current = null;
        setSelected(null);
        assignDraft(null);
        markDirty(false);
        notify(
          "恢复完成；原库保护副本：" +
            result.protection_path +
            (result.audit_warning ? "；" + result.audit_warning : ""),
          Boolean(result.audit_warning),
        );
      } else {
        result = await api(action, payload);
        if (result.cancelled) return;
        if (action === "import") {
          const ok = result.items.filter((i) => i.ok).length;
          const failed = result.items.filter((i) => !i.ok);
          notify(
            `成功导入 ${ok} 篇` +
              (failed.length
                ? `，${failed.length} 篇失败：${failed[0].error}`
                : ""),
            failed.length > 0,
          );
        } else if (action === "export") {
          notify(`已导出 ${result.count} 篇到 ${result.path}`);
        } else {
          notify("备份已创建：" + result.path);
        }
        await refresh();
      }
    } catch (e) {
      notify(e.message, true);
    }
  }
  async function insertLink(target) {
    if (!draftRef.current) return;
    changeDraft("body", draftRef.current.body + `\n\n[[note:${target.id}]]`);
    setEdit(true);
    setModal(null);
  }

  useEffect(() => {
    const key = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
        e.preventDefault();
        saveDraft();
      }
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((value) => !value);
      }
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "n") {
        e.preventDefault();
        newNote();
      }
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  });

  useEffect(() => {
    window.__desktopSmoke = async () => {
      try {
        const n = await api("create", {
          title: "星图实体检查",
          body: "# 实体窗口验证\n\n本内容由自动检查生成。",
          tags: ["界面验证"],
        });
        const saved = await api("save", {
          ...n,
          title: "星图实体检查已保存",
          body: n.body + "\n\n保存成功。",
          revision: n.revision,
        });
        const back = await api("note", { id: n.id });
        const state = await refresh();
        const day = new Date(new Date(saved.updated_at).getTime() + 8 * 3600000)
          .toISOString()
          .slice(0, 10);
        const matching = await api("snapshot", {
          query: "保存成功",
          date_from: day,
          date_to: day,
        });
        const excluded = await api("snapshot", {
          query: "保存成功",
          date_from: "2000-01-01",
          date_to: "2000-01-01",
        });
        const hit = matching.notes.find((item) => item.id === n.id);
        const cSearchReady = Boolean(
          state.capabilities.date_filters &&
          state.capabilities.hit_snippets &&
          hit?.excerpt.includes("保存成功") &&
          hit?.matched_fields.includes("body") &&
          !excluded.notes.some((item) => item.id === n.id),
        );
        window.__desktopSmokeResult = {
          passed:
            back.title === saved.title &&
            back.body.includes("保存成功") &&
            Boolean(document.querySelector("canvas")) &&
            cSearchReady,
          note_id: n.id,
          graph_nodes: state.graph.nodes.length,
          graph_links: state.graph.links.length,
          canvas_present: Boolean(document.querySelector("canvas")),
          frontend_loaded: true,
          c_search_ready: cSearchReady,
          capabilities: state.capabilities,
        };
      } catch (e) {
        window.__desktopSmokeResult = { passed: false, error: e.message };
      }
    };
  }, [refresh]);

  const displayed =
    snapshot?.notes.filter(
      (n) => route !== "favorites" || snapshot.pinned_ids.includes(n.id),
    ) || [];
  const filtered = Boolean(query || tag || dateFrom || dateTo);
  const pageTitle = {
    graph: "Galaxy",
    notes: "Notes",
    favorites: "Favourites",
    trash: "Trash",
  }[route];
  const pageHint = {
    graph: "每条线都是正文里真实保存的关联。",
    notes: "所有笔记按最近修改排序。",
    favorites: "你标记过的想法。",
    trash: "移除的笔记仍可恢复。",
  }[route];
  const pageMeta = {
    graph: { en: "Galaxy", label: "YOUR KNOWLEDGE UNIVERSE", no: "Nº 01" },
    notes: { en: "Library", label: "ALL ENTRIES", no: "Nº 02" },
    favorites: { en: "Favourites", label: "SELECTED ENTRIES", no: "Nº 03" },
    trash: { en: "Archive", label: "REMOVED ENTRIES", no: "Nº 04" },
  }[route];

  const readerHtml = useMemo(() => {
    const html = selected?.html || "";
    const match = html.match(/^\s*<h1[^>]*>([\s\S]*?)<\/h1>/);
    if (!match) return html;
    const text = match[1].replace(/<[^>]+>/g, "").trim();
    if (text && text === String(selected.title || "").trim()) {
      return html.slice(match[0].length);
    }
    return html;
  }, [selected]);

  const navItems = [
    ["graph", Orbit, "知识星图"],
    ["notes", LayoutGrid, "全部笔记"],
    ["favorites", Star, "我的收藏"],
    ["trash", Trash2, "回收站"],
  ];

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* ---------------------------------------------------------- sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 flex w-[236px] flex-col border-r border-[#15140f1f] bg-[#ece4cf]">
        <div className="flex h-[52px] shrink-0 items-center gap-2 px-4">
          <span className="grid size-[22px] place-items-center rounded-[5px] bg-primary text-[14px] font-semibold text-primary-foreground">
            知
          </span>
          <span className="text-[17px] font-bold tracking-[-0.025em]">
            知页
          </span>
        </div>

        <div className="px-2">
          <button
            onClick={() => setModal("tools")}
            className="flex w-full items-center gap-2.5 rounded-md px-2 py-1.5 text-left transition-colors hover:bg-accent"
          >
            <span className="grid size-5 shrink-0 place-items-center rounded-[4px] border border-border bg-black/[0.05] text-[14px] text-muted-foreground">
              知
            </span>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-[14px] leading-4">
                {snapshot?.demo ? "演示空间" : "我的知识库"}
              </span>
              <span className="block truncate text-[14px] leading-4 text-subtle">
                {snapshot?.demo
                  ? "独立数据 · 可随时重置"
                  : "本地存储 · 不会上传"}
              </span>
            </span>
            <ChevronRight className="size-3.5 shrink-0 text-subtle" />
          </button>
        </div>

        <nav className="mt-5 px-2">
          <div className="space-y-px">
            {navItems.map(([key, Icon, label]) => (
              <button
                key={key}
                onClick={() => navigate(key)}
                className={cn(
                  "flex h-9 w-full items-center gap-2.5 rounded-full px-3 text-[14px] transition-colors",
                  route === key
                    ? "bg-[#ed6f5c] text-white shadow-[0_12px_22px_-16px_rgba(237,111,92,0.9)]"
                    : "text-[#5a5448] hover:bg-[#15140f0a] hover:text-[#15140f]",
                )}
              >
                <Icon className="size-[15px] shrink-0" strokeWidth={1.7} />
                <span className="flex-1 text-left">{label}</span>
                {key === "notes" && (
                  <span className="font-mono text-[14px] tabular-nums text-[#5a5448]">
                    {snapshot?.stats.active || 0}
                  </span>
                )}
              </button>
            ))}
          </div>
        </nav>

        <div className="flex-1" />

        <div className="shrink-0 border-t border-border p-2">
          <button
            onClick={() => setModal("tools")}
            className="flex w-full items-center gap-2.5 rounded-md px-2 py-1.5 text-left transition-colors hover:bg-accent"
          >
            <Database className="size-[15px] shrink-0 text-subtle" />
            <span className="min-w-0 flex-1">
              <span className="block truncate text-[14px] leading-4">
                本地知识库
              </span>
              <span className="flex items-center gap-1.5 text-[14px] leading-4 text-subtle">
                <i className="size-1 rounded-full bg-emerald-500" />
                数据只在你的电脑
              </span>
            </span>
            <MoreHorizontal className="size-3.5 shrink-0 text-subtle" />
          </button>
        </div>
      </aside>

      {/* ------------------------------------------------------------- main */}
      <div className="ml-[236px] flex h-screen flex-col overflow-hidden">
        <header className="sticky top-0 z-20 flex h-[52px] shrink-0 items-center gap-4 border-b border-[#15140f1f] bg-[#efe7d2] px-7">
          <div className="flex items-center gap-2 text-[14px] font-semibold uppercase tracking-[0.16em] text-[#8b8676]">
            <span>Workspace</span>
            <span className="text-[#8b8676]">/</span>
            <span className="text-[#15140f]">{pageTitle}</span>
          </div>

          <div className="ml-auto flex items-center gap-2">
            <div className="flex h-8 w-[272px] items-center gap-2 rounded-md border border-border bg-black/[0.025] px-2.5 transition-colors focus-within:border-[#15140f]">
              <Search className="size-3.5 shrink-0 text-subtle" />
              <input
                ref={queryRef}
                aria-label="搜索笔记"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="搜索笔记…"
                className="h-full min-w-0 flex-1 bg-transparent text-[14px] outline-none placeholder:text-subtle"
              />
              <kbd className="rounded border border-border px-1 py-[1px] text-[14px] text-subtle">
                Ctrl K
              </kbd>
            </div>
            <span className="hidden items-center gap-1.5 text-[14px] text-subtle xl:flex">
              <i className="size-1 rounded-full bg-emerald-500" />
              本地运行
            </span>
            <IconButton
              icon={Settings2}
              label="偏好设置"
              onClick={() => setModal("settings")}
            />
            <span className="grid size-6 place-items-center rounded-full border border-border bg-black/[0.05] text-[14px] text-muted-foreground">
              Z
            </span>
          </div>
        </header>

        <main className="flex min-h-0 flex-1 flex-col px-14 pt-11">
          <div className="flex items-start justify-between gap-12">
            <div className="min-w-0">
              <h1 className="mt-5 font-serif text-[104px] font-normal italic leading-[0.9] tracking-[-0.03em]">
                {pageTitle}
              </h1>

            </div>

            <div className="flex shrink-0 items-center gap-3 pt-3">
              {snapshot?.capabilities?.date_filters && (
                <div className="flex h-9 items-center gap-2 rounded-full border border-[#15140f1f] px-3.5 text-[14px] text-[#5a5448]">
                  <span className="shrink-0">更新于</span>
                  <input
                    type="date"
                    aria-label="开始日期"
                    value={dateFrom}
                    onChange={(e) => setDateFrom(e.target.value)}
                    className="h-6 w-[104px] bg-transparent text-[14px] text-[#5a5448] outline-none [color-scheme:light]"
                  />
                  <span className="shrink-0">–</span>
                  <input
                    type="date"
                    aria-label="结束日期"
                    value={dateTo}
                    onChange={(e) => setDateTo(e.target.value)}
                    className="h-6 w-[104px] bg-transparent text-[14px] text-[#5a5448] outline-none [color-scheme:light]"
                  />
                  {(dateFrom || dateTo) && (
                    <button
                      onClick={() => {
                        setDateFrom("");
                        setDateTo("");
                      }}
                      aria-label="清除日期筛选"
                      className="rounded-full p-1 text-[#8b8676] transition-colors hover:bg-[#15140f0a] hover:text-[#ed6f5c]"
                    >
                      <X className="size-3" />
                    </button>
                  )}
                </div>
              )}
              <Button onClick={newNote} className="h-10 gap-2 px-5 text-[14px]">
                <Plus />
                新建笔记
                <kbd className="ml-0.5 rounded-full border border-white/30 px-1.5 text-[14px] text-white/75">
                  N
                </kbd>
              </Button>
            </div>
          </div>

          {route === "graph" ? (
          <div className="mt-10 grid min-h-0 flex-1 grid-cols-[minmax(0,1.62fr)_258px] gap-12 pb-6">
              <section className="flex min-h-0 flex-col">

                <div className="min-h-0 flex-1 border-y border-[#15140f26]">
                  {snapshot ? (
                    <GraphBoundary>
                      <Galaxy
                        graph={snapshot.graph}
                        paused={Boolean(selected)}
                        matched={snapshot.matched_ids}
                        query={filtered}
                        onOpen={openNote}
                      />
                    </GraphBoundary>
                  ) : (
                    <div className="flex h-full items-center justify-center gap-2 text-[14px] text-[#8b8676]">
                      <Loader2 className="size-3.5 animate-spin" />
                      正在连接本地知识库…
                    </div>
                  )}
                </div>
              </section>

              <aside className="flex min-h-0 flex-col overflow-y-auto pr-1">
                <div className="flex items-baseline justify-between border-b border-[#15140f26] pb-3">
                  <span className="text-[18px] font-normal tracking-[-0.01em]">
                    {filtered ? "搜索结果" : "最近更新"}
                  </span>
                  <button
                    onClick={() => navigate("notes")}
                    className="text-[14px] uppercase tracking-[0.16em] text-[#8b8676] transition-colors hover:text-[#ed6f5c]"
                  >
                    全部
                  </button>
                </div>

                {displayed.slice(0, 5).map((n, index) => (
                  <button
                    key={n.id}
                    onClick={() => openNote(n.id)}
                    className="recent-item flex w-full gap-3 border-b border-[#15140f14] py-4 text-left transition-colors hover:bg-[#f7f1de66]"
                  >
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-[16px] font-normal leading-6">
                        {n.title}
                      </span>
                      <p
                        className={
                          filtered
                            ? "mt-1 line-clamp-2 text-[14px] leading-5 text-[#5a5448]"
                            : "sr-only"
                        }
                      >
                        <HighlightedSnippet
                          text={n.excerpt}
                          ranges={n.snippet_highlights}
                        />
                      </p>
                      <span className="mt-1.5 block text-[14px] uppercase tracking-[0.14em] text-[#8b8676]">
                        {dateLabel(n.updated_at)}
                      </span>
                    </span>
                  </button>
                ))}

                {!displayed.length && (
                  <p className="py-6 text-[14px] text-[#8b8676]">
                    没有符合条件的笔记
                  </p>
                )}
              </aside>
            </div>
          ) : (
            <section className="mt-10 min-h-0 flex-1 overflow-y-auto pb-4">

              {displayed.map((n, index) => (
                <article
                  key={n.id}
                  className="note-card group grid cursor-pointer grid-cols-[minmax(0,1fr)_auto] items-baseline gap-6 border-b border-[#15140f14] py-5 transition-colors hover:bg-[#f7f1de4d]"
                  onClick={() => openNote(n.id)}
                  tabIndex={0}
                  onKeyDown={(e) => e.key === "Enter" && openNote(n.id)}
                >
                  <div className="min-w-0">
                    <h3 className="text-[19px] font-normal leading-[1.35] tracking-[-0.01em]">
                      {n.title}
                    </h3>
                    <p
                      className={
                        filtered
                          ? "mt-1.5 line-clamp-2 max-w-[72ch] text-[14px] leading-5 text-[#5a5448]"
                          : "sr-only"
                      }
                    >
                      <HighlightedSnippet
                        text={n.excerpt}
                        ranges={n.snippet_highlights}
                      />
                    </p>
                  </div>

                  <div className="flex items-center gap-5">
                    <span className="text-[14px] uppercase tracking-[0.14em] text-[#8b8676]">
                      {dateLabel(n.updated_at)}
                    </span>
                    <span className="text-[14px] uppercase tracking-[0.14em] text-[#8b8676]">
                      v{n.revision}
                    </span>
                    <button
                      aria-label={n.pinned ? "取消收藏" : "收藏笔记"}
                      onClick={(e) => {
                        e.stopPropagation();
                        togglePin(n);
                      }}
                      className={
                        "grid size-7 place-items-center rounded-full transition-colors " +
                        (n.pinned
                          ? "text-[#ed6f5c]"
                          : "text-[#8b8676] opacity-0 hover:bg-[#15140f0a] hover:text-[#15140f] group-hover:opacity-100")
                      }
                    >
                      <Star
                        className="size-4"
                        fill={n.pinned ? "currentColor" : "none"}
                      />
                    </button>
                  </div>
                </article>
              ))}

              {!displayed.length && (
                <div className="mt-16 flex flex-col items-start gap-3">
                  <span className="u-label">Empty</span>
                  <p className="text-[40px] font-extrabold leading-[0.95] tracking-[-0.035em]">
                    这里还没有笔记
                  </p>
                  <p className="text-[14px] text-[#5a5448]">
                    {query || tag
                      ? "换一个关键词，或清除筛选再试试"
                      : "从一条新的灵感开始吧"}
                  </p>
                  <Button onClick={newNote} className="mt-3 gap-2">
                    <Plus />
                    新建笔记
                  </Button>
                </div>
              )}
            </section>
          )}

          <footer className="-mx-14 flex shrink-0 items-center justify-between border-t border-[#15140f26] px-14 py-3 text-[14px] uppercase tracking-[0.16em] text-[#8b8676]">
            <span className="flex items-center gap-1.5">
              <ShieldCheck className="size-3.5" />
              数据保存在本机，不会上传
            </span>
            <span>知页 1.1.0</span>
          </footer>
        </main>
      </div>

      {/* ------------------------------------------------------------ drawer */}
      {selected && draft && (
        <>
          <div
            className="drawer-backdrop fixed inset-0 z-40 bg-[#15140f]/25"
            onClick={closeDrawer}
          />
          <aside
            className="note-drawer fixed inset-y-0 right-0 z-50 flex w-[min(560px,100vw)] flex-col border-l border-[#15140f1f] bg-[#f7f1de] shadow-[-18px_0_50px_-30px_rgba(21,20,15,0.4)]"
            data-testid="note-drawer"
          >
            <header className="flex h-12 shrink-0 items-center justify-between border-b border-border px-3">
              <span className="flex items-center gap-2 text-[14px] text-muted-foreground">
                <FileText className="size-3.5" />
                {selected.deleted ? "回收站笔记" : "笔记"}
              </span>
              <div className="flex items-center gap-0.5">
                <IconButton
                  icon={History}
                  label="历史版本"
                  onClick={history}
                  size="icon-sm"
                />
                <IconButton
                  icon={Trash2}
                  label={selected.deleted ? "恢复笔记" : "移入回收站"}
                  onClick={deleteOrRestore}
                  size="icon-sm"
                />
                <IconButton
                  icon={X}
                  label="关闭笔记"
                  onClick={closeDrawer}
                  size="icon-sm"
                />
              </div>
            </header>

            <div className="shrink-0 px-6 pb-4 pt-5">
              <div className="drawer-title">
                <input
                  aria-label="笔记标题"
                  value={draft.title}
                  disabled={selected.deleted}
                  onChange={(e) => changeDraft("title", e.target.value)}
                  className="w-full bg-transparent text-[28px] font-normal leading-[1.25] tracking-[-0.02em] outline-none placeholder:text-subtle disabled:opacity-60"
                  placeholder="无标题"
                />
              </div>
              <div className="mt-1.5 flex items-center gap-3 text-[14px] text-subtle">
                <span className="tabular-nums">
                  {dateLabel(selected.updated_at)}
                </span>
                <span className="tabular-nums">v{draft.revision}</span>
                <span
                  className={cn(
                    "flex items-center gap-1",
                    saveError && "text-destructive",
                  )}
                >
                  {saving ? (
                    <>
                      <Loader2 className="size-3 animate-spin" />
                      保存中
                    </>
                  ) : saveError ? (
                    <>
                      <AlertCircle className="size-3" />
                      保存失败，修改已保留
                    </>
                  ) : dirty ? (
                    <>
                      <Circle className="size-[6px] fill-current" />
                      未保存
                    </>
                  ) : (
                    <>
                      <Check className="size-3" />
                      已保存到本机
                    </>
                  )}
                </span>
              </div>
            </div>

            <div className="flex h-9 shrink-0 items-center justify-between border-y border-border bg-black/[0.02] px-3">
              <div className="flex items-center gap-0.5 rounded-md bg-black/[0.05] p-0.5">
                <button
                  onClick={async () => {
                    if (await saveDraft()) {
                      const n = await api("note", { id: selected.id });
                      setSelected(n);
                      selectedRef.current = n;
                      setEdit(false);
                    }
                  }}
                  className={cn(
                    "flex h-6 items-center gap-1.5 rounded px-2 text-[14px] transition-colors",
                    !edit
                      ? "bg-[#ed6f5c] text-white"
                      : "text-subtle hover:text-foreground",
                  )}
                >
                  <Eye className="size-3.5" />
                  阅读
                </button>
                <button
                  onClick={() => setEdit(true)}
                  disabled={selected.deleted}
                  className={cn(
                    "flex h-6 items-center gap-1.5 rounded px-2 text-[14px] transition-colors",
                    edit
                      ? "bg-[#ed6f5c] text-white"
                      : "text-subtle hover:text-foreground",
                  )}
                >
                  <Pencil className="size-3.5" />
                  编辑
                </button>
              </div>
              <div className="flex items-center gap-0.5">
                <IconButton
                  icon={Link2}
                  label="插入关联"
                  onClick={() => setModal("links")}
                  disabled={selected.deleted}
                  size="icon-sm"
                />
                <label className="ml-1 flex h-6 items-center gap-1 rounded border border-border px-1.5 text-[14px] text-subtle">
                  Aa
                  <select
                    aria-label="编辑器字号"
                    value={fontSize}
                    onChange={async (e) => {
                      const size = Number(e.target.value);
                      try {
                        await api("preferences", { font_size: size });
                        setFontSize(size);
                      } catch (err) {
                        notify(err.message, true);
                      }
                    }}
                    className="h-6 rounded border border-border bg-black/[0.03] px-1 text-[14px] text-muted-foreground outline-none"
                  >
                    {Array.from({ length: 13 }, (_, i) => (
                      <option key={i + 12}>{i + 12}</option>
                    ))}
                  </select>
                </label>
              </div>
            </div>

            {saveError && (
              <div className="flex items-center justify-between gap-3 border-b border-destructive/25 bg-destructive/10 px-5 py-2 text-[14px] text-destructive">
                {saveError}
                <button
                  onClick={() => {
                    navigator.clipboard?.writeText(draftRef.current.body);
                    notify("请核对剪贴板中的正文");
                  }}
                  className="shrink-0 rounded border border-destructive/30 px-2 py-0.5 text-[14px] hover:bg-destructive/15"
                >
                  复制正文留存
                </button>
              </div>
            )}

            {!edit && (
              <NoteFindPanel
                key={selected.id}
                previewRef={previewRef}
                contentVersion={selected.html}
              />
            )}
            <div className="drawer-content min-h-0 flex-1 overflow-auto px-5 py-4">
              {edit ? (
                <textarea
                  autoFocus
                  aria-label="Markdown正文"
                  value={draft.body}
                  style={{ fontSize }}
                  onChange={(e) => changeDraft("body", e.target.value)}
                  spellCheck={false}
                  className="h-full min-h-[280px] w-full resize-none bg-transparent leading-7 outline-none"
                />
              ) : (
                <div
                  className="markdown"
                  ref={previewRef}
                  style={{ fontSize }}
                  dangerouslySetInnerHTML={{ __html: readerHtml }}
                  onClick={(e) => {
                    const a = e.target.closest("a");
                    if (a) {
                      e.preventDefault();
                      const href = a.getAttribute("href") || "";
                      if (href.startsWith("#note:")) openNote(href.slice(6));
                      else if (href) notify("外部链接：" + href);
                    }
                  }}
                />
              )}
            </div>

            {edit && (
              <div className="flex shrink-0 items-center gap-2 border-t border-border px-5 py-2.5">
                <Hash className="size-4 shrink-0 text-subtle" />
                <input
                  aria-label="笔记标签"
                  disabled={selected.deleted}
                  value={draft.tagText}
                  onChange={(e) => changeDraft("tagText", e.target.value)}
                  placeholder="添加标签，用逗号分隔"
                  className="h-7 w-full bg-transparent text-[14px] outline-none placeholder:text-subtle disabled:opacity-60"
                />
              </div>
            )}

            <div className="shrink-0 border-t border-border px-5 py-2.5">
              <p className="mb-1.5 text-[14px] text-subtle">反向链接</p>
              {selected.backlinks?.length ? (
                <div className="space-y-0.5">
                  {selected.backlinks.map((n) => (
                    <button
                      key={n.id}
                      onClick={() => openNote(n.id)}
                      className="flex w-full items-center gap-1.5 rounded px-1.5 py-1 text-left text-[14px] text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
                    >
                      <Link2 className="size-3 shrink-0" />
                      <span className="min-w-0 flex-1 truncate">{n.title}</span>
                      <span className="tabular-nums text-subtle">
                        {n.count}
                      </span>
                    </button>
                  ))}
                </div>
              ) : (
                <p className="text-[14px] text-subtle">
                  还没有其他笔记链接到这里
                </p>
              )}
            </div>

            <footer className="flex h-12 shrink-0 items-center justify-between border-t border-border px-5">
              <span className="text-[14px] text-subtle">
                {selected.deleted
                  ? "恢复后可继续编辑"
                  : "停止输入后自动保存 · Ctrl S"}
              </span>
              <Button
                size="sm"
                disabled={saving || selected.deleted}
                onClick={saveDraft}
                className="gap-1.5"
              >
                <Save className="size-3.5" />
                保存
              </Button>
            </footer>
          </aside>
        </>
      )}

      {/* ------------------------------------------------------------ modals */}
      <Dialog
        open={Boolean(modal)}
        onOpenChange={(open) => !open && setModal(null)}
      >
        <DialogContent className="max-w-[480px]">
          <div className="pr-8">
            <DialogTitle>
              {
                {
                  settings: "偏好设置",
                  tools: "数据与备份",
                  history: "历史版本",
                  links: "插入关联",
                  about: "关于知识图谱",
                }[modal]
              }
            </DialogTitle>
            <DialogDescription className="mt-1">
              {
                {
                  settings: "调整阅读与编辑的显示方式。",
                  tools: "备份、恢复与导入导出都在本机完成。",
                  history: "回退到旧版本会生成一个新版本，不会丢失历史。",
                  links: "用稳定身份连接笔记，改名也不会断开。",
                  about: "节点是有效笔记，连线是正文里保存的关联。",
                }[modal]
              }
            </DialogDescription>
          </div>

          {modal === "settings" && (
            <div className="divide-y divide-border rounded-lg border border-border">
              <div className="flex items-center justify-between gap-6 px-3.5 py-3">
                <div>
                  <p className="text-[14px] font-medium">正文字号</p>
                  <p className="mt-0.5 text-[14px] text-subtle">
                    应用于阅读与编辑，保存后下次恢复
                  </p>
                </div>
                <select
                  aria-label="设置字号"
                  value={fontSize}
                  onChange={async (e) => {
                    const value = Number(e.target.value);
                    try {
                      await api("preferences", { font_size: value });
                      setFontSize(value);
                      notify("字号设置已保存");
                    } catch (err) {
                      notify(err.message, true);
                    }
                  }}
                  className="h-8 rounded-md border border-border bg-black/[0.03] px-2 text-[14px] text-muted-foreground outline-none hover:border-[#15140f66]"
                >
                  {Array.from({ length: 13 }, (_, i) => (
                    <option key={i}>{i + 12}</option>
                  ))}
                </select>
              </div>
              <div className="flex items-start gap-2.5 px-3.5 py-3 text-[14px] leading-5 text-subtle">
                <ShieldCheck className="mt-0.5 size-3.5 shrink-0" />
                知识库保存在本机，没有云端账号，也不会自动上传笔记。
              </div>
            </div>
          )}

          {modal === "tools" && (
            <div className="overflow-hidden rounded-lg border border-border">
              {[
                [
                  Download,
                  "创建完整备份",
                  "笔记、关联、历史与回收站",
                  "backup",
                  {},
                ],
                [
                  RotateCcw,
                  "从备份恢复",
                  "恢复前自动保留当前库",
                  "pick_restore",
                  {},
                ],
                [Upload, "导入 Markdown", "同名笔记会重命名", "import", {}],
                [
                  FolderOpen,
                  "导出为 HTML",
                  "选择空目录离线浏览",
                  "export",
                  { kind: "html" },
                ],
                [
                  FileText,
                  "导出为 Markdown",
                  "保留可读纯文本",
                  "export",
                  { kind: "markdown" },
                ],
              ].map(([Icon, title, sub, action, p], i) => (
                <button
                  key={title}
                  onClick={() => fileAction(action, p)}
                  className={cn(
                    "flex w-full items-center gap-3 px-3.5 py-2.5 text-left transition-colors hover:bg-accent",
                    i > 0 && "border-t border-border",
                  )}
                >
                  <Icon className="size-4 shrink-0 text-subtle" />
                  <span className="min-w-0 flex-1">
                    <span className="block text-[14px]">{title}</span>
                    <span className="block text-[14px] text-subtle">{sub}</span>
                  </span>
                  <ChevronRight className="size-3.5 shrink-0 text-subtle" />
                </button>
              ))}
            </div>
          )}

          {modal === "history" && (
            <div className="max-h-[380px] space-y-1.5 overflow-y-auto">
              {versions.map((v) => (
                <div
                  key={v.id}
                  className="version flex items-start justify-between gap-3 rounded-lg border border-border px-3 py-2.5"
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <Badge className="tabular-nums">v{v.revision}</Badge>
                      <span className="truncate text-[14px]">{v.title}</span>
                    </div>
                    <p className="mt-1 text-[14px] text-subtle">
                      {v.action} ·{" "}
                      {new Date(v.created_at).toLocaleString("zh-CN")}
                    </p>
                    <p className="mt-1 line-clamp-2 text-[14px] leading-4 text-muted-foreground">
                      {v.body.slice(0, 100)}
                    </p>
                  </div>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => restoreVersion(v)}
                    disabled={selected?.deleted}
                  >
                    恢复
                  </Button>
                </div>
              ))}
            </div>
          )}

          {modal === "links" && (
            <div className="link-choices max-h-[360px] space-y-0.5 overflow-y-auto rounded-lg border border-border p-1">
              {snapshot?.graph.nodes
                .filter((n) => n.id !== selected?.id)
                .map((n) => (
                  <button
                    key={n.id}
                    onClick={() => insertLink(n)}
                    className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-[14px] text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
                  >
                    <FileText className="size-3.5 shrink-0" />
                    <span className="min-w-0 flex-1 truncate">{n.title}</span>
                    <Plus className="size-3.5 shrink-0" />
                  </button>
                ))}
            </div>
          )}

          {modal === "about" && (
            <div className="space-y-3 text-[14px] leading-5 text-muted-foreground">
              <p>
                图谱展示最近 150
                篇有效笔记，全部内容仍可通过搜索查找。移入回收站的笔记会从图谱隐藏，恢复后重新出现。
              </p>
              <p className="rounded-lg border border-border px-3 py-2.5 text-[14px]">
                拖动旋转 · 滚轮缩放 ·
                点击节点阅读。图形环境不可用时，可从「全部笔记」打开内容。
              </p>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* ----------------------------------------------------------- confirm */}
      <Dialog
        open={Boolean(confirm)}
        onOpenChange={(open) => !open && answer(false)}
      >
        <DialogContent showClose={false} className="max-w-[380px]">
          <DialogTitle className="sr-only">确认继续</DialogTitle>
          {confirm && (
            <>
              <div className="flex items-start gap-3 pr-2">
                <span className="grid size-8 shrink-0 place-items-center rounded-lg border border-border bg-black/[0.05]">
                  <AlertCircle className="size-4 text-muted-foreground" />
                </span>
                <div className="min-w-0">
                  <h2 className="text-[14px] font-semibold">确认继续</h2>
                  <p className="mt-1 text-[14px] leading-5 text-muted-foreground">
                    {confirm.text}
                  </p>
                </div>
              </div>
              <div className="flex justify-end gap-2">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => answer(false)}
                >
                  {confirm.mode === "unsaved" ? "返回编辑" : "取消"}
                </Button>
                {confirm.mode === "unsaved" ? (
                  <>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                      onClick={() => answer("discard")}
                    >
                      放弃修改
                    </Button>
                    <Button size="sm" onClick={() => answer("save")}>
                      保存并继续
                    </Button>
                  </>
                ) : (
                  <Button size="sm" onClick={() => answer(true)}>
                    确定
                  </Button>
                )}
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>

      <Toaster />

      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        notes={paletteNotes}
        loading={paletteLoading}
        search={async (text) => {
          const data = await api("snapshot", { query: text });
          return data.notes || [];
        }}
        onOpenNote={(id) => {
          setPaletteOpen(false);
          openNote(id);
        }}
        onAction={(id) => {
          setPaletteOpen(false);
          if (["graph", "notes", "favorites", "trash"].includes(id))
            navigate(id);
          else if (id === "new") newNote();
          else if (id === "save") saveDraft();
          else if (id === "settings") setModal("settings");
          else if (id === "tools") setModal("tools");
          else if (id === "backup") fileAction("backup", {});
        }}
      />
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
