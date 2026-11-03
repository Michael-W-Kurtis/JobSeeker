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
        r"\bnoc\s+engineer\b",
        r"network operations (?:center|centre)",
        r"infrastructure engineer",
        r"production engineer",
        r"market operations engineer",
        r"market ops engineer",
    )
)

# Place/title only. Bare "remote" in the description is remote support /
# remote desktop, not WFH. Genuine remote work keeps regardless of HQ geo.
REMOTE_RE = re.compile(
    r"\b(remote|wfh|work[\s-]*from[\s-]*home)\b",
    re.I,
)
REMOTE_MODE_RE = re.compile(
    r"\b("
    r"fully\s+remote|remote-first|remote-only|100%\s+remote|"
    r"work[\s-]*from[\s-]*home|\bwfh\b|"
    r"remote\s+work|remote\s+position|remote\s+role|remote\s+job|"
    r"this\s+is\s+a\s+remote"
    r")\b",
    re.I,
)

# Closed allowlist. One hit is enough even if NJ / Brooklyn / etc. also appear.
# Generic NYC / New York, New York / Nassau is not enough.
ALLOW_GEO_RE = re.compile(
    r"""
    \bmanhattan\b|\bqueens\b|\bbronx\b
    """,
    re.I | re.VERBOSE,
)

JUNIOR_TITLE_RE = re.compile(
    r"\b(intern|internship|junior|jr\.?|entry[ -]?level|new[ -]?grad|graduate)\b",
    re.I,
)
# Keep "Junior Senior" / "Staff intern" IC mixes. lead/manager are a drop, not a keep.
SENIOR_TITLE_RE = re.compile(
    r"\b(senior|sr\.?|staff|principal|mid[ -]?level)\b",
    re.I,
)
# Title only. JD phrases like "report to the manager" must not kill IC roles.
LEADERSHIP_TITLE_RE = re.compile(
    r"""
    \b(
      manager|director|
      vice[ -]?president|vp|
      head[ -]of|
      chief|
      leader|
      lead
    )\b
    """,
    re.I | re.VERBOSE,
)

MAX_YEARS_REQUIRED = 2
_YEARS_NUM = r"""
    (?:
      (?P<min>\d{1,2})\s*(?:-|–|to)\s*(?P<max>\d{1,2})
      |
      (?P<plus>\d{1,2})\s*\+
      |
      (?P<n>\d{1,2})
    )
"""
EXPERIENCE_RE = re.compile(
    rf"""
    {_YEARS_NUM}
    \s*(?:years?|yrs?|year)
    (?:\s+of)?
    \s+(?:experience|exp\b|professional|relevant|hands-?on|in\b|with\b)
    """,
    re.I | re.VERBOSE,
)
# "Work Experience 10-15 Years" / "Work Experience: 7+ Years"
EXPERIENCE_LABEL_RE = re.compile(
    rf"""
    (?:work\s+)?experience\s*[:\-]?\s*(?:of\s*)?
    {_YEARS_NUM}
    \s*(?:years?|yrs?|year)?
    """,
    re.I | re.VERBOSE,
)
AT_LEAST_RE = re.compile(
    r"(?:at\s+least|minimum(?:\s+of)?|min\.?)\s+(\d{1,2})\s*\+?\s*(?:years?|yrs?|year)",
    re.I,
)
_CAP_PREFIX_RE = re.compile(
    r"(?:under|up\s+to|at\s+most|no\s+more\s+than|maximum|max(?:imum)?(?:\s+of)?)\s*$",
    re.I,
)


def geo_text(job: Mapping[str, Any]) -> str:
    area = job.get("area") or []
    if isinstance(area, (list, tuple)):
        area_text = " ".join(str(x) for x in area)
    else:
        area_text = str(area)
    return f"{job.get('location') or ''} {area_text}"


def matches_role(job: Mapping[str, Any]) -> bool:
    text = f"{job.get('title') or ''} {job.get('description') or ''}"
    return any(rx.search(text) for rx in ROLE_RES)


def is_remote(job: Mapping[str, Any]) -> bool:
    geo = geo_text(job)
    title = str(job.get("title") or "")
    if REMOTE_RE.search(geo) or REMOTE_RE.search(title):
        return True
    return bool(REMOTE_MODE_RE.search(str(job.get("description") or "")))


