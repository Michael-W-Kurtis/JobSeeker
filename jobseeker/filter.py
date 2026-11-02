from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

ROLE_RES = tuple(
    re.compile(p, re.I)
    for p in (
        r"\bdev\s*-?\s*ops\b",
        r"\bsre\b",
        r"site reliability",
        r"\bsysadmin\b",
        r"systems? administrator",
        r"help\s*-?\s*desk",
        r"desktop support",
        r"technical support",
        r"solutions architect",
        r"cloud architect",
    )
)

LOCATION_RES = tuple(
    re.compile(p, re.I)
    for p in (
        r"\bnew york\b",
        r"\bnyc\b",
        r"\bbrooklyn\b",
        r"\bmanhattan\b",
        r"\bqueens\b",
        r"\bbronx\b",
        r"\bhoboken\b",
        r"jersey city",
        r"\bhybrid\b",
        r"\bremote\b",
        r"united states",
        r"\busa\b",
    )
)

JUNIOR_TITLE_RE = re.compile(
    r"\b(intern|internship|junior|jr\.?|entry[ -]?level|new[ -]?grad|graduate)\b",
    re.I,
)
SENIOR_TITLE_RE = re.compile(
    r"\b(senior|sr\.?|staff|principal|lead|manager|mid[ -]?level)\b",
    re.I,
)


def _blob(job: Mapping[str, Any]) -> str:
    area = job.get("area") or []
    if isinstance(area, (list, tuple)):
        area_text = " ".join(str(x) for x in area)
    else:
        area_text = str(area)
    return " ".join(
        str(job.get(k) or "")
        for k in ("title", "description", "location", "company")
    ) + " " + area_text


def matches_role(job: Mapping[str, Any]) -> bool:
    text = f"{job.get('title') or ''} {job.get('description') or ''}"
    return any(rx.search(text) for rx in ROLE_RES)


def matches_location(job: Mapping[str, Any]) -> bool:
    return any(rx.search(_blob(job)) for rx in LOCATION_RES)


def is_junior_title(title: str) -> bool:
    if not JUNIOR_TITLE_RE.search(title or ""):
        return False
    return not SENIOR_TITLE_RE.search(title or "")


def is_relevant(job: Mapping[str, Any]) -> bool:
    if is_junior_title(str(job.get("title") or "")):
        return False
    return matches_role(job) and matches_location(job)


def relevant_jobs(jobs: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [job for job in jobs if is_relevant(job)]
