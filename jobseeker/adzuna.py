from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Mapping

API_ROOT = "https://api.adzuna.com/v1/api"
USER_AGENT = "JobSeeker/0.1 (personal job search)"
TAG_RE = re.compile(r"<[^>]+>")

# One query per role family. `what` is AND of terms; `what_or` is OR.
# `distance` must be set: Adzuna defaults to 5km.
DEFAULT_QUERIES: tuple[dict[str, str], ...] = (
    {"what": "devops"},
    {"what": "SRE"},
    {"what": "sysadmin"},
    {"what_phrase": "help desk"},
    {"what_phrase": "solutions architect"},
    {"what_phrase": "NOC engineer"},
    {"what_phrase": "infrastructure engineer"},
    {"what_phrase": "production engineer"},
    {"what_phrase": "market operations engineer"},
)


class AdzunaError(RuntimeError):
    pass


def _strip_markup(text: str) -> str:
    return TAG_RE.sub("", text).replace("&nbsp;", " ").strip()


def normalize(raw: Mapping[str, Any]) -> dict[str, Any]:
    location = raw.get("location") if isinstance(raw.get("location"), dict) else {}
    company = raw.get("company") if isinstance(raw.get("company"), dict) else {}
    category = raw.get("category") if isinstance(raw.get("category"), dict) else {}
    area = location.get("area") or []
    if not isinstance(area, list):
        area = [str(area)]
    return {
        "id": str(raw.get("id") or ""),
        "title": _strip_markup(str(raw.get("title") or "")),
        "description": _strip_markup(str(raw.get("description") or "")),
        "created": str(raw.get("created") or ""),
        "url": str(raw.get("redirect_url") or ""),
        "company": str(company.get("display_name") or ""),
        "location": str(location.get("display_name") or ""),
        "area": [str(x) for x in area],
        "salary_min": raw.get("salary_min"),
        "salary_max": raw.get("salary_max"),
        "category": str(category.get("tag") or ""),
        "source": "adzuna",
    }


def search(
    app_id: str,
    app_key: str,
    *,
    country: str = "us",
    page: int = 1,
    where: str = "New York",
    distance_km: int = 40,
    max_days_old: int = 7,
    salary_min: int = 60000,
    salary_max: int = 120000,
    results_per_page: int = 50,
    category: str = "it-jobs",
    extra: Mapping[str, str] | None = None,
    opener: urllib.request.OpenerDirector | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": str(results_per_page),
        "where": where,
        "distance": str(distance_km),
        "max_days_old": str(max_days_old),
        "category": category,
        "sort_by": "salary",
        "salary_min": str(salary_min),
        "salary_max": str(salary_max),
        "content-type": "application/json",
    }
    if extra:
        params.update({k: v for k, v in extra.items() if v})
    url = (
        f"{API_ROOT}/jobs/{urllib.parse.quote(country)}/search/{int(page)}"
        f"?{urllib.parse.urlencode(params)}"
    )
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
        method="GET",
    )
    open_url = opener.open if opener is not None else urllib.request.urlopen
    try:
        with open_url(req, timeout=timeout) as resp:
            body = resp.read()
            status = getattr(resp, "status", 200)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise AdzunaError(f"Adzuna HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise AdzunaError(f"Adzuna request failed: {exc.reason}") from exc
    if status != 200:
        raise AdzunaError(f"Adzuna HTTP {status}")
    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise AdzunaError("Adzuna returned non-JSON") from exc
    if not isinstance(payload, dict):
        raise AdzunaError("Adzuna JSON was not an object")
    return payload


def collect(
    app_id: str,
    app_key: str,
    *,
    where: str,
    distance_km: int,
    max_days_old: int,
    salary_min: int = 60000,
    salary_max: int = 120000,
    country: str = "us",
    queries: tuple[dict[str, str], ...] = DEFAULT_QUERIES,
    opener: urllib.request.OpenerDirector | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    pages: list[dict[str, Any]] = []
    jobs: list[dict[str, Any]] = []
    seen: set[str] = set()
    for extra in queries:
        page = search(
            app_id,
            app_key,
            country=country,
            where=where,
            distance_km=distance_km,
            max_days_old=max_days_old,
            salary_min=salary_min,
            salary_max=salary_max,
            extra=extra,
            opener=opener,
        )
        pages.append(page)
        for raw in page.get("results") or []:
            if not isinstance(raw, dict):
                continue
            job = normalize(raw)
            key = job["id"] or job["url"]
            if not key or key in seen:
                continue
            seen.add(key)
            jobs.append(job)
    return jobs, pages
