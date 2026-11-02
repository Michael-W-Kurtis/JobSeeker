from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from collections.abc import Mapping
from typing import Any
from zoneinfo import ZoneInfo

from jobseeker.adzuna import collect
from jobseeker.config import Config
from jobseeker.filter import relevant_jobs
from jobseeker.store import SeenStore
from jobseeker.telegram import send_digest

NY = ZoneInfo("America/New_York")


@dataclass
class RunResult:
    fetched: int
    relevant: int
    new: int
    sent_chunks: int
    dry_run: bool
    raw_path: Path | None
    jobs: list[Mapping[str, Any]]


def dump_raw(pages: list[dict[str, Any]], state_dir: Path) -> Path:
    raw_dir = state_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(NY).strftime("%Y%m%dT%H%M%S")
    path = raw_dir / f"adzuna-{stamp}.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for page in pages:
            fh.write(json.dumps(page, ensure_ascii=False) + "\n")
    return path


def run(
    cfg: Config,
    *,
    dry_run: bool = False,
    opener=None,
    telegram_opener=None,
) -> RunResult:
    jobs, pages = collect(
        cfg.adzuna_app_id,
        cfg.adzuna_app_key,
        where=cfg.where,
        distance_km=cfg.distance_km,
        max_days_old=cfg.max_days_old,
        country=cfg.country,
        opener=opener,
    )
    raw_path = dump_raw(pages, cfg.state_dir)
    matched = relevant_jobs(jobs)
    store = SeenStore(cfg.state_dir / "seen.sqlite")
    try:
        new_jobs = store.unseen(matched)
        if not new_jobs:
            return RunResult(
                fetched=len(jobs),
                relevant=len(matched),
                new=0,
                sent_chunks=0,
                dry_run=dry_run,
                raw_path=raw_path,
                jobs=[],
            )
        if dry_run:
            return RunResult(
                fetched=len(jobs),
                relevant=len(matched),
                new=len(new_jobs),
                sent_chunks=0,
                dry_run=True,
                raw_path=raw_path,
                jobs=new_jobs,
            )
        chunks = send_digest(
            cfg.telegram_bot_token,
            cfg.telegram_chat_id,
            new_jobs,
            where=cfg.where,
            opener=telegram_opener,
        )
        store.mark_alerted(new_jobs)
        return RunResult(
            fetched=len(jobs),
            relevant=len(matched),
            new=len(new_jobs),
            sent_chunks=chunks,
            dry_run=False,
            raw_path=raw_path,
            jobs=new_jobs,
        )
    finally:
        store.close()


def print_new_jobs(jobs: list[Mapping[str, Any]]) -> None:
    for job in jobs:
        created = (job.get("created") or "")[:10]
        print(
            f"- {job.get('title')} | {job.get('company')} | "
            f"{job.get('location')} | {created} | {job.get('url')}"
        )
