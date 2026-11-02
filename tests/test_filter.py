from __future__ import annotations

import json
import unittest
from pathlib import Path

from jobseeker.adzuna import normalize
from jobseeker.filter import is_junior_title, is_relevant, relevant_jobs

FIXTURE = Path(__file__).parent / "fixtures" / "adzuna_search.json"


def _jobs():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return [normalize(raw) for raw in payload["results"]]


class FilterTests(unittest.TestCase):
    def test_keeps_senior_devops_nyc(self):
        jobs = {job["id"]: job for job in _jobs()}
        self.assertTrue(is_relevant(jobs["1001"]))

    def test_drops_junior_even_if_role_matches(self):
        jobs = {job["id"]: job for job in _jobs()}
        self.assertTrue(is_junior_title(jobs["1002"]["title"]))
        self.assertFalse(is_relevant(jobs["1002"]))

    def test_drops_unrelated_role(self):
        jobs = {job["id"]: job for job in _jobs()}
        self.assertFalse(is_relevant(jobs["1003"]))

    def test_keeps_remote_sre(self):
        jobs = {job["id"]: job for job in _jobs()}
        self.assertTrue(is_relevant(jobs["1004"]))

    def test_relevant_set(self):
        ids = {job["id"] for job in relevant_jobs(_jobs())}
        self.assertEqual(ids, {"1001", "1004"})

    def test_senior_help_desk_not_junior(self):
        self.assertFalse(is_junior_title("Senior Help Desk Analyst"))
        self.assertTrue(
            is_relevant(
                {
                    "title": "Senior Help Desk Analyst",
                    "description": "Tickets and on-site support",
                    "location": "Manhattan, New York",
                    "company": "Bank",
                    "area": ["US", "New York"],
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