def matches_location(job: Mapping[str, Any]) -> bool:
    if is_remote(job):
        return True
    blob = f"{geo_text(job)} {job.get('title') or ''}"
    return bool(ALLOW_GEO_RE.search(blob))


def is_junior_title(title: str) -> bool:
    if not JUNIOR_TITLE_RE.search(title or ""):
        return False
    return not SENIOR_TITLE_RE.search(title or "")


def is_leadership_title(title: str) -> bool:
    return bool(LEADERSHIP_TITLE_RE.search(title or ""))


def _named_years_too_high(m: re.Match[str], max_years: int) -> bool:
    if m.group("min") is not None:
        return int(m.group("min")) > max_years or int(m.group("max")) > max_years
    if m.group("plus") is not None:
        return int(m.group("plus")) > max_years
    if m.group("n") is not None:
        return int(m.group("n")) > max_years
    return False


def exceeds_max_experience(
    job: Mapping[str, Any], *, max_years: int = MAX_YEARS_REQUIRED
) -> bool:
    text = f"{job.get('title') or ''} {job.get('description') or ''}"
    for rx in (EXPERIENCE_RE, EXPERIENCE_LABEL_RE):
        for m in rx.finditer(text):
            left = text[max(0, m.start() - 24) : m.start()]
            if _CAP_PREFIX_RE.search(left.rstrip()):
                continue
            if _named_years_too_high(m, max_years):
                return True
    for m in AT_LEAST_RE.finditer(text):
        left = text[max(0, m.start() - 24) : m.start()]
        if _CAP_PREFIX_RE.search(left.rstrip()):
            continue
        if int(m.group(1)) > max_years:
            return True
    return False


SALARY_MIN_EXCL = 60_000
SALARY_MAX_EXCL = 120_000
_ANNUAL_FLOOR = 1_000


def _money(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return number


def advertised_salary(job: Mapping[str, Any]) -> tuple[float, float] | None:
    lo = _money(job.get("salary_min"))
    hi = _money(job.get("salary_max"))
    if lo is None and hi is None:
        return None
    if lo is None:
        lo = hi
    if hi is None:
        hi = lo
    if lo is None or hi is None:
        return None
    if lo > hi:
        lo, hi = hi, lo
    return lo, hi


def in_salary_band(
    job: Mapping[str, Any],
    *,
    salary_min_excl: int = SALARY_MIN_EXCL,
    salary_max_excl: int = SALARY_MAX_EXCL,
) -> bool:
    band = advertised_salary(job)
    if band is None:
        return False
    lo, hi = band
    if hi < _ANNUAL_FLOOR:
        return False
    return lo > salary_min_excl and hi < salary_max_excl


def salary_sort_key(job: Mapping[str, Any]) -> float:
    band = advertised_salary(job)
    if band is None:
        return 0.0
    return band[1]


def format_salary_usd(job: Mapping[str, Any]) -> str:
    band = advertised_salary(job)
    if band is None:
        return ""

    def _fmt(amount: float) -> str:
        whole = int(round(amount))
        if whole % 1000 == 0:
            return f"${whole // 1000}k"
        return f"${whole:,}"

    lo, hi = band
    if int(round(lo)) == int(round(hi)):
        return _fmt(lo)
    return f"{_fmt(lo)}–{_fmt(hi)}"


def is_relevant(
    job: Mapping[str, Any],
    *,
    salary_min_excl: int = SALARY_MIN_EXCL,
    salary_max_excl: int = SALARY_MAX_EXCL,
) -> bool:
    title = str(job.get("title") or "")
    if is_leadership_title(title):
        return False
    if is_junior_title(title):
        return False
    if exceeds_max_experience(job):
        return False
    if not in_salary_band(
        job,
        salary_min_excl=salary_min_excl,
        salary_max_excl=salary_max_excl,
    ):
        return False
    return matches_role(job) and matches_location(job)


def relevant_jobs(
    jobs: Iterable[Mapping[str, Any]],
    *,
    salary_min_excl: int = SALARY_MIN_EXCL,
    salary_max_excl: int = SALARY_MAX_EXCL,
) -> list[Mapping[str, Any]]:
    kept = [
        job
        for job in jobs
        if is_relevant(
            job,
            salary_min_excl=salary_min_excl,
            salary_max_excl=salary_max_excl,
        )
    ]
    kept.sort(key=salary_sort_key, reverse=True)
    return kept
