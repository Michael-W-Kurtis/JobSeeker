from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def _require(name: str) -> str:
    value = (os.environ.get(name) or "").strip()
    if not value:
        raise SystemExit(f"missing required environment variable: {name}")
    return value


def _optional(name: str, default: str) -> str:
    value = os.environ.get(name)
    if value is None or not str(value).strip():
        return default
    return str(value).strip()


@dataclass(frozen=True)
class Config:
    adzuna_app_id: str
    adzuna_app_key: str
    telegram_bot_token: str
    telegram_chat_id: str
    where: str
    distance_km: int
    max_days_old: int
    country: str
    state_dir: Path
    repo_root: Path


def load_config(
    *,
    repo_root: Path,
    env_file: Path | None = None,
    where: str | None = None,
    state_dir: Path | None = None,
    require_telegram: bool = True,
) -> Config:
    load_env_file(env_file or (repo_root / ".env"))
    chat_id = (
        (os.environ.get("TELEGRAM_CHAT_ID") or "").strip()
        or (os.environ.get("TELEGRAM_HOME_CHANNEL") or "").strip()
    )
    token = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
    if require_telegram:
        if not token:
            raise SystemExit("missing required environment variable: TELEGRAM_BOT_TOKEN")
        if not chat_id:
            raise SystemExit("missing required environment variable: TELEGRAM_CHAT_ID")
    return Config(
        adzuna_app_id=_require("ADZUNA_APP_ID"),
        adzuna_app_key=_require("ADZUNA_APP_KEY"),
        telegram_bot_token=token,
        telegram_chat_id=chat_id,
        where=where or _optional("JOBSEEKER_WHERE", "New York"),
        distance_km=int(_optional("JOBSEEKER_DISTANCE_KM", "40")),
        max_days_old=int(_optional("JOBSEEKER_MAX_DAYS_OLD", "7")),
        country=_optional("JOBSEEKER_COUNTRY", "us"),
        state_dir=state_dir or Path(_optional("JOBSEEKER_STATE_DIR", str(repo_root / "data"))),
        repo_root=repo_root,
    )
