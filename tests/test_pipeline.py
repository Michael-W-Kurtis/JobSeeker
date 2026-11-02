from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from jobseeker.adzuna import normalize
from jobseeker.config import Config
from jobseeker.pipeline import run
from jobseeker.store import SeenStore

FIXTURE = Path(__file__).parent / "fixtures" / "adzuna_search.json"


class FakeResponse:
    def __init__(self, body: bytes, status: int = 200) -> None:
        self._body = body
        self.status = status

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *args) -> bool:
        return False


class RecordingOpener:
    def __init__(self, body: bytes) -> None:
        self.body = body
        self.urls: list[str] = []
        self.payloads: list[bytes] = []

    def open(self, req, timeout=None) -> FakeResponse:
        self.urls.append(getattr(req, "full_url", str(req)))
        self.payloads.append(getattr(req, "data", None) or b"")
        return FakeResponse(self.body)


def _cfg(state_dir: Path) -> Config:
    return Config(
        adzuna_app_id="id",
        adzuna_app_key="key",
        telegram_bot_token="token",
        telegram_chat_id="123",
        where="New York",
        distance_km=40,
        max_days_old=7,
        country="us",
        state_dir=state_dir,
        repo_root=state_dir,
    )


class PipelineTests(unittest.TestCase):
    def test_dry_run_does_not_mark_or_send(self):
        fixture = FIXTURE.read_bytes()
        with TemporaryDirectory() as tmp:
            state = Path(tmp)
            adz = RecordingOpener(fixture)
            tg = RecordingOpener(b'{"ok": true, "result": {}}')
            result = run(_cfg(state), dry_run=True, opener=adz, telegram_opener=tg)
            self.assertEqual(result.fetched, 4)
            self.assertEqual(result.relevant, 2)
            self.assertEqual(result.new, 2)
            self.assertEqual(result.sent_chunks, 0)
            self.assertEqual(tg.urls, [])
            store = SeenStore(state / "seen.sqlite")
            jobs = [normalize(raw) for raw in json.loads(fixture)["results"]]
            self.assertEqual(len(store.unseen(jobs)), 4)
            store.close()
            self.assertTrue(result.raw_path and result.raw_path.is_file())

    def test_second_run_is_silent(self):
        fixture = FIXTURE.read_bytes()
        with TemporaryDirectory() as tmp:
            state = Path(tmp)
            cfg = _cfg(state)
            adz = RecordingOpener(fixture)
            tg = RecordingOpener(b'{"ok": true, "result": {}}')
            first = run(cfg, opener=adz, telegram_opener=tg)
            self.assertEqual(first.new, 2)
            self.assertEqual(first.sent_chunks, 1)
            self.assertEqual(len(tg.urls), 1)

            adz2 = RecordingOpener(fixture)
            tg2 = RecordingOpener(b'{"ok": true, "result": {}}')
            second = run(cfg, opener=adz2, telegram_opener=tg2)
            self.assertEqual(second.new, 0)
            self.assertEqual(second.sent_chunks, 0)
            self.assertEqual(tg2.urls, [])

    def test_failed_telegram_does_not_mark_seen(self):
        fixture = FIXTURE.read_bytes()
        with TemporaryDirectory() as tmp:
            state = Path(tmp)
            adz = RecordingOpener(fixture)

            class Boom:
                def open(self, req, timeout=None):
                    raise RuntimeError("nope")

            with self.assertRaises(Exception):
                run(_cfg(state), opener=adz, telegram_opener=Boom())
            store = SeenStore(state / "seen.sqlite")
            jobs = [normalize(raw) for raw in json.loads(fixture)["results"]]
            self.assertEqual(len(store.unseen(jobs)), 4)
            store.close()


if __name__ == "__main__":
    unittest.main()
