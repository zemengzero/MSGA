from support import StoreFixture

from zhiyeteam.models import ValidationError
from zhiyeteam.transfer import export_notes, import_markdown, safe_markdown_html


class TransferTests(StoreFixture):
    def test_utf8_import_conflict_and_partial_failure(self):
        a = self.path.parent / "a.md"
        b = self.path.parent / "b.md"
        c = self.path.parent / "bad.md"
        a.write_bytes(b"\xef\xbb\xbf" + "# 课程\n正文".encode())
        b.write_text("# 课程\n第二篇", encoding="utf-8")
        c.write_bytes(b"\xff\xfe\x00")
        result = import_markdown(self.store, [a, b, c])
        self.assertEqual([r["ok"] for r in result], [True, True, False])
        self.assertEqual(self.store.stats()["active"], 2)
        self.assertNotEqual(result[0]["title"], result[1]["title"])

    def test_html_strips_active_content(self):
        text = '<script>alert(1)</script><img src="https://bad.test/track" onerror="evil()"><a href="javascript:evil()">bad</a>'
        result = safe_markdown_html(text)
        self.assertNotIn("<script", result)
        self.assertNotIn("onerror", result)
        self.assertNotIn("javascript:", result)
        self.assertNotIn("https://bad.test", result)

    def test_export_internal_links_are_local(self):
        target = self.store.create("目标", "内容")
        source = self.store.create("来源", f"[[note:{target.id}]]")
        directory = self.path.parent / "export"
        rows = export_notes(self.store, directory, "html")
        mapping = {r["id"]: r["file"] for r in rows}
        output = (directory / mapping[source.id]).read_text(encoding="utf-8")
        self.assertIn(mapping[target.id], output)
        self.assertTrue((directory / "index.html").exists())

    def test_nonempty_export_refused(self):
        folder = self.path.parent / "export"
        folder.mkdir()
        (folder / "mine.txt").write_text("keep")
        with self.assertRaises(ValidationError):
            export_notes(self.store, folder)
        self.assertEqual((folder / "mine.txt").read_text(), "keep")

    def test_malformed_uri_is_inert(self):
        result = safe_markdown_html('<a href="http://[">broken</a>')
        self.assertIn("broken", result)
        self.assertNotIn("href=", result)
