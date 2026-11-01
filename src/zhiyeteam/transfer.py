import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

import markdown

from .links import extract_links
from .models import MAX_BODY_BYTES, ValidationError


class SafeHTML(HTMLParser):
    ALLOWED = {
        "p",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "ul",
        "ol",
        "li",
        "strong",
        "em",
        "blockquote",
        "pre",
        "code",
        "hr",
        "br",
        "table",
        "thead",
        "tbody",
        "tr",
        "td",
        "th",
        "a",
        "del",
    }

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "img":
            self.parts.append("<span>[图片未导出]</span>")
            return
        if tag not in self.ALLOWED:
            return
        clean = []
        if tag == "a":
            values = dict(attrs)
            href = values.get("href", "")
            try:
                scheme = urlsplit(href).scheme.lower()
            except ValueError:
                scheme = ""
                href = ""
            if (
                scheme in ("https", "http")
                or re.fullmatch(r"[\w\-\u4e00-\u9fff]+\.html", href)
                or href.startswith("#")
            ):
                clean.append('href="' + html.escape(href, quote=True) + '"')
            clean.append('rel="noreferrer noopener"')
        self.parts.append("<" + tag + (" " + " ".join(clean) if clean else "") + ">")

    def handle_endtag(self, tag):
        if tag in self.ALLOWED and tag not in ("hr", "br"):
            self.parts.append("</" + tag + ">")

    def handle_data(self, data):
        self.parts.append(html.escape(data))


def safe_markdown_html(body):
    rendered = markdown.markdown(body, extensions=["fenced_code", "tables"])
    parser = SafeHTML()
    parser.feed(rendered)
    parser.close()
    return "".join(parser.parts)


def import_markdown(store, paths):
    report = []
    titles = {n.title for n in store.list_notes()}
    for raw in paths:
        path = Path(raw)
        try:
            if path.suffix.lower() != ".md":
                raise ValidationError("只导入.md文件")
            if path.stat().st_size > MAX_BODY_BYTES:
                raise ValidationError("正文超过1MiB")
            body = path.read_bytes().decode("utf-8-sig", errors="strict")
            first = next(
                (
                    line[2:].strip()
                    for line in body.splitlines()
                    if line.startswith("# ")
                ),
                path.stem,
            )
            title = first[:70] or "导入笔记"
            base = title
            n = 1
            while title in titles:
                title = f"{base}（导入{n}）"
                n += 1
            note = store.create(title, body, ["导入"])
            titles.add(title)
            report.append(
                {"file": path.name, "ok": True, "id": note.id, "title": title}
            )
        except (OSError, UnicodeError, ValidationError) as exc:
            report.append({"file": path.name, "ok": False, "error": str(exc)})
    return report


def _filename(note, ext):
    title = re.sub(r"[^\w\u4e00-\u9fff-]", "_", note.title)[:28] or "note"
    return title + "_" + note.id + ext


def _replace_links(body, notes, names):
    for link in reversed(extract_links(body)):
        target = notes.get(link.target)
        label = link.alias or (target.title if target else "目标不可用")
        label = (
            html.escape(label)
            .replace("\\", "\\\\")
            .replace("[", "\\[")
            .replace("]", "\\]")
        )
        text = f"[{label}]({names[target.id]})" if target else label + "（目标未导出）"
        body = body[: link.start] + text + body[link.end :]
    return body


def export_notes(store, directory, kind="markdown"):
    directory = Path(directory).resolve()
    if directory.exists() and any(directory.iterdir()):
        raise ValidationError("请选择一个空的导出目录，避免覆盖已有文件")
    if kind not in ("markdown", "html"):
        raise ValidationError("不支持的导出格式")
    directory.mkdir(parents=True, exist_ok=True)
    notes = store.list_notes()
    by_id = {n.id: n for n in notes}
    names = {n.id: _filename(n, ".html" if kind == "html" else ".md") for n in notes}
    report = []
    for note in notes:
        body = _replace_links(note.body, by_id, names)
        if kind == "html":
            content = (
                '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>'
                + html.escape(note.title)
                + "</title><style>body{font:17px/1.75 system-ui,sans-serif;max-width:900px;margin:48px auto;padding:0 24px;color:#172b45}pre{padding:18px;background:#f1f5fa;overflow:auto}table{border-collapse:collapse}td,th{border:1px solid #ccd6e3;padding:8px}a{color:#245bdd}</style><h1>"
                + html.escape(note.title)
                + "</h1>"
                + safe_markdown_html(body)
                + "</html>"
            )
        else:
            content = body
        path = directory / names[note.id]
        with path.open("x", encoding="utf-8", newline="") as stream:
            stream.write(content)
        report.append(
            {"id": note.id, "title": note.title, "tags": note.tags, "file": path.name}
        )
    with (directory / "notes_index.json").open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    if kind == "html":
        index = (
            '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>知页导出索引</title><h1>知页 · 导出索引</h1><ul>'
            + "".join(
                '<li><a href="'
                + html.escape(r["file"], quote=True)
                + '">'
                + html.escape(r["title"])
                + "</a></li>"
                for r in report
            )
            + "</ul></html>"
        )
        with (directory / "index.html").open("x", encoding="utf-8") as stream:
            stream.write(index)
    return report
