from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from zhiyeteam.models import ValidationError
from zhiyeteam.ui import NotebookApp


class LayoutTests(TestCase):
    def app(self):
        app = object.__new__(NotebookApp)
        for name in (
            "root",
            "paned",
            "previewbox",
            "narrow_hint",
            "editor",
            "tags_entry",
        ):
            setattr(app, name, Mock())
        app.preview_visible = True
        return app

    def test_narrow_resize_hides_once_and_boundary_restores(self):
        app = self.app()
        for width in (980, 1100, 1199):
            app._window_resized(SimpleNamespace(widget=app.root, width=width))
        app.paned.forget.assert_called_once_with(app.previewbox)
        self.assertFalse(app.preview_visible)
        app._window_resized(SimpleNamespace(widget=app.root, width=1200))
        self.assertTrue(app.preview_visible)
        app.paned.add.assert_called_once_with(app.previewbox, minsize=300, width=385)

    def test_child_resize_does_not_change_layout(self):
        app = self.app()
        app._window_resized(SimpleNamespace(widget=object(), width=100))
        app.paned.forget.assert_not_called()
        app.paned.add.assert_not_called()

    def test_control_tab_moves_focus_and_stops_tab_insertion(self):
        app = self.app()
        self.assertEqual(app._focus_tags(), "break")
        app.tags_entry.focus_set.assert_called_once()
        self.assertEqual(app._focus_editor(), "break")
        app.editor.focus_set.assert_called_once()

    def test_font_selection_failure_reverts_control_and_reports_error(self):
        app = self.app()
        app.font_size_var = Mock()
        app.font_size_var.get.return_value = "18"
        app.editor_font_size = 12
        app.set_editor_font_size = Mock(side_effect=ValidationError("磁盘只读"))
        with patch("zhiyeteam.ui.messagebox.showerror") as dialog:
            app._font_selected()
        app.font_size_var.set.assert_called_once_with("12")
        dialog.assert_called_once()
        self.assertEqual(app.editor_font_size, 12)
