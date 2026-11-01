"""Tk desktop views; domain and persistence live in separate modules."""

import json
import os
import re
import sqlite3
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .backup import create_backup, inspect_backup, restore_backup
from .links import backlinks, extract_links
from .models import AppError, ValidationError
from .search import search_notes, tag_counts
from .transfer import export_notes, import_markdown

BG = "#f3f6fb"
INK = "#172b45"
MUTED = "#5b6e85"
BLUE = "#285dde"
NAV = "#172c49"


class NotebookApp:
    def __init__(self, root, store, data_dir, demo=False):
        self.root, self.store, self.data_dir, self.demo = (
            root,
            store,
            Path(data_dir),
            demo,
        )
        self.current = None
        self.dirty = False
        self.loading = False
        self.trash = False
        self.after_save = None
        self.after_preview = None
        self.after_search = None
        self.smoke_error = None
        self.modal_guard = False
        self.editor_font_size = self._read_font_size()
        self.font_size_var = tk.StringVar(value=str(self.editor_font_size))
        self.title_var = tk.StringVar()
        self.tags_var = tk.StringVar()
        self.query_var = tk.StringVar()
        self.filter_var = tk.StringVar()
        self.status_var = tk.StringVar(value="所有内容只保存在本机")
        root.title("知页 · 本地学习知识库")
        root.geometry("1480x900")
        root.minsize(980, 640)
        root.configure(bg=BG)
        icon = Path(__file__).with_name("assets") / "icon.ico"
        if os.name == "nt" and icon.exists():
            root.iconbitmap(str(icon))
        self._styles()
        self._layout()
        root.bind("<Configure>", self._window_resized, add="+")
        self.title_var.trace_add("write", lambda *_: self._changed())
        self.tags_var.trace_add("write", lambda *_: self._changed())
        self.query_var.trace_add("write", lambda *_: self._schedule_search())
        self.filter_var.trace_add("write", lambda *_: self._schedule_search())
        root.bind("<Control-s>", lambda _e: self.save())
        root.bind("<Control-n>", lambda _e: self.new_note())
        root.bind("<Control-f>", lambda _e: self.search_entry.focus_set())
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.report_callback_exception = self._callback_error
        self.refresh()
        root.after(10000, self._autosave_tick)

    def _styles(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("TFrame", background=BG)
        s.configure("White.TFrame", background="white")
        s.configure(
            "TLabel", background=BG, foreground=INK, font=("Microsoft YaHei UI", 10)
        )
        s.configure(
            "TButton",
            font=("Microsoft YaHei UI", 10),
            padding=(10, 7),
            background="white",
            foreground=INK,
            borderwidth=0,
        )
        s.map("TButton", background=[("active", "#e7eefc")])
        s.configure("Accent.TButton", background=BLUE, foreground="white")
        s.map(
            "Accent.TButton",
            background=[("active", "#1748b6"), ("disabled", "#9aacce")],
        )
        s.configure(
            "TEntry",
            fieldbackground="white",
            padding=7,
            bordercolor="#dce3ef",
            lightcolor="#dce3ef",
        )
        s.configure(
            "Treeview",
            font=("Microsoft YaHei UI", 10),
            rowheight=44,
            fieldbackground="white",
            background="white",
            foreground=INK,
            borderwidth=0,
        )
        s.configure(
            "Treeview.Heading",
            font=("Microsoft YaHei UI", 9),
            padding=8,
            background="#eef3fa",
            foreground=MUTED,
        )
        s.map(
            "Treeview",
            background=[("selected", "#e4edff")],
            foreground=[("selected", BLUE)],
        )

    def _read_font_size(self):
        size = self.store.settings("editor_font_size", 12)
        return size if type(size) is int and 12 <= size <= 24 else 12

    def set_editor_font_size(self, size):
        if type(size) is not int or not 12 <= size <= 24:
            raise ValidationError("编辑器字号必须为12–24之间的整数")
        self.store.set_setting("editor_font_size", size)
        self.editor.configure(font=("Consolas", size))
        self.editor_font_size = size
        self.font_size_var.set(str(size))

    def _font_selected(self, _event=None):
        try:
            self.set_editor_font_size(int(self.font_size_var.get()))
        except (ValueError, AppError, sqlite3.Error) as exc:
            self.font_size_var.set(str(self.editor_font_size))
            messagebox.showerror("字号设置未保存", str(exc), parent=self.root)

    def _label(self, parent, text, font=10, fg=INK, bg="white", **kw):
        return tk.Label(
            parent, text=text, font=("Microsoft YaHei UI", font), fg=fg, bg=bg, **kw
        )

    def _layout(self):
        top = tk.Frame(self.root, bg="white", height=78)
        top.pack(fill="x")
        top.pack_propagate(False)
        brand = tk.Frame(top, bg="white")
        brand.pack(side="left", padx=25, pady=13)
        self._label(brand, "知页", 24, BLUE).pack(side="left")
        self._label(
            brand, "  LOCAL KNOWLEDGE\n  本地学习知识库", 9, MUTED, justify="left"
        ).pack(side="left", padx=8)
        self._label(
            top, "演示库 · 合成示例" if self.demo else "离线空间 · 本机保存", 10, BLUE
        ).pack(side="right", padx=28)
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True)
        sidebar = tk.Frame(body, bg=NAV, width=205)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        self._label(sidebar, "WORKSPACE", 9, "#91aacb", NAV, anchor="w").pack(
            fill="x", padx=22, pady=(25, 13)
        )
        for text, command in [
            ("全部笔记", lambda: self.set_view(False)),
            ("回收站", lambda: self.set_view(True)),
            ("导入 Markdown", self.import_files),
            ("备份与恢复", self.backup_menu),
        ]:
            tk.Button(
                sidebar,
                text=text,
                command=command,
                bg=NAV,
                fg="white",
                activebackground="#29476d",
                activeforeground="white",
                font=("Microsoft YaHei UI", 11),
                bd=0,
                anchor="w",
                padx=22,
                pady=12,
                cursor="hand2",
            ).pack(fill="x")
        self._label(sidebar, "标签 / TAGS", 9, "#91aacb", NAV, anchor="w").pack(
            fill="x", padx=22, pady=(28, 8)
        )
        tagarea = tk.Frame(sidebar, bg=NAV)
        tagarea.pack(fill="both", expand=True)
        tagcanvas = tk.Canvas(tagarea, bg=NAV, highlightthickness=0, width=160)
        tagscroll = ttk.Scrollbar(tagarea, orient="vertical", command=tagcanvas.yview)
        tagscroll.pack(side="right", fill="y")
        tagcanvas.pack(side="left", fill="both", expand=True)
        tagcanvas.configure(yscrollcommand=tagscroll.set)
        self.tag_frame = tk.Frame(tagcanvas, bg=NAV)
        tagwindow = tagcanvas.create_window((0, 0), window=self.tag_frame, anchor="nw")
        self.tag_frame.bind(
            "<Configure>",
            lambda _e: tagcanvas.configure(scrollregion=tagcanvas.bbox("all")),
        )
        tagcanvas.bind(
            "<Configure>", lambda e: tagcanvas.itemconfigure(tagwindow, width=e.width)
        )
        self.sidebar_stats = self._label(
            sidebar, "", 10, "#bdcde3", NAV, justify="left", anchor="w"
        )
        self.sidebar_stats.pack(
            side="bottom", fill="x", padx=22, pady=12, before=tagarea
        )
        right = tk.Frame(body, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=18, pady=16)
        heading = tk.Frame(right, bg=BG)
        heading.pack(fill="x", pady=(0, 12))
        self.heading_label = self._label(heading, "我的知识库", 20, INK, BG)
        self.heading_label.pack(side="left")
        toolbar = tk.Frame(right, bg=BG)
        toolbar.pack(fill="x", pady=(0, 10))
        for text, command in [
            ("新建笔记", self.new_note),
            ("保存", self.save),
            ("插入关联", self.insert_link),
            ("历史版本", self.show_history),
            ("移入回收站", self.delete_action),
        ]:
            btn = ttk.Button(
                toolbar,
                text=text,
                command=command,
                width=0,
                style="Accent.TButton" if text == "新建笔记" else "TButton",
            )
            btn.pack(side="left", padx=3)
            if text == "移入回收站":
                self.delete_button = btn
            if text == "保存":
                self.save_button = btn
        paned = tk.PanedWindow(right, orient="horizontal", bg=BG, sashwidth=10, bd=0)
        self.paned = paned
        paned.pack(fill="both", expand=True)
        left = tk.Frame(paned, bg="white")
        paned.add(left, minsize=225, width=275)
        self._label(left, "搜索与筛选", 11, INK, anchor="w").pack(
            fill="x", padx=13, pady=(14, 6)
        )
        self.search_entry = ttk.Entry(left, textvariable=self.query_var)
        self.search_entry.pack(fill="x", padx=12)
        self._label(left, "关键词可查标题与正文", 9, MUTED, anchor="w").pack(
            fill="x", padx=13, pady=(4, 10)
        )
        ttk.Entry(left, textvariable=self.filter_var).pack(fill="x", padx=12)
        self._label(left, "标签用逗号分隔，多个条件取 AND", 8, MUTED, anchor="w").pack(
            fill="x", padx=13, pady=(3, 8)
        )
        self.result_label = self._label(left, "", 9, MUTED, anchor="w")
        self.result_label.pack(fill="x", padx=13, pady=6)
        listframe = tk.Frame(left, bg="white")
        listframe.pack(fill="both", expand=True, padx=3, pady=3)
        self.list = ttk.Treeview(
            listframe, columns=("title",), show="headings", selectmode="browse"
        )
        self.list.heading("title", text="笔记标题")
        self.list.column("title", width=240)
        self.list_scrollbar = ttk.Scrollbar(
            listframe, orient="vertical", command=self.list.yview
        )
        self.list_scrollbar.pack(side="right", fill="y")
        self.list.pack(side="left", fill="both", expand=True)
        self.list.configure(yscrollcommand=self.list_scrollbar.set)
        self.list.bind("<<TreeviewSelect>>", self._selected)
        actions = tk.Frame(left, bg="white")
        actions.pack(side="bottom", fill="x", padx=9, pady=10, before=listframe)
        ttk.Button(actions, text="导出 HTML", command=lambda: self.export("html")).pack(
            side="left"
        )
        ttk.Button(actions, text="更多", command=self.more_menu).pack(side="right")
        center = tk.Frame(paned, bg="white")
        paned.add(center, minsize=330, width=465)
        self.title_entry = ttk.Entry(
            center, textvariable=self.title_var, font=("Microsoft YaHei UI", 18, "bold")
        )
        self.title_entry.pack(fill="x", padx=16, pady=(16, 7))
        self.save_state = self._label(center, "选择一篇笔记开始", 9, MUTED, anchor="w")
        self.save_state.pack(fill="x", padx=18, pady=(0, 10))
        fontrow = tk.Frame(center, bg="white")
        fontrow.pack(fill="x", padx=18, pady=(0, 4))
        self._label(fontrow, "编辑器字号", 9, MUTED).pack(side="left")
        self.font_picker = ttk.Combobox(
            fontrow,
            textvariable=self.font_size_var,
            values=tuple(range(12, 25)),
            width=4,
            state="readonly",
        )
        self.font_picker.pack(side="left", padx=8)
        self.font_picker.bind("<<ComboboxSelected>>", self._font_selected)
        self.narrow_hint = self._label(center, "", 8, MUTED, anchor="w")
        self.narrow_hint.pack(fill="x", padx=18)
        editor_frame = tk.Frame(center, bg="white")
        editor_frame.pack(fill="both", expand=True)
        self.editor = tk.Text(
            editor_frame,
            wrap="word",
            undo=True,
            maxundo=200,
            font=("Consolas", self.editor_font_size),
            bg="white",
            fg=INK,
            insertbackground=BLUE,
            bd=0,
            padx=18,
            pady=12,
            spacing1=3,
            spacing3=5,
        )
        self.editor_scrollbar = ttk.Scrollbar(
            editor_frame, orient="vertical", command=self.editor.yview
        )
        self.editor_scrollbar.pack(side="right", fill="y")
        self.editor.pack(side="left", fill="both", expand=True)
        self.editor.configure(yscrollcommand=self.editor_scrollbar.set)
        self.editor.bind("<Control-Tab>", self._focus_tags)
        self.editor.bind("<<Modified>>", self._text_changed)
        tagrow = tk.Frame(center, bg="#f7f9fd")
        tagrow.pack(side="bottom", fill="x", before=editor_frame)
        self._label(tagrow, "标签", 10, MUTED, "#f7f9fd").pack(side="left", padx=12)
        self.tags_entry = ttk.Entry(tagrow, textvariable=self.tags_var)
        self.tags_entry.pack(side="left", fill="x", expand=True, padx=8, pady=10)
        self.tags_entry.bind("<Control-Tab>", self._focus_editor)
        previewbox = tk.Frame(paned, bg="white")
        self.previewbox = previewbox
        self.preview_visible = True
        paned.add(previewbox, minsize=300, width=385)
        self._label(previewbox, "阅读视图 / PREVIEW", 10, BLUE, anchor="w").pack(
            fill="x", padx=18, pady=(18, 8)
        )
        preview_frame = tk.Frame(previewbox, bg="white")
        preview_frame.pack(fill="both", expand=True)
        self.preview = tk.Text(
            preview_frame,
            wrap="word",
            font=("Microsoft YaHei UI", 11),
            bg="white",
            fg=INK,
            bd=0,
            padx=18,
            pady=10,
            spacing3=9,
            state="disabled",
            cursor="arrow",
        )
        self.preview_scrollbar = ttk.Scrollbar(
            preview_frame, orient="vertical", command=self.preview.yview
        )
        self.preview_scrollbar.pack(side="right", fill="y")
        self.preview.pack(side="left", fill="both", expand=True)
        self.preview.configure(yscrollcommand=self.preview_scrollbar.set)
        for name, font, color in [
            ("h1", ("Microsoft YaHei UI", 20, "bold"), INK),
            ("h2", ("Microsoft YaHei UI", 15, "bold"), INK),
            ("strong", ("Microsoft YaHei UI", 11, "bold"), INK),
            ("code", ("Consolas", 10), "#475873"),
            ("link", ("Microsoft YaHei UI", 11), BLUE),
        ]:
            self.preview.tag_configure(name, font=font, foreground=color)
        self.backlink_frame = tk.Frame(previewbox, bg="white", height=90)
        self.backlink_frame.pack(
            side="bottom", fill="x", padx=12, pady=(0, 12), before=preview_frame
        )
        self._label(previewbox, "反向引用", 10, MUTED, anchor="w").pack(
            side="bottom", fill="x", padx=18, pady=(10, 2), before=preview_frame
        )
        bottom = tk.Frame(self.root, bg="white")
        bottom.pack(side="bottom", fill="x", before=body)
        self._label(
            bottom, "", 9, MUTED, textvariable=self.status_var, anchor="w"
        ).pack(side="left", fill="x", expand=True, padx=22, pady=8)
        self._label(
            bottom, "Ctrl+N 新建  ·  Ctrl+S 保存  ·  Ctrl+F 搜索", 9, MUTED
        ).pack(side="right", padx=20)

    def _window_resized(self, event):
        if event.widget is not self.root:
            return
        visible = event.width >= 1200
        if visible == self.preview_visible:
            return
        if visible:
            self.paned.add(self.previewbox, minsize=300, width=385)
        else:
            self.paned.forget(self.previewbox)
        self.preview_visible = visible
        self.narrow_hint.configure(
            text="" if visible else "窗口较窄，阅读视图已收起；放宽窗口即可恢复"
        )

    def _focus_tags(self, _event=None):
        self.tags_entry.focus_set()
        return "break"

    def _focus_editor(self, _event=None):
        self.editor.focus_set()
        return "break"

    def _callback_error(self, kind, value, tb):
        self.smoke_error = str(value)
        self.error(value)

    def error(self, exc):
        self.status_var.set("操作未完成；未保存内容仍保留在编辑器")
        if self.store.writes_disabled:
            self.save_button.configure(state="disabled")
            self.save_state.configure(text="恢复保护状态 · 已停止写入", fg="#a34b12")
        messagebox.showerror("操作未完成", str(exc), parent=self.root)

    def _changed(self):
        if self.loading or self.current is None or self.current.deleted:
            return
        self.dirty = True
        self.save_state.configure(text="未保存 · 内容尚未写入本机", fg="#a34b12")
        if self.after_save:
            self.root.after_cancel(self.after_save)
        self.after_save = self.root.after(1200, lambda: self.save(silent=True))
        if self.after_preview:
            self.root.after_cancel(self.after_preview)
        self.after_preview = self.root.after(200, self.render_preview)

    def _text_changed(self, _event):
        if self.editor.edit_modified():
            self.editor.edit_modified(False)
            self._changed()

    def _autosave_tick(self):
        if self.dirty and not self.modal_guard:
            self.save(silent=True)
        self.root.after(10000, self._autosave_tick)

    def _schedule_search(self):
        if self.after_search:
            self.root.after_cancel(self.after_search)
        self.after_search = self.root.after(220, lambda: self.refresh(autoselect=False))

    def guard(self):
        if not self.dirty:
            return True
        if self.modal_guard:
            return False
        if self.after_save:
            self.root.after_cancel(self.after_save)
            self.after_save = None
        self.modal_guard = True
        try:
            answer = messagebox.askyesnocancel(
                "有未保存内容",
                "是否先保存？\n选择“否”将在切换时放弃当前修改；备份与导出只使用已保存内容。",
                parent=self.root,
            )
        finally:
            self.modal_guard = False
        if answer is None:
            return False
        return self.save() if answer else True

    def _selected(self, _event):
        chosen = self.list.selection()
        if chosen and (self.current is None or chosen[0] != self.current.id):
            if (
                not self.open_note(chosen[0])
                and self.current
                and self.list.exists(self.current.id)
            ):
                self.list.selection_set(self.current.id)

    def set_view(self, trash):
        if not self.guard():
            return
        self.trash = trash
        self.current = None
        self.dirty = False
        self.refresh()

    def refresh(self, select_id=None, autoselect=True):
        notes = search_notes(
            self.store, self.query_var.get(), self.filter_var.get(), self.trash
        )
        for item in self.list.get_children():
            self.list.delete(item)
        for note in notes:
            self.list.insert("", "end", iid=note.id, values=(note.title,))
        self.result_label.configure(
            text=f"找到 {len(notes)} 篇"
            + (" · 回收站" if self.trash else " · 最近修改优先")
        )
        self.heading_label.configure(text="回收站" if self.trash else "我的知识库")
        self.delete_button.configure(text="恢复笔记" if self.trash else "移入回收站")
        stat = self.store.stats()
        self.sidebar_stats.configure(
            text=f"{stat['active']} 篇有效笔记\n{stat['tags']} 个标签\n{stat['versions']} 个版本\n回收站 {stat['trash']} 篇"
        )
        for child in self.tag_frame.winfo_children():
            child.destroy()
        tags = tag_counts(self.store)
        for tag, count in tags[:100]:
            tk.Button(
                self.tag_frame,
                text=f"# {tag}    {count}",
                command=lambda t=tag: self.filter_var.set(t),
                anchor="w",
                bg=NAV,
                fg="#ccdbed",
                activebackground="#29476d",
                bd=0,
                padx=22,
                pady=5,
                font=("Microsoft YaHei UI", 9),
            ).pack(fill="x")
        if len(tags) > 100:
            self._label(
                self.tag_frame,
                "仅列前100个标签，其他标签可在筛选框输入",
                8,
                "#ccdbed",
                NAV,
                wraplength=160,
                justify="left",
            ).pack(fill="x", padx=12, pady=8)
        pick = select_id or (self.current.id if self.current else None)
        if pick and self.list.exists(pick):
            self.list.selection_set(pick)
            self.list.see(pick)
        elif self.current is None and notes and autoselect:
            self.open_note(notes[0].id, skip_guard=True)
            self.list.selection_set(notes[0].id)
        elif self.current is None:
            self._clear_editor()
        self.render_backlinks()

    def _clear_editor(self):
        self.loading = True
        self.title_var.set("")
        self.tags_var.set("")
        self.editor.configure(state="normal")
        self.editor.delete("1.0", "end")
        self.editor.edit_modified(False)
        self.editor.configure(state="disabled")
        self.title_entry.configure(state="disabled")
        self.tags_entry.configure(state="disabled")
        self.save_button.configure(state="disabled")
        self.dirty = False
        self.loading = False
        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("end", "选择一篇笔记，或点击“新建笔记”。")
        self.preview.configure(state="disabled")
        self.save_state.configure(text="尚未选择笔记", fg=MUTED)

    def open_note(self, note_id, skip_guard=False):
        if not skip_guard and not self.guard():
            return False
        try:
            note = self.store.get(note_id)
        except AppError as exc:
            self.error(exc)
            return False
        if self.after_save:
            self.root.after_cancel(self.after_save)
            self.after_save = None
        self.loading = True
        self.current = note
        self.title_entry.configure(state="normal")
        self.tags_entry.configure(state="normal")
        self.editor.configure(state="normal")
        self.title_var.set(note.title)
        self.tags_var.set("，".join(note.tags))
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", note.body)
        self.editor.edit_reset()
        self.editor.edit_modified(False)
        self.dirty = False
        self.loading = False
        self.title_entry.selection_clear()
        if note.deleted:
            self.title_entry.configure(state="readonly")
            self.tags_entry.configure(state="readonly")
            self.editor.configure(state="disabled")
        self.save_button.configure(state="disabled" if note.deleted else "normal")
        self.save_state.configure(
            text=f"{'回收站 · 只读' if note.deleted else '已保存到本机'}  ·  v{note.revision}  ·  {note.id[:8]}",
            fg=MUTED,
        )
        self.render_preview()
        self.render_backlinks()
        return True

    def new_note(self):
        if not self.guard():
            return
        note = self.store.create("未命名笔记")
        self.trash = False
        self.current = None
        self.dirty = False
        self.query_var.set("")
        self.filter_var.set("")
        self.open_note(note.id, True)
        self.refresh(note.id)
        self.title_entry.focus_set()
        self.title_entry.selection_range(0, "end")

    def save(self, silent=False):
        self.after_save = None
        if self.modal_guard:
            return False
        if not self.current or self.current.deleted:
            return True
        try:
            saved = self.store.save(
                self.current.id,
                self.title_var.get(),
                self.editor.get("1.0", "end-1c"),
                self.tags_var.get(),
                self.current.revision,
            )
            self.current = saved
            self.dirty = False
            self.save_state.configure(
                text=f"已保存到本机 · v{saved.revision} · {saved.id[:8]}", fg="#24744a"
            )
            self.status_var.set("保存成功，历史版本同步保留")
            self.refresh(saved.id, False)
            self.render_preview()
            return True
        except (AppError, sqlite3.Error, OSError) as exc:
            self.save_state.configure(text="未保存 · " + str(exc), fg="#a34b12")
            if not silent:
                self.error(exc)
            return False

    def delete_action(self):
        if not self.current or not self.guard():
            return
        note = self.current
        if not messagebox.askyesno(
            "确认操作",
            "恢复这篇笔记？" if note.deleted else "移入回收站？之后仍可恢复。",
            parent=self.root,
        ):
            return
        self.store.set_deleted(note.id, not note.deleted)
        self.current = None
        self.dirty = False
        self.refresh()

    def render_preview(self):
        self.after_preview = None
        body = self.editor.get("1.0", "end-1c")
        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        pos = 0
        for i, link in enumerate(extract_links(body)):
            self.preview.insert("end", body[pos : link.start])
            try:
                target = self.store.get(link.target)
                label = link.alias or target.title
                unavailable = target.deleted
            except ValidationError:
                label = link.alias or "目标不可用"
                unavailable = True
            tag = f"target_{i}"
            self.preview.insert(
                "end", label + ("（目标不可用）" if unavailable else ""), ("link", tag)
            )
            if not unavailable:
                self.preview.tag_bind(
                    tag, "<Button-1>", lambda _e, t=link.target: self.open_note(t)
                )
            pos = link.end
        self.preview.insert("end", body[pos:])
        text = self.preview.get("1.0", "end-1c")
        in_code = False
        for number, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith(("```", "~~~")):
                in_code = not in_code
                self.preview.delete(f"{number}.0", f"{number}.end")
                continue
            tag = (
                "code"
                if in_code
                else (
                    "h1"
                    if line.startswith("# ")
                    else "h2"
                    if line.startswith("## ")
                    else None
                )
            )
            if tag:
                self.preview.tag_add(tag, f"{number}.0", f"{number}.end")
            if not in_code:
                prefix = re.match(r"^#{1,6} +", line)
                if prefix:
                    self.preview.delete(
                        f"{number}.0", f"{number}.{len(prefix.group())}"
                    )
                cursor = f"{number}.0"
                while True:
                    start = self.preview.search("**", cursor, stopindex=f"{number}.end")
                    if not start:
                        break
                    end = self.preview.search(
                        "**", start + " +2c", stopindex=f"{number}.end"
                    )
                    if not end:
                        break
                    self.preview.tag_add("strong", start, end + " +2c")
                    self.preview.delete(end, end + " +2c")
                    self.preview.delete(start, start + " +2c")
                    cursor = start + " +1c"
        self.preview.configure(state="disabled")

    def render_backlinks(self):
        for child in self.backlink_frame.winfo_children():
            child.destroy()
        rows = backlinks(self.store, self.current.id) if self.current else []
        if not rows:
            self._label(
                self.backlink_frame, "暂无其他笔记引用", 9, MUTED, anchor="w"
            ).pack(fill="x", padx=5, pady=5)
        for note, count in rows[:5]:
            ttk.Button(
                self.backlink_frame,
                text=f"{note.title[:18]}  ×{count}",
                command=lambda n=note.id: self.open_note(n),
            ).pack(fill="x", pady=2)

    def insert_link(self):
        if not self.current or self.current.deleted:
            return
        dialog = tk.Toplevel(self.root)
        dialog.title("插入稳定关联")
        dialog.geometry("520x400")
        dialog.transient(self.root)
        self._label(dialog, "选择目标；以后修改标题不会破坏关联。", 11, INK, BG).pack(
            pady=15
        )
        tree = ttk.Treeview(dialog, columns=("title",), show="headings")
        tree.heading("title", text="目标笔记")
        tree.pack(fill="both", expand=True, padx=18)
        for n in self.store.list_notes():
            tree.insert("", "end", iid=n.id, values=(n.title,))

        def insert():
            if not tree.selection():
                return
            self.editor.insert("insert", f"[[note:{tree.selection()[0]}]]")
            self.editor.focus_set()
            dialog.destroy()

        ttk.Button(
            dialog, text="插入关联", command=insert, style="Accent.TButton"
        ).pack(pady=15)

    def show_history(self):
        if not self.current or not self.guard():
            return
        note_id = self.current.id
        dialog = tk.Toplevel(self.root)
        dialog.title("历史版本")
        dialog.geometry("760x600")
        dialog.transient(self.root)
        records = self.store.versions(note_id)
        tree = ttk.Treeview(
            dialog, columns=("version", "action", "time"), show="headings", height=7
        )
        for c, t, w in [
            ("version", "版本", 70),
            ("action", "操作", 210),
            ("time", "记录时间（UTC）", 260),
        ]:
            tree.heading(c, text=t)
            tree.column(c, width=w)
        tree.pack(fill="x", padx=18, pady=15)
        index = {str(v["id"]): v for v in records}
        for v in records:
            tree.insert(
                "",
                "end",
                iid=str(v["id"]),
                values=(
                    f"v{v['revision']}",
                    v["action"],
                    v["created_at"][:19].replace("T", " "),
                ),
            )
        view = tk.Text(
            dialog, wrap="word", font=("Microsoft YaHei UI", 11), bd=0, padx=15, pady=12
        )
        view.pack(fill="both", expand=True, padx=18)

        def selected(_=None):
            if tree.selection():
                row = index[tree.selection()[0]]
                view.configure(state="normal")
                view.delete("1.0", "end")
                view.insert("end", row["title"] + "\n\n" + row["body"])
                view.configure(state="disabled")

        tree.bind("<<TreeviewSelect>>", selected)

        def restore():
            if not tree.selection() or self.current.deleted:
                return
            if not messagebox.askyesno(
                "回退版本", "回退会保存为新版本，现有历史仍保留。继续？", parent=dialog
            ):
                return
            try:
                row = index[tree.selection()[0]]
                new = self.store.restore_version(
                    note_id, row["id"], self.current.revision
                )
                self.open_note(new.id, True)
                self.refresh(new.id)
                dialog.destroy()
            except AppError as exc:
                self.error(exc)

        ttk.Button(
            dialog,
            text="以此版本恢复（保留全部历史）",
            command=restore,
            style="Accent.TButton",
        ).pack(pady=15)
        if records:
            tree.selection_set(str(records[0]["id"]))
            selected()

    def backup_menu(self):
        menu = tk.Menu(self.root, tearoff=False)
        menu.add_command(label="创建完整备份", command=self.backup)
        menu.add_command(label="从备份恢复", command=self.restore)
        menu.tk_popup(self.root.winfo_pointerx(), self.root.winfo_pointery())

    def backup(self):
        if not self.guard():
            return
        filename = filedialog.asksaveasfilename(
            parent=self.root,
            title="创建完整备份",
            defaultextension=".db",
            initialfile="知页备份_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".db",
            filetypes=[("知页备份", "*.db")],
        )
        if not filename:
            return
        try:
            create_backup(self.store, filename)
            self.status_var.set("完整备份已校验并保存：" + filename)
        except (AppError, OSError, sqlite3.Error) as exc:
            self.error(exc)

    def restore(self):
        filename = filedialog.askopenfilename(
            parent=self.root, title="选择知页备份", filetypes=[("知页备份", "*.db")]
        )
        if not filename:
            return
        try:
            info = inspect_backup(filename)
        except AppError as exc:
            self.error(exc)
            return
        if (
            not messagebox.askyesno(
                "完整恢复",
                f"备份包含 {info['notes']} 篇有效笔记、{info['trash']} 篇回收站笔记。\n当前库会先生成保护副本，再由备份完整替换。继续？",
                parent=self.root,
            )
            or not self.guard()
        ):
            return
        try:
            protected = restore_backup(self.store, filename, self.data_dir / "backups")
            self.current = None
            self.dirty = False
            self.trash = False
            self.refresh()
            self.status_var.set("恢复完成；恢复前数据保留在：" + str(protected))
        except (AppError, sqlite3.Error, OSError) as exc:
            self.error(exc)

    def import_files(self):
        if not self.guard():
            return
        files = filedialog.askopenfilenames(
            parent=self.root, filetypes=[("Markdown", "*.md")]
        )
        if not files:
            return
        report = import_markdown(self.store, files)
        good = [r for r in report if r["ok"]]
        bad = [r for r in report if not r["ok"]]
        self.status_var.set(f"导入完成：成功 {len(good)}，失败 {len(bad)}")
        if good:
            self.trash = False
            self.dirty = False
            self.open_note(good[-1]["id"], True)
            self.refresh(good[-1]["id"])
        if bad:
            messagebox.showwarning(
                "部分文件未导入",
                "\n".join(r["file"] + "：" + r["error"] for r in bad[:8]),
                parent=self.root,
            )

    def export(self, kind):
        if not self.guard():
            return
        folder = filedialog.askdirectory(parent=self.root, title="选择空目录用于导出")
        if not folder:
            return
        try:
            rows = export_notes(self.store, folder, kind)
            self.status_var.set(f"已导出 {len(rows)} 篇笔记到 {folder}")
        except (AppError, OSError) as exc:
            self.error(exc)

    def save_buffer_as_file(self):
        if not self.current:
            return
        path = filedialog.asksaveasfilename(
            parent=self.root, defaultextension=".md", filetypes=[("Markdown", "*.md")]
        )
        if path:
            try:
                Path(path).write_text(
                    self.editor.get("1.0", "end-1c"), encoding="utf-8"
                )
                self.status_var.set("编辑器当前内容已另存，原笔记未被覆盖")
            except OSError as exc:
                self.error(exc)

    def more_menu(self):
        menu = tk.Menu(self.root, tearoff=False)
        menu.add_command(
            label="导出全部 Markdown", command=lambda: self.export("markdown")
        )
        menu.add_command(
            label="当前编辑内容另存为文件", command=self.save_buffer_as_file
        )
        menu.add_separator()
        menu.add_command(label="创建完整备份", command=self.backup)
        menu.add_command(label="从备份恢复", command=self.restore)
        if self.current and self.current.deleted:
            menu.add_command(label="永久删除当前回收站笔记", command=self.purge)
        menu.tk_popup(self.root.winfo_pointerx(), self.root.winfo_pointery())

    def purge(self):
        if (
            self.current
            and self.current.deleted
            and messagebox.askyesno(
                "永久删除",
                "将删除当前笔记及其历史。旧备份仍可能包含它。确认永久删除？",
                parent=self.root,
            )
        ):
            self.store.purge(self.current.id)
            self.current = None
            self.dirty = False
            self.refresh()

    def close(self):
        if self.guard():
            self.store.close()
            self.root.destroy()

    def smoke(self, report_path):
        """Exercise actual UI widgets without interacting with personal data."""
        report = {"mode": "actual Tk widget smoke test", "passed": False}
        try:
            self.new_note()
            self.title_var.set("界面验收记录")
            self.editor.insert("end", "# 界面验证\n\n真实控件输入与保存。")
            self.tags_var.set("验收")
            if not self.save():
                raise RuntimeError("UI save failed")
            note_id = self.current.id
            if self.store.get(note_id).body != "# 界面验证\n\n真实控件输入与保存。":
                raise RuntimeError("saved content mismatch")
            choices = [n for n in self.store.list_notes() if "本周学习复盘" in n.title]
            if choices:
                self.open_note(choices[0].id, True)
                self.refresh(choices[0].id)
            self.root.update_idletasks()
            if self.smoke_error:
                raise RuntimeError(self.smoke_error)
            report.update(
                passed=True,
                ui_saved_note_id=note_id,
                preview_nonempty=bool(self.preview.get("1.0", "end").strip()),
                visible=bool(self.root.winfo_viewable()),
                stats=self.store.stats(),
            )
        except Exception as exc:
            report["error"] = str(exc)
        Path(report_path).parent.mkdir(parents=True, exist_ok=True)
        Path(report_path).write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        self.root.after(3500, lambda: (self.store.close(), self.root.destroy()))
