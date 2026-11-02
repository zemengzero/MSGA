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
import {
  Orbit,
  Search,
  Plus,
  Sparkles,
  LayoutGrid,
  Network,
  Star,
  Trash2,
  ArrowUpRight,
  ArrowLeft,
  X,
  Settings2,
  Database,
  Download,
  Upload,
  RotateCcw,
  History,
  Link2,
  Check,
  CheckCircle2,
  FileText,
  ChevronRight,
  Maximize2,
  MoreHorizontal,
  FolderOpen,
  ShieldCheck,
  Circle,
  Save,
  Pencil,
  Eye,
  Copy,
  Command,
  AlertCircle,
  Loader2,
  Hash,
  BookOpen,
  ExternalLink,
} from "lucide-react";
import "./style.css";
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
function Glyph({ icon: Icon, size = 18, ...rest }) {
  return <Icon size={size} strokeWidth={1.7} {...rest} />;
}
function IconButton({ icon, label, onClick, ...props }) {
  return (
    <button
      className="icon-button"
      title={label}
      aria-label={label}
      onClick={onClick}
      {...props}
    >
      <Glyph icon={icon} />
    </button>
  );
}

function Galaxy({ graph, matched, query, onOpen, paused }) {
  const ref = useRef();
  const host = useRef();
  const [size, setSize] = useState({ width: 700, height: 470 });
  const [hover, setHover] = useState(null);
  const [failed, setFailed] = useState(false);
  const [ready, setReady] = useState(false);
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
  useEffect(() => {
    const t = setTimeout(() => {
      setReady(true);
      if (ref.current) {
        ref.current.camera().zoom = 1.65;
        ref.current.camera().updateProjectionMatrix();
        ref.current.zoomToFit(900, 45);
      }
    }, 1600);
    return () => clearTimeout(t);
  }, [data]);
  const sphere = useCallback(
    (n) => {
      const group = new THREE.Group();
      const lit =
        (!query || hits.has(n.id)) && (!hover || neighbours.has(n.id));
      const r = 3 + Math.min(n.degree, 8) * 0.38;
      const orb = new THREE.Mesh(
        new THREE.SphereGeometry(r, 18, 14),
        new THREE.MeshBasicMaterial({
          color: lit ? n.color : "#333748",
          transparent: true,
          opacity: lit ? 0.95 : 0.24,
        }),
      );
      group.add(orb);
      const halo = new THREE.Mesh(
        new THREE.SphereGeometry(r * 1.9, 14, 10),
        new THREE.MeshBasicMaterial({
          color: n.color,
          transparent: true,
          opacity: lit ? 0.09 : 0.012,
          depthWrite: false,
        }),
      );
      group.add(halo);
      if (n.featured || n.id === hover) {
        const canvas = document.createElement("canvas");
        canvas.width = 640;
        canvas.height = 100;
        const ctx = canvas.getContext("2d");
        ctx.font = '32px "Microsoft YaHei UI", sans-serif';
        ctx.textAlign = "center";
        ctx.fillStyle = lit ? "#eef0ff" : "#666b84";
        ctx.fillText(n.title.slice(0, 16), 320, 55);
        const texture = new THREE.CanvasTexture(canvas);
        const sprite = new THREE.Sprite(
          new THREE.SpriteMaterial({
            map: texture,
            transparent: true,
            depthWrite: false,
          }),
        );
        sprite.scale.set(75, 12, 1);
        sprite.position.y = -r - 8;
        group.add(sprite);
      }
      return group;
    },
    [hover, neighbours, hits, query],
  );
  return (
    <div className="graph-stage" ref={host} data-testid="graph-stage">
      <div className="cosmic-grid" />
      <div className="orbital ring-one" />
      <div className="orbital ring-two" />
      {!failed && data.nodes.length > 0 ? (
        <ForceGraph3D
          ref={ref}
          graphData={data}
          width={size.width}
          height={size.height}
          backgroundColor="#10121d"
          showNavInfo={false}
          nodeThreeObject={sphere}
          nodeLabel={(n) => escapeHtml(n.title)}
          nodeRelSize={5}
          linkColor={(l) =>
            hover &&
            neighbours.has(l.source.id || l.source) &&
            neighbours.has(l.target.id || l.target)
              ? "#a799ed99"
              : "#7881b53f"
          }
          linkWidth={(l) =>
            hover && (l.source.id === hover || l.target.id === hover)
              ? 1.5
              : 0.45
          }
          linkOpacity={0.42}
          linkDirectionalParticles={(l) =>
            hover && (l.source.id === hover || l.target.id === hover) ? 2 : 0
          }
          linkDirectionalParticleWidth={1.1}
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
        <div className="graph-empty">
          <Orbit size={56} />
          <h3>
            {failed ? "当前设备未能加载3D图谱" : "让第一条灵感，成为起点"}
          </h3>
          <p>
            {failed
              ? "笔记仍可在“全部笔记”中正常使用"
              : "新建笔记，再用关联把想法连接起来"}
          </p>
        </div>
      )}
      <div className="graph-inset">
        <span className="live-dot" />
        关系随笔记同步
      </div>
      <div className="graph-controls">
        <IconButton
          icon={Maximize2}
          label="图谱居中"
          onClick={() => ref.current?.zoomToFit(700, 50)}
        />
      </div>
      <div className="graph-bottom">
        <span>
          <Circle size={11} /> 拖动旋转 · 滚轮缩放 · 点击阅读
        </span>
        <span>
          {data.nodes.length} 节点 · {data.links.length} 关联
        </span>
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
      <div className="graph-empty error-fallback">
        <Orbit size={48} />
        <h3>3D视图暂不可用</h3>
        <p>当前图形环境不支持，请从右侧卡片或“全部笔记”打开内容。</p>
      </div>
    ) : (
      this.props.children
    );
  }
}

