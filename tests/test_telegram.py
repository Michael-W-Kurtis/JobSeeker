from __future__ import annotations

import unittest

from jobseeker.telegram import abbreviate_location, format_digest, format_job_line, html_escape


class TelegramFormatTests(unittest.TestCase):
    def test_escapes_html(self):
        self.assertEqual(html_escape("A & B <C>"), "A &amp; B &lt;C&gt;")

    def test_empty_digest(self):
        self.assertEqual(format_digest([], where="New York"), [])

    def test_title_is_the_listing_hyperlink(self):
        jobs = [
            {
                "title": "DevOps <lead>",
                "company": "Acme & Co",
                "location": "New York City, New York",
                "area": ["US", "New York", "New York City"],
                "url": "https://www.adzuna.com/details/1",
                "created": "2026-11-01T12:00:00Z",
            }
        ]
        chunks = format_digest(jobs, where="New York")
        self.assertEqual(len(chunks), 1)
        body = chunks[0]
        self.assertIn("Manhattan · Queens · Bronx · Remote", body)
        self.assertNotIn("Nassau", body)
        self.assertNotIn("Brooklyn", body)
        self.assertIn(
            '<a href="https://www.adzuna.com/details/1"><b>DevOps &lt;lead&gt;</b></a>',
            body,
        )
        self.assertNotIn("Adzuna listing", body)
        self.assertNotIn("https://www.adzuna.com/details/1</a>", body.replace(
            '<a href="https://www.adzuna.com/details/1"><b>DevOps &lt;lead&gt;</b></a>',
            "",
        ))
        self.assertIn("Acme &amp; Co", body)
        self.assertIn("<blockquote>", body)
        self.assertIn("</blockquote>", body)

    def test_abbreviates_place_names(self):
        self.assertEqual(
            abbreviate_location(
                {
                    "location": "New York City, New York",
                    "area": ["US", "New York", "New York City"],
                }
            ),
            "NYC",
        )
        self.assertEqual(
            abbreviate_location(
                {
                    "location": "Grand Central, Manhattan",
                    "area": ["US", "New York", "New York City", "Manhattan", "Grand Central"],
                }
            ),
            "Manhattan",
        )
        self.assertEqual(
            abbreviate_location(
                {
                    "location": "Astoria, Queens",
                    "area": ["US", "New York", "New York City", "Queens", "Astoria"],
                }
            ),
            "Queens",
        )
        self.assertEqual(
            abbreviate_location(
                {
                    "location": "Garden City, New York",
                    "area": ["US", "New York", "Nassau County", "Garden City"],
                }
            ),
            "Nassau",
        )
        self.assertEqual(
            abbreviate_location(
                {
                    "location": "Hub, Bronx",
                    "area": ["US", "New York", "New York City", "Bronx", "Hub"],
                }
            ),
            "Bronx",
        )
        self.assertEqual(
            abbreviate_location(
                {
                    "location": "Remote, United States",
                    "area": ["US"],
                }
            ),
            "Remote",
        )
        line = format_job_line(
            {
                "title": "SRE",
                "company": "Labs",
                "location": "New York City, New York",
                "area": ["US", "New York", "New York City"],
                "url": "https://www.adzuna.com/details/2",
                "created": "2026-11-01T12:00:00Z",
            }
        )
        self.assertIn("NYC", line)
        self.assertNotIn("New York City", line)
        paid = format_job_line(
            {
                "title": "SRE",
                "company": "Labs",
                "location": "New York City, New York",
                "area": ["US", "New York", "New York City"],
                "url": "https://www.adzuna.com/details/2",
                "created": "2026-11-01T12:00:00Z",
                "salary_min": 80000,
                "salary_max": 90000,
            }
        )
        self.assertIn("$80k–$90k", paid)

    def test_splits_when_over_limit(self):
        jobs = [
            {
                "title": f"DevOps {i} " + ("x" * 200),
                "company": "Acme",
                "location": "New York City, New York",
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
