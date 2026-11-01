import unittest
from unittest.mock import Mock, patch

from zhiyeteam.ui import NotebookApp


class GuardTests(unittest.TestCase):
    def test_cancel_guard_suppresses_nested_autosave(self):
        app = object.__new__(NotebookApp)
        app.root = Mock()
        app.dirty = True
        app.modal_guard = False
        app.after_save = "timer"

        def answer(*_a, **_kw):
            self.assertTrue(app.modal_guard)
            self.assertFalse(app.save(silent=True))
            return None

        with patch("zhiyeteam.ui.messagebox.askyesnocancel", side_effect=answer):
            self.assertFalse(app.guard())
        self.assertTrue(app.dirty)
        self.assertFalse(app.modal_guard)
        app.root.after_cancel.assert_called_once_with("timer")
