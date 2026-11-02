import json
from types import SimpleNamespace
from unittest.mock import patch

from support import StoreFixture
from zhiyeteam.galaxy_api import GalaxyAPI


class GalaxyHighlightTests(StoreFixture):
    def snapshot(self, query=""):
        result = GalaxyAPI(self.path.parent).invoke("snapshot", {"query": query})
        self.assertTrue(result["ok"], result)
        return json.loads(json.dumps(result))["data"]

    def test_real_highlight_offsets_survive_api_json_mapping(self):
        note = self.store.create("Unicode", "## 😀 动态规划 Ai ai")
        result = self.snapshot("动态规划 AI")["notes"][0]
        self.assertEqual(result["id"], note.id)
        self.assertEqual(result["excerpt"], "## 😀 动态规划 Ai ai")
        self.assertEqual(result["snippet_highlights"], [[5, 9], [10, 12], [13, 15]])
        self.assertEqual(self.snapshot()["notes"][0]["snippet_highlights"], [])

    def test_old_hit_object_without_ranges_remains_supported(self):
        note = self.store.create("A", "body")
        hit = SimpleNamespace(note=note, snippet="body", matched_fields={"body"})
        with patch("zhiyeteam.search.search_hits", return_value=[hit]):
            self.assertEqual(self.snapshot()["notes"][0]["snippet_highlights"], [])

    def test_dictionary_hit_ranges_are_serialized_as_lists(self):
        note = self.store.create("A", "AI")
        hit = {"note": note, "snippet": "AI", "matched_fields": ["body"],
               "snippet_highlights": ((0, 2),)}
        with patch("zhiyeteam.search.search_hits", return_value=[hit]):
            self.assertEqual(self.snapshot()["notes"][0]["snippet_highlights"], [[0, 2]])