function App() {
  const [snapshot, setSnapshot] = useState(null);
  const [route, setRoute] = useState("graph");
  const [query, setQuery] = useState("");
  const [tag, setTag] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [showDates, setShowDates] = useState(false);
  const [selected, setSelected] = useState(null);
  const [draft, setDraft] = useState(null);
  const draftRef = useRef(null);
  const selectedRef = useRef(null);
  const [dirty, setDirty] = useState(false);
  const dirtyRef = useRef(false);
  const [saving, setSaving] = useState(false);
  const saveTask = useRef(null);
  const [saveError, setSaveError] = useState("");
  const [edit, setEdit] = useState(false);
  const [modal, setModal] = useState(null);
  const [confirm, setConfirm] = useState(null);
  const [toast, setToast] = useState(null);
  const [fontSize, setFontSize] = useState(14);
  const [versions, setVersions] = useState([]);
  const queryRef = useRef();
  const request = useRef(0);
  const openRequest = useRef(0);
  const initialised = useRef(false);
  const notify = useCallback((message, bad = false) => {
    setToast({ message, bad });
    setTimeout(() => setToast(null), 5000);
  }, []);
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
                ? "；失败：" +
                  failed.map((i) => i.file + " " + i.error).join("；")
                : ""),
            failed.length > 0,
          );
        } else
          notify(
            action === "backup"
              ? "完整备份已保存：" + result.path
              : `已导出 ${result.count} 篇到：${result.path}`,
          );
      }
      await refresh();
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
        queryRef.current?.focus();
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
    graph: "知识星图",
    notes: "全部笔记",
    favorites: "我的收藏",
    trash: "回收站",
  }[route];
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-icon">
            <Orbit size={27} />
          </span>
          <div>
            <strong>
              知页<span> / </span>星图
            </strong>
            <small>CONNECT YOUR IDEAS</small>
          </div>
        </div>
        <div className="workspace-switch">
          <span className="workspace-avatar">知</span>
          <div>
            <strong>我的知识空间</strong>
            <small>
              {snapshot?.demo ? "演示空间 · 独立数据" : "个人空间 · 本机保存"}
            </small>
          </div>
          <ChevronRight size={15} />
        </div>
        <div className="section-caption">WORKSPACE</div>
        <nav>
          {[
            ["graph", Orbit, "知识星图"],
            ["notes", LayoutGrid, "全部笔记"],
            ["favorites", Star, "我的收藏"],
            ["trash", Trash2, "回收站"],
          ].map(([key, Icon, label]) => (
            <button
              key={key}
              className={"nav-item " + (route === key ? "active" : "")}
              onClick={() => navigate(key)}
            >
              <Glyph icon={Icon} />
              <span>{label}</span>
              {key === "notes" && <b>{snapshot?.stats.active || 0}</b>}
              {key === "graph" && <span className="nav-new">NEW</span>}
            </button>
          ))}
        </nav>
        <div className="section-caption tag-caption">
          我的标签 <span>{snapshot?.tags.length || 0}</span>
        </div>
        <div className="sidebar-tags">
          {snapshot?.tags.slice(0, 18).map((t) => (
            <button
              key={t.name}
              className={"tag-filter " + (tag === t.name ? "chosen" : "")}
              onClick={() => setTag(tag === t.name ? "" : t.name)}
            >
              <span className="color-dot" style={{ background: t.color }} />
              <span>{t.name}</span>
              <small>{t.count}</small>
            </button>
          ))}
        </div>
        <div className="sidebar-bottom">
          <div className="inspiration">
            <Sparkles size={20} />
            <strong>想法，因连接而闪光</strong>
            <p>
              记录一个念头，
              <br />
              发现一片新的宇宙。
            </p>
            <span className="mini-orbit" />
          </div>
          <button className="local-space" onClick={() => setModal("tools")}>
            <span className="local-icon">
              <Database size={18} />
            </span>
            <div>
              <strong>本地知识库</strong>
              <small>
                <span className="live-dot" /> 数据只在你的电脑
              </small>
            </div>
            <MoreHorizontal size={16} />
          </button>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            <span>个人空间</span>
            <ChevronRight size={13} />
            <strong>{pageTitle}</strong>
          </div>
          <div className="global-search">
            <Search size={16} />
            <input
              ref={queryRef}
              aria-label="搜索笔记"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="搜索你的想法与笔记…"
            />
            <kbd>Ctrl K</kbd>
          </div>
          <div className="top-actions">
            <span className="offline-badge">
              <span className="live-dot" />
              本地运行
            </span>
            <IconButton
              icon={Settings2}
              label="偏好设置"
              onClick={() => setModal("settings")}
            />
            <span className="profile">Z</span>
          </div>
        </header>
        <main className="workspace-content">
          <section className="page-heading">
            <div>
              <div className="overline">
                <Sparkles size={13} /> YOUR PERSONAL KNOWLEDGE UNIVERSE
              </div>
              <h1>
                {pageTitle}
                <span className="heading-star">✦</span>
              </h1>
              <p>
                {route === "trash"
                  ? "找回那些尚未消失的灵感。"
                  : "每一个想法，都有它的引力。让知识在连接中生长。"}
              </p>
            </div>
            <button className="primary new-note" onClick={newNote}>
              <Plus size={17} />
              新建笔记<span>N</span>
            </button>
          </section>
          <section className="stat-row">
            {[
              [
                FileText,
                "笔记总数",
                snapshot?.stats.active || 0,
                "每一条灵感，都值得留下",
                "purple",
              ],
              [
                Network,
                "知识连接",
                snapshot?.stats.connections || 0,
                "让孤立的想法，彼此相遇",
                "blue",
              ],
              [
                Hash,
                "探索领域",
                snapshot?.stats.tags || 0,
                "跨越边界，发现更多可能",
                "pink",
              ],
            ].map(([Icon, label, count, sub, color]) => (
              <div className={"stat-card " + color} key={label}>
                <div className="stat-icon">
                  <Icon size={21} />
                </div>
                <div className="stat-info">
                  <span>{label}</span>
                  <strong>
                    {count}
                    <small>{label === "探索领域" ? "个" : "条"}</small>
                  </strong>
                  <p>{sub}</p>
                </div>
                <span className="stat-decoration">↗</span>
              </div>
            ))}
          </section>
          {tag && (
            <div className="active-filter">
              <Hash size={13} />
              {tag}
              <button onClick={() => setTag("")} aria-label="清除标签筛选">
                <X size={13} />
              </button>
            </div>
          )}
          {snapshot?.capabilities?.date_filters && (
            <div className="date-filters">
              <span>按更新时间</span>
              <input
                type="date"
                aria-label="开始日期"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
              />
              <span>至</span>
              <input
                type="date"
                aria-label="结束日期"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
              />
              {(dateFrom || dateTo) && (
                <button
                  onClick={() => {
                    setDateFrom("");
                    setDateTo("");
                  }}
                >
                  清除日期
                </button>
              )}
            </div>
          )}
          {route === "graph" ? (
            <div className="dashboard-grid">
              <section className="graph-panel">
                <div className="panel-title">
                  <div>
                    <span className="panel-icon">
                      <Orbit size={18} />
                    </span>
                    <strong>你的知识宇宙</strong>
                    <span className="subtle-badge">3D 视图</span>
                  </div>
                  <IconButton
                    icon={MoreHorizontal}
                    label="图谱说明"
                    onClick={() => setModal("about")}
                  />
                </div>
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
                  <div className="loading">
                    <Loader2 className="spin" />
                    正在连接你的知识…
                  </div>
                )}
                <div className="graph-legend">
                  {snapshot?.tags.slice(0, 5).map((t) => (
                    <button
                      key={t.name}
                      onClick={() => setTag(tag === t.name ? "" : t.name)}
                    >
                      <i style={{ background: t.color }} />
                      {t.name}
                    </button>
                  ))}
                </div>
              </section>
              <aside className="insight-column">
                <section className="recent-panel">
                  <div className="panel-title">
                    <strong>{filtered ? "找回的想法" : "最近的灵感"}</strong>
                    <button
                      className="text-button"
                      onClick={() => navigate("notes")}
                    >
                      查看全部
                      <ChevronRight size={12} />
                    </button>
                  </div>
                  <div className="recent-list">
                    {displayed.slice(0, 4).map((n) => (
                      <button
                        className="recent-item"
                        key={n.id}
                        onClick={() => openNote(n.id)}
                      >
                        <span className="note-icon" style={{ color: n.color }}>
                          <FileText size={18} />
                        </span>
                        <div>
                          <strong>{n.title}</strong>
                          <p><HighlightedSnippet text={n.excerpt} ranges={n.snippet_highlights} /></p>
                          <small>
                            {dateLabel(n.updated_at)}
                            <span>·</span>
                            {n.tags[0] || "未分类"}
                          </small>
                        </div>
                        <ArrowUpRight size={14} />
                      </button>
                    ))}
                    {!displayed.length && (
                      <p className="quiet-empty">没有符合条件的笔记</p>
                    )}
                  </div>
                </section>
                <section className="distribution">
                  <div className="panel-title">
                    <strong>知识分布</strong>
                    <span className="muted">
                      {snapshot?.stats.tags || 0} 个标签
                    </span>
                  </div>
                  {snapshot?.tags.slice(0, 4).map((t) => (
                    <div className="distribution-row" key={t.name}>
                      <div>
                        <span>
                          <i style={{ background: t.color }} />
                          {t.name}
                        </span>
                        <small>{t.count} 篇</small>
                      </div>
                      <div className="track">
                        <span
                          style={{
                            width: `${Math.max(8, (t.count / Math.max(snapshot.stats.active, 1)) * 100)}%`,
                            background: t.color,
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </section>
              </aside>
            </div>
          ) : (
            <section className="notes-section">
              <div className="list-heading">
                <strong>
                  {filtered ? "搜索结果" : pageTitle}
                  <span>
                    {route === "favorites"
                      ? displayed.length
                      : snapshot?.match_count || 0}{" "}
                    篇
                  </span>
                </strong>
                <span>最近修改优先</span>
              </div>
              <div className="note-grid">
                {displayed.map((n) => (
                  <article
                    key={n.id}
                    className="note-card"
                    onClick={() => openNote(n.id)}
                    tabIndex={0}
                    onKeyDown={(e) => e.key === "Enter" && openNote(n.id)}
                  >
                    <div className="note-card-top">
                      <span className="note-icon" style={{ color: n.color }}>
                        <FileText size={19} />
                      </span>
                      <button
                        className={
                          "icon-button " + (n.pinned ? "is-pinned" : "")
                        }
                        aria-label={n.pinned ? "取消收藏" : "收藏笔记"}
                        onClick={(e) => {
                          e.stopPropagation();
                          togglePin(n);
                        }}
                      >
                        <Star size={16} />
                      </button>
                    </div>
                    <h3>{n.title}</h3>
                    <p><HighlightedSnippet text={n.excerpt} ranges={n.snippet_highlights} /></p>
                    <div className="note-card-tags">
                      {n.tags.slice(0, 3).map((t) => (
                        <span key={t}># {t}</span>
                      ))}
                    </div>
                    <footer>
                      <span>{dateLabel(n.updated_at)}</span>
                      <span>
                        v{n.revision}
                        <ArrowUpRight size={14} />
                      </span>
                    </footer>
                  </article>
                ))}
              </div>
              {!displayed.length && (
                <div className="empty-state">
                  <BookOpen size={36} />
                  <h3>这里还没有笔记</h3>
                  <p>
                    {query || tag
                      ? "换一个关键词，或清除筛选再试试"
                      : "从一条新的灵感开始吧"}
                  </p>
                  <button className="primary" onClick={newNote}>
                    <Plus size={16} />
                    记录一个想法
                  </button>
                </div>
              )}
            </section>
          )}
          <footer className="workspace-footer">
            <span>
              <ShieldCheck size={13} /> 灵感属于你，数据也属于你。
            </span>
            <span>知页 · CONNECT YOUR IDEAS</span>
          </footer>
        </main>
      </div>
      {selected && draft && (
        <>
          <div className="drawer-backdrop" onClick={closeDrawer} />
          <aside className="note-drawer" data-testid="note-drawer">
            <header>
              <span>
                <FileText size={16} />{" "}
                {selected.deleted ? "回收站笔记" : "灵感笔记"}
              </span>
              <div>
                <IconButton icon={History} label="历史版本" onClick={history} />
                <IconButton
                  icon={Trash2}
                  label={selected.deleted ? "恢复笔记" : "移入回收站"}
                  onClick={deleteOrRestore}
                />
                <IconButton icon={X} label="关闭笔记" onClick={closeDrawer} />
              </div>
            </header>
            <div className="drawer-title">
              <input
                aria-label="笔记标题"
                value={draft.title}
                disabled={selected.deleted}
                onChange={(e) => changeDraft("title", e.target.value)}
              />
              <div className="note-meta">
                <span>{dateLabel(selected.updated_at)}</span>
                <span>v{draft.revision}</span>
                <span className={saveError ? "save-error" : ""}>
                  {saving ? (
                    <>
                      <Loader2 size={12} className="spin" />
                      保存中
                    </>
                  ) : saveError ? (
                    <>
                      <AlertCircle size={12} />
                      保存失败，修改已保留
                    </>
                  ) : dirty ? (
                    <>
                      <Circle size={10} />
                      未保存
                    </>
                  ) : (
                    <>
                      <Check size={12} />
                      已保存到本机
                    </>
                  )}
                </span>
              </div>
            </div>
            <div className="editor-toolbar">
              <div className="segmented">
                <button
                  className={!edit ? "selected" : ""}
                  onClick={async () => {
                    if (await saveDraft()) {
                      const n = await api("note", { id: selected.id });
                      setSelected(n);
                      selectedRef.current = n;
                      setEdit(false);
                    }
                  }}
                >
                  <Eye size={14} />
                  阅读
                </button>
                <button
                  className={edit ? "selected" : ""}
                  onClick={() => setEdit(true)}
                  disabled={selected.deleted}
                >
                  <Pencil size={14} />
                  编辑
                </button>
              </div>
              <div>
                <IconButton
                  icon={Link2}
                  label="插入关联"
                  onClick={() => setModal("links")}
                  disabled={selected.deleted}
                />
                <label className="font-picker">
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
                  >
                    {Array.from({ length: 13 }, (_, i) => (
                      <option key={i + 12}>{i + 12}</option>
                    ))}
                  </select>
                </label>
              </div>
            </div>
            {saveError && (
              <div className="editor-error">
                {saveError}
                <button
                  onClick={() => {
                    navigator.clipboard?.writeText(draftRef.current.body);
                    notify("请核对剪贴板中的正文");
                  }}
                >
                  复制正文留存
                </button>
              </div>
            )}
            <div className="drawer-content">
              {edit ? (
                <textarea
                  autoFocus
                  aria-label="Markdown正文"
                  value={draft.body}
                  style={{ fontSize }}
                  onChange={(e) => changeDraft("body", e.target.value)}
                  spellCheck={false}
                />
              ) : (
                <div
                  className="markdown"
                  style={{ fontSize }}
                  dangerouslySetInnerHTML={{ __html: selected.html || "" }}
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
            <div className="tag-editor">
              <Hash size={14} />
              <input
                aria-label="笔记标签"
                disabled={selected.deleted}
                value={draft.tagText}
                onChange={(e) => changeDraft("tagText", e.target.value)}
                placeholder="添加标签，用逗号分隔"
              />
            </div>
            <div className="backlinks">
              <small>反向关联</small>
              {selected.backlinks?.length ? (
                selected.backlinks.map((n) => (
                  <button key={n.id} onClick={() => openNote(n.id)}>
                    <Link2 size={12} />
                    {n.title}
                    <ChevronRight size={12} />
                  </button>
                ))
              ) : (
                <span>还没有其他笔记链接到这里</span>
              )}
            </div>
            <footer className="drawer-footer">
              <span>
                {selected.deleted
                  ? "点击恢复按钮，可找回这条笔记"
                  : "静止输入后自动保存 · Ctrl S 手动保存"}
              </span>
              <button
                className="primary"
                disabled={saving || selected.deleted}
                onClick={saveDraft}
              >
                <Save size={14} />
                保存
              </button>
            </footer>
          </aside>
        </>
      )}
      {modal && (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <section
            className={"modal " + (modal === "history" ? "wide-modal" : "")}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-heading">
              <h2>
                {
                  {
                    settings: "让记录更舒适",
                    tools: "数据与备份",
                    history: "每一个版本，都有来路",
                    links: "连接一个想法",
                    about: "关于这片知识宇宙",
                  }[modal]
                }
              </h2>
              <IconButton
                icon={X}
                label="关闭窗口"
                onClick={() => setModal(null)}
              />
            </div>
            {modal === "settings" && (
              <>
                <p className="modal-description">
                  为你的阅读与记录，找到舒服的节奏。
                </p>
                <div className="setting-row">
                  <div>
                    <strong>文字大小</strong>
                    <p>应用于笔记阅读与编辑，保存后下次恢复。</p>
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
                  >
                    {Array.from({ length: 13 }, (_, i) => (
                      <option key={i}>{i + 12}</option>
                    ))}
                  </select>
                </div>
                <div className="privacy-note">
                  <ShieldCheck size={20} />
                  <p>
                    你的知识库保存在本机。这里没有云端账号，也不会自动上传笔记。
                  </p>
                </div>
              </>
            )}
            {modal === "tools" && (
              <>
                <p className="modal-description">给知识一个安全的归处。</p>
                <div className="tool-grid">
                  {[
                    [
                      Download,
                      "创建完整备份",
                      "包括笔记、关联、历史与回收站",
                      "backup",
                      {},
                    ],
                    [
                      RotateCcw,
                      "从备份恢复",
                      "恢复前自动保留当前库的保护副本",
                      "pick_restore",
                      {},
                    ],
                    [
                      Upload,
                      "导入Markdown",
                      "同名笔记会重命名，保留已有内容",
                      "import",
                      {},
                    ],
                    [
                      FolderOpen,
                      "导出为HTML",
                      "选择空目录，离线浏览你的笔记",
                      "export",
                      { kind: "html" },
                    ],
                    [
                      FileText,
                      "导出为Markdown",
                      "选择空目录，保留可读内容",
                      "export",
                      { kind: "markdown" },
                    ],
                  ].map(([Icon, title, sub, action, p]) => (
                    <button
                      key={title}
                      className="tool-option"
                      onClick={() => fileAction(action, p)}
                    >
                      <Icon size={21} />
                      <div>
                        <strong>{title}</strong>
                        <p>{sub}</p>
                      </div>
                      <ChevronRight size={15} />
                    </button>
                  ))}
                </div>
              </>
            )}
            {modal === "history" && (
              <>
                <p className="modal-description">
                  回到旧内容，会生成一个新版本，不覆盖已有历史。
                </p>
                <div className="history-list">
                  {versions.map((v) => (
                    <div className="version" key={v.id}>
                      <div>
                        <span className="version-badge">v{v.revision}</span>
                        <strong>{v.title}</strong>
                        <p>
                          {v.action} ·{" "}
                          {new Date(v.created_at).toLocaleString("zh-CN")}
                        </p>
                        <p className="version-excerpt">
                          {v.body.slice(0, 100)}
                        </p>
                      </div>
                      <button
                        className="secondary"
                        onClick={() => restoreVersion(v)}
                        disabled={selected?.deleted}
                      >
                        恢复
                      </button>
                    </div>
                  ))}
                </div>
              </>
            )}
            {modal === "links" && (
              <>
                <p className="modal-description">
                  以稳定身份连接笔记，改名也不会丢失关联。
                </p>
                <div className="link-choices">
                  {snapshot?.graph.nodes
                    .filter((n) => n.id !== selected?.id)
                    .map((n) => (
                      <button key={n.id} onClick={() => insertLink(n)}>
                        <FileText size={15} />
                        {n.title}
                        <Plus size={14} />
                      </button>
                    ))}
                </div>
              </>
            )}
            {modal === "about" && (
              <>
                <p className="modal-description">
                  每一个节点是一篇有效笔记，每一条线是正文中实际保存的关联。
                </p>
                <p className="modal-description">
                  改名保留身份；移入回收站后从星图隐藏，恢复后重新出现。图谱展示最近150篇有效笔记，全部内容仍可通过搜索查找。
                </p>
                <div className="privacy-note">
                  <Orbit size={24} />
                  <p>
                    可以拖动旋转、滚轮缩放，点击节点阅读。图形环境暂不可用时，仍可从笔记列表打开内容。
                  </p>
                </div>
              </>
            )}
          </section>
        </div>
      )}
      {confirm && (
        <div className="modal-overlay confirm-layer">
          <section className="modal confirm-modal">
            <div className="confirm-symbol">
              <AlertCircle size={24} />
            </div>
            <h2>确认继续</h2>
            <p className="modal-description">{confirm.text}</p>
            <div className="confirm-actions">
              <button className="secondary" onClick={() => answer(false)}>
                {confirm.mode === "unsaved" ? "返回编辑" : "取消"}
              </button>
              {confirm.mode === "unsaved" ? (
                <>
                  <button
                    className="secondary danger-text"
                    onClick={() => answer("discard")}
                  >
                    放弃修改
                  </button>
                  <button className="primary" onClick={() => answer("save")}>
                    保存并继续
                  </button>
                </>
              ) : (
                <button className="primary" onClick={() => answer(true)}>
                  确定
                </button>
              )}
            </div>
          </section>
        </div>
      )}
      {toast && (
        <div className={"toast " + (toast.bad ? "bad" : "")} role="status">
          {toast.bad ? <AlertCircle size={17} /> : <CheckCircle2 size={17} />}
          <span>{toast.message}</span>
          <button onClick={() => setToast(null)} aria-label="关闭提示">
            <X size={14} />
          </button>
        </div>
      )}
    </div>
  );
}
createRoot(document.getElementById("root")).render(<App />);
