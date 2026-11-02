from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterable, Mapping
from typing import Any

TELEGRAM_API = "https://api.telegram.org"
MAX_MESSAGE = 3500
USER_AGENT = "JobSeeker/0.1 (personal job search)"


class TelegramError(RuntimeError):
    pass


def html_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def format_job_line(job: Mapping[str, Any]) -> str:
    title = html_escape(str(job.get("title") or "(no title)"))
    company = html_escape(str(job.get("company") or "unknown company"))
    location = html_escape(str(job.get("location") or "location n/a"))
    url = str(job.get("url") or "").strip()
    created = html_escape(str(job.get("created") or "")[:10])
    head = f"• <b>{title}</b> — {company} — {location}"
    if created:
        head += f" ({created})"
    if url:
        return f'{head}\n  <a href="{html_escape(url)}">Adzuna listing</a>'
    return head


def format_digest(jobs: Iterable[Mapping[str, Any]], *, where: str) -> list[str]:
    jobs = list(jobs)
    if not jobs:
        return []
    header = (
        f"{len(jobs)} new Adzuna match"
        f"{'es' if len(jobs) != 1 else ''} · {html_escape(where)}\n"
        "Personal search only. Source: Adzuna.\n"
    )
    chunks: list[str] = []
    current = header
    for job in jobs:
        block = "\n" + format_job_line(job) + "\n"
        if len(current) + len(block) > MAX_MESSAGE:
            chunks.append(current.rstrip())
            current = header + block
        else:
            current += block
    if current.strip():
        chunks.append(current.rstrip())
    return chunks


def send_message(
    bot_token: str,
    chat_id: str,
    text: str,
    *,
    opener: urllib.request.OpenerDirector | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    url = f"{TELEGRAM_API}/bot{bot_token}/sendMessage"
    payload = json.dumps(
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    open_url = opener.open if opener is not None else urllib.request.urlopen
    try:
        with open_url(req, timeout=timeout) as resp:
            body = resp.read()
            status = getattr(resp, "status", 200)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise TelegramError(f"Telegram HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise TelegramError(f"Telegram request failed: {exc.reason}") from exc
    if status != 200:
        raise TelegramError(f"Telegram HTTP {status}")
    try:
        data = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise TelegramError("Telegram returned non-JSON") from exc
    if not data.get("ok"):
        raise TelegramError(f"Telegram error: {data}")
    return data


def send_digest(
    bot_token: str,
    chat_id: str,
    jobs: Iterable[Mapping[str, Any]],
    *,
    where: str,
    opener: urllib.request.OpenerDirector | None = None,
) -> int:
    chunks = format_digest(jobs, where=where)
    for chunk in chunks:
        send_message(bot_token, chat_id, chunk, opener=opener)
    return len(chunks)
