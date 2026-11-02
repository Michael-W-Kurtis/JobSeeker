from __future__ import annotations

import argparse
import sys
from pathlib import Path

from jobseeker.config import load_config
from jobseeker.pipeline import print_new_jobs, run


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="jobseeker",
        description="Fetch Adzuna listings, filter locally, Telegram only new matches.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and filter; do not send Telegram or mark seen",
    )
    parser.add_argument("--where", default=None, help='Adzuna where= (default: "New York")')
    parser.add_argument("--env-file", default=None, help="Path to .env (default: repo/.env)")
    parser.add_argument("--state-dir", default=None, help="Raw dumps + seen.sqlite (default: ./data)")
    args = parser.parse_args(argv)

    root = repo_root()
    cfg = load_config(
        repo_root=root,
        env_file=Path(args.env_file) if args.env_file else None,
        where=args.where,
        state_dir=Path(args.state_dir) if args.state_dir else None,
        require_telegram=not args.dry_run,
    )
    result = run(cfg, dry_run=args.dry_run)
    print(
        f"fetched={result.fetched} relevant={result.relevant} "
        f"new={result.new} sent_chunks={result.sent_chunks} "
        f"dry_run={result.dry_run} raw={result.raw_path}"
    )
    if result.jobs:
        print_new_jobs(result.jobs)
    if result.new == 0:
        print("no new matches; telegram silent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
