from unittest.mock import Mock, patch

from support import StoreFixture
from zhiyeteam.models import ValidationError
from zhiyeteam.ui import NotebookApp


class PreferenceTests(StoreFixture):
    def app(self):
        app = object.__new__(NotebookApp)
        app.store = self.store
        app.editor = Mock()
        app.font_size_var = Mock()
        app.editor_font_size = 12
        return app

    def test_font_preference_persists_without_editing_notes(self):
        note = self.store.create("正文不应变化", "动态规划正文", ["课程"])
        before = self.store.get(note.id)
        app = self.app()
        app.set_editor_font_size(18)
        self.assertEqual(self.app()._read_font_size(), 18)
        self.assertEqual(self.store.get(note.id), before)
        app.editor.configure.assert_called_once_with(font=("Consolas", 18))

    def test_invalid_font_values_do_not_overwrite_existing_preference(self):
        app = self.app()
        app.set_editor_font_size(16)
        for size in (11, 25, True, "18", 18.5):
            with self.subTest(size=size), self.assertRaises(ValidationError):
                app.set_editor_font_size(size)
        self.assertEqual(self.store.settings("editor_font_size"), 16)
        self.store.set_setting("editor_font_size", "bad value")
        self.assertEqual(app._read_font_size(), 12)

    def test_failed_preference_write_preserves_displayed_font(self):
        app = self.app()
        with patch.object(
            self.store, "set_setting", side_effect=ValidationError("只读")
        ):
            with self.assertRaises(ValidationError):
                app.set_editor_font_size(18)
        self.assertEqual(app.editor_font_size, 12)
        app.editor.configure.assert_not_called()
