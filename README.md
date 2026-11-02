# JobSeeker

Personal Adzuna collector. Pull listings, dump the raw payload, filter locally, Telegram only jobs that have not been alerted yet. Empty delta is silence.

This is not a public job board. Adzuna ToS: personal job search only. Do not republish the feed.

## What it does

1. GET Adzuna US `/jobs/us/search/1` for a small set of role queries (`devops`, `SRE`, `sysadmin`, `help desk`, `solutions architect`).
2. `where=New York` (override with `--where` or `JOBSEEKER_WHERE`). `distance=40` because Adzuna defaults to 5km.
3. `category=it-jobs`, `max_days_old=7`, `sort_by=date`, `results_per_page=50`.
4. Write the raw JSON pages to `data/raw/adzuna-<timestamp>.jsonl`.
5. Keep listings whose title/description match the role list and whose location blob looks like NYC / hybrid / remote-US. Drop intern/junior titles unless they also say senior/staff/lead.
6. Dedup on Adzuna id, else canonical URL, else `(company, title, location)` in `data/seen.sqlite`.
7. If there are unseen matches, send one HTML digest to Telegram and mark those ids seen. If Telegram fails, nothing is marked, so the next run retries.

## Setup

Stdlib only. Python 3.10+.

```bash
cd /home/mwk/git/JobSeeker
cp .env.example .env
```

Register a free personal Adzuna app (no card): https://developer.adzuna.com/signup

Put these in `.env`:

```
ADZUNA_APP_ID=...
ADZUNA_APP_KEY=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

`.env` is gitignored.

## Run

Dry run (hits Adzuna, prints matches, does not Telegram, does not mark seen):

```bash
cd /home/mwk/git/JobSeeker
python3 -m jobseeker --dry-run
```

Live (Telegram + mark seen):

```bash
cd /home/mwk/git/JobSeeker
python3 -m jobseeker
```

No cron until that live pass looks sane.

## Tests (no network, no keys)

```bash
cd /home/mwk/git/JobSeeker
python3 -m unittest discover -s tests -v
```
