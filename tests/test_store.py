from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jobseeker.store import SeenStore, job_key


class StoreTests(unittest.TestCase):
    def test_unseen_then_alerted(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SeenStore(Path(tmp) / "seen.sqlite")
            a = {"id": "1", "title": "DevOps", "company": "A", "location": "NYC", "url": "https://x/1"}
            b = {"id": "2", "title": "SRE", "company": "B", "location": "NYC", "url": "https://x/2"}
            self.assertEqual([job_key(j) for j in store.unseen([a, b])], ["adzuna:1", "adzuna:2"])
            store.mark_alerted([a])
            unseen = store.unseen([a, b])
            self.assertEqual([job_key(j) for j in unseen], ["adzuna:2"])
            store.close()

    def test_fallback_tuple_key(self):
        job = {"id": "", "url": "", "company": "Acme", "title": "SRE", "location": "NYC"}
        self.assertEqual(job_key(job), "tuple:acme|sre|nyc")


if __name__ == "__main__":
    unittest.main()
