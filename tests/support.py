import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from zhiyeteam.store import NoteStore


class StoreFixture(unittest.TestCase):
    def setUp(self):
        root = Path.cwd() / "runtime" / "tests"
        root.mkdir(parents=True, exist_ok=True)
        self.temp = TemporaryDirectory(dir=root)
        self.path = Path(self.temp.name) / "notes.db"
        self.store = NoteStore(self.path)

    def tearDown(self):
        self.store.close()
        assert (
            Path(self.temp.name)
            .resolve()
            .is_relative_to((Path.cwd() / "runtime" / "tests").resolve())
        )
        self.temp.cleanup()
