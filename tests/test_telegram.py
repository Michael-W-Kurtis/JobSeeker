from __future__ import annotations

import json
import unittest
from pathlib import Path

from jobseeker.telegram import format_digest, html_escape


class TelegramFormatTests(unittest.TestCase):
    def test_escapes_html(self):
        self.assertEqual(html_escape("A & B <C>"), "A &amp; B &lt;C&gt;")

    def test_empty_digest(self):
        self.assertEqual(format_digest([], where="New York"), [])

    def test_includes_adzuna_link_and_count(self):
        jobs = [
            {
                "title": "DevOps <lead>",
                "company": "Acme & Co",
                "location": "New York",
                "url": "https://www.adzuna.com/details/1",
                "created": "2026-11-01T12:00:00Z",
            }
        ]
        chunks = format_digest(jobs, where="New York")
        self.assertEqual(len(chunks), 1)
        self.assertIn("1 new Adzuna match · New York", chunks[0])
        self.assertIn("Adzuna listing", chunks[0])
        self.assertIn("DevOps &lt;lead&gt;", chunks[0])
        self.assertIn("Acme &amp; Co", chunks[0])

    def test_splits_when_over_limit(self):
        jobs = [
            {
                "title": f"DevOps {i} " + ("x" * 200),
                "company": "Acme",
                "location": "New York",
                "url": f"https://www.adzuna.com/details/{i}",
                "created": "2026-11-01T12:00:00Z",
            }
            for i in range(40)
        ]
        chunks = format_digest(jobs, where="New York")
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 3500)


if __name__ == "__main__":
    unittest.main()
