import json
import re
import urllib.error
import urllib.request
from pathlib import Path
from unittest import TestCase
from tempfile import TemporaryDirectory

from zhiyeteam.galaxy_api import GalaxyAPI
from zhiyeteam.galaxy_server import serve


class ServerTests(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name)
        assets = self.root / "web"
        assets.mkdir()
        (assets / "index.html").write_text(
            "<html><head></head><body>app</body></html>", encoding="utf-8"
        )
        self.server, self.url = serve(GalaxyAPI(self.root / "data"), assets)
        text = urllib.request.urlopen(self.url).read().decode()
        self.token = re.search(r'window.ZHIYE_TOKEN="([^"]+)"', text)[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.temp.cleanup()

    def test_authenticated_same_origin_request_returns_real_data(self):
        req = urllib.request.Request(
            self.url + "/api/snapshot",
            data=b"{}",
            headers={"X-Zhiye-Token": self.token, "Origin": self.url},
        )
        result = json.load(urllib.request.urlopen(req))
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["stats"]["active"], 0)

    def test_wrong_token_and_cross_origin_are_blocked(self):
        for token, origin in (("wrong", self.url), (self.token, "https://example.com")):
            req = urllib.request.Request(
                self.url + "/api/create",
                data=b'{"title":"blocked"}',
                headers={"X-Zhiye-Token": token, "Origin": origin},
            )
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(req)
            self.assertEqual(error.exception.code, 403)

    def test_database_and_traversal_cannot_be_served(self):
        for path in ("/notes.db", "/../data/notes.db", "/%2e%2e/data/notes.db"):
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(self.url + path)
            self.assertEqual(error.exception.code, 404)
