from __future__ import annotations

import json
import unittest
from pathlib import Path

from jobseeker.adzuna import normalize
from jobseeker.filter import (
    exceeds_max_experience,
    is_junior_title,
    is_leadership_title,
    is_relevant,
    matches_location,
    relevant_jobs,
)

FIXTURE = Path(__file__).parent / "fixtures" / "adzuna_search.json"


def _jobs():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return [normalize(raw) for raw in payload["results"]]


def _job(**kwargs):
    base = {
        "title": "Senior DevOps Engineer",
        "description": "Kubernetes and Terraform",
        "location": "",
        "company": "Acme",
        "area": [],
        "salary_min": 85000,
        "salary_max": 95000,
    }
    base.update(kwargs)
    return base


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
        self.assertTrue(matches_location(jobs["1004"]))
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
                    "area": ["US", "New York", "New York City", "Manhattan"],
                    "salary_min": 85000,
                    "salary_max": 95000,
                }
            )
        )

    def test_keeps_manhattan_queens_bronx(self):
        self.assertTrue(
            matches_location(
                _job(
                    location="Grand Central, Manhattan",
                    area=["US", "New York", "New York City", "Manhattan", "Grand Central"],
                )
            )
        )
        self.assertTrue(
            matches_location(
                _job(
                    location="Astoria, Queens",
                    area=["US", "New York", "New York City", "Queens", "Astoria"],
                )
            )
        )
        self.assertTrue(
            matches_location(
                _job(
                    location="Hub, Bronx",
                    area=["US", "New York", "New York City", "Bronx", "Hub"],
                )
            )
        )
        self.assertFalse(
            matches_location(
                _job(
                    location="Garden City, New York",
                    area=["US", "New York", "Nassau County", "Garden City"],
                )
            )
        )

    def test_drops_brooklyn_generic_nyc_nassau_only(self):
        self.assertFalse(
            matches_location(
                _job(
                    location="Downtown Brooklyn",
                    area=["US", "New York", "New York City", "Brooklyn"],
                )
            )
        )
        self.assertFalse(
            matches_location(
                _job(
                    location="New York City, New York",
                    area=["US", "New York", "New York City"],
                )
            )
        )
        self.assertFalse(
            matches_location(
                _job(
                    location="New York, New York",
                    area=["US", "New York", "New York"],
                )
            )
        )
        self.assertTrue(
            matches_location(
                _job(
                    title="SRE",
                    description="Fully remote, United States",
                    location="Austin, Texas",
                    area=["US", "Texas", "Austin"],
                )
            )
        )

    def test_keeps_if_any_allowlisted_location_even_with_nj_or_brooklyn(self):
        self.assertTrue(
            matches_location(
                _job(
                    title="DevOps Engineer - Iselin, NJ & Manhattan, NY",
                    location="Iselin, New Jersey",
                    area=["US", "New Jersey", "Middlesex County", "Iselin"],
                )
            )
        )
        self.assertTrue(
            matches_location(
                _job(
                    location="Jersey City, New Jersey / Manhattan, NY",
                    area=["US", "New Jersey", "Hudson County", "Jersey City"],
                )
            )
        )
        self.assertTrue(
            matches_location(
                _job(
                    location="Downtown Brooklyn",
                    area=["US", "New York", "New York City", "Brooklyn", "Manhattan"],
                )
            )
        )

    def test_drops_new_jersey_only(self):
        self.assertFalse(
            matches_location(
                _job(
                    location="Jersey City, Hudson County",
                    area=["US", "New Jersey", "Hudson County", "Jersey City"],
                )
            )
        )
        self.assertFalse(
            matches_location(
                _job(
                    location="Summit Avenue, Hudson County",
                    area=["US", "New Jersey", "Hudson County", "Summit Avenue"],
                )
            )
        )
        self.assertTrue(
            matches_location(
                _job(
                    title="SRE (Remote, NJ)",
                    description="This is a fully remote role.",
                    location="Jersey City, New Jersey",
                    area=["US", "New Jersey", "Hudson County", "Jersey City"],
                )
            )
        )

    def test_drops_westchester_suffolk_upstate(self):
        self.assertFalse(
            matches_location(
                _job(
                    location="White Plains, Westchester County",
                    area=["US", "New York", "Westchester County", "White Plains"],
                )
            )
        )
        self.assertFalse(
            matches_location(
                _job(
                    location="Melville, Suffolk County",
                    area=["US", "New York", "Suffolk County", "Melville"],
                )
            )
        )
        self.assertFalse(
            matches_location(
                _job(
                    location="Albany, New York",
                    area=["US", "New York", "Albany"],
                )
            )
        )

    def test_keeps_bronx_on_site_and_hybrid(self):
        job = _job(
            title="Grant-Desktop Support",
            description=(
                "Operate all IT related job functions by travelling to the "
                "assigned office locations throughout New York City within "
                "the primary site in Brooklyn. Responsible for local and "
                "remote end user support for other Programs & expansion centers."
            ),
            location="Bronx, New York City",
            area=["US", "New York", "New York City", "Bronx"],
        )
        self.assertTrue(matches_location(job))
        self.assertTrue(is_relevant(job))
        self.assertTrue(
            matches_location(
                _job(
                    title="SRE",
                    description="This is a fully remote role in the United States.",
                    location="Bronx, New York City",
                    area=["US", "New York", "New York City", "Bronx"],
                )
            )
        )

    def test_drops_when_required_years_exceed_two(self):
        self.assertTrue(
            exceeds_max_experience(
                _job(description="5+ years of experience with Kubernetes")
            )
        )
        self.assertTrue(
            exceeds_max_experience(
                _job(description="3-5 years of experience in DevOps")
            )
        )
        self.assertTrue(
            exceeds_max_experience(
                _job(description="At least 8 years of experience in software")
            )
        )
        self.assertTrue(
            exceeds_max_experience(
                _job(description="Work Experience 10-15 Years")
            )
        )
        self.assertTrue(
            exceeds_max_experience(
                _job(description="Work Experience: 7+ Years")
            )
        )
        self.assertTrue(
            exceeds_max_experience(
                _job(description="10+ years of experience building platforms")
            )
        )
        self.assertTrue(
            exceeds_max_experience(
                _job(description="Requires 10+ Years Experience")
            )
        )
        self.assertFalse(
            is_relevant(
                _job(
                    title="DevOps Engineer",
                    description="5+ years of experience with Terraform",
                    location="Grand Central, Manhattan",
                    area=["US", "New York", "New York City", "Manhattan", "Grand Central"],
                )
            )
        )

    def test_keeps_one_to_two_years_and_unspecified(self):
        self.assertFalse(
            exceeds_max_experience(
                _job(description="1-2 years of experience with Linux")
            )
        )
        self.assertFalse(
            exceeds_max_experience(
                _job(description="2 years of experience in help desk")
            )
        )
        self.assertFalse(
            exceeds_max_experience(
                _job(description="Kubernetes and Terraform")
            )
        )
        self.assertFalse(
            exceeds_max_experience(
                _job(description="Windows 10/11 troubleshooting and Administration skills")
            )
        )
        self.assertTrue(
            is_relevant(
                _job(
                    title="DevOps Engineer",
                    description="1-2 years of experience with Terraform",
                    location="Grand Central, Manhattan",
                    area=["US", "New York", "New York City", "Manhattan", "Grand Central"],
                )
            )
        )

    def test_drops_manager_and_lead_titles(self):
        manhattan = dict(
            location="Grand Central, Manhattan",
            area=["US", "New York", "New York City", "Manhattan", "Grand Central"],
        )
        self.assertTrue(is_leadership_title("Lead Software & Platform Engineer"))
        self.assertTrue(is_leadership_title("Engineering Manager"))
        self.assertTrue(is_leadership_title("DevOps Team Leader"))
        self.assertTrue(is_leadership_title("Lead Engineer"))
        self.assertFalse(is_leadership_title("Senior DevOps Engineer"))
        self.assertFalse(is_leadership_title("Staff SRE"))
        self.assertFalse(
            is_relevant(
                _job(
                    title="Lead Software & Platform Engineer",
                    description="DevOps/SRE practices on trading platforms",
                    **manhattan,
                )
            )
        )
        self.assertFalse(
            is_relevant(_job(title="Engineering Manager", **manhattan))
        )
        self.assertTrue(
            is_relevant(
                _job(
                    title="Senior DevOps Engineer",
                    description="Reports to the engineering manager. Leadership team.",
                    **manhattan,
                )
            )
        )

    def test_keeps_noc_infra_production_market_ops(self):
        manhattan = dict(
            location="Grand Central, Manhattan",
            area=["US", "New York", "New York City", "Manhattan", "Grand Central"],
        )
        for title in (
            "NOC Engineer",
            "Associate Production Engineer",
            "Infrastructure Engineer",
            "Market Operations Engineer",
        ):
            self.assertTrue(
                is_relevant(_job(title=title, **manhattan)),
                title,
            )
        self.assertFalse(
            is_relevant(_job(title="Junior NOC Engineer", **manhattan))
        )
        self.assertFalse(
            is_relevant(_job(title="Lead Infrastructure Engineer", **manhattan))
        )
        self.assertFalse(
            is_relevant(
                _job(
                    title="Infrastructure Engineer",
                    location="Jersey City, Hudson County",
                    area=["US", "New Jersey", "Hudson County", "Jersey City"],
                )
            )
        )

    def test_salary_window_and_sort(self):
        manhattan = dict(
            location="Grand Central, Manhattan",
            area=["US", "New York", "New York City", "Manhattan", "Grand Central"],
        )
        self.assertFalse(is_relevant(_job(salary_min=None, salary_max=None, **manhattan)))
        self.assertFalse(is_relevant(_job(salary_min=60000, salary_max=90000, **manhattan)))
        self.assertFalse(is_relevant(_job(salary_min=90000, salary_max=120000, **manhattan)))
        self.assertFalse(is_relevant(_job(salary_min=50000, salary_max=90000, **manhattan)))
        self.assertFalse(is_relevant(_job(salary_min=90000, salary_max=150000, **manhattan)))
        self.assertFalse(is_relevant(_job(salary_min=45, salary_max=55, **manhattan)))
        self.assertTrue(is_relevant(_job(salary_min=60001, salary_max=119999, **manhattan)))
        ordered = relevant_jobs(
            [
                _job(title="SRE", salary_min=80000, salary_max=85000, **manhattan),
                _job(
                    title="DevOps Engineer",
                    salary_min=100000,
                    salary_max=110000,
                    **manhattan,
                ),
            ]
        )
        self.assertEqual(
            [job["title"] for job in ordered],
            ["DevOps Engineer", "SRE"],
        )


if __name__ == "__main__":
    unittest.main()
