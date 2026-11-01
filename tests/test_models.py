import unittest

from zhiyeteam.models import Note


class ModelTests(unittest.TestCase):
    def test_note_snapshot_is_immutable(self):
        note = Note("id", "title", "body", (), "a", "b", 1)
        with self.assertRaises(AttributeError):
            note.title = "changed"
