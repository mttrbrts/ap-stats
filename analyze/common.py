"""Shared helpers for ap-stats analysis scripts."""
from __future__ import annotations
import argparse
import json
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR = Path(__file__).parent.parent / "output"

BOT_LOGINS = {"pre-commit-ci", "snyk-bot", "jupyterhub-bot", "dependabot"}

def is_bot(login: str | None) -> bool:
    if login is None:
        return True
    return login.endswith("[bot]") or login in BOT_LOGINS

def get_windows(as_of: datetime | None = None, window_months: int = 12):
    """Return (current_start, current_end, prior_start, prior_end) as UTC datetimes."""
    if as_of is None:
        as_of = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    current_end = as_of
    current_start = current_end - relativedelta(months=window_months)
    prior_end = current_start
    prior_start = prior_end - relativedelta(months=window_months)
    return current_start, current_end, prior_start, prior_end

def parse_dt(s: str) -> datetime:
    """Parse GitHub ISO-8601 timestamp to UTC datetime."""
    return datetime.fromisoformat(s.replace("Z", "+00:00"))

def load_repos() -> list[dict]:
    return json.loads((DATA_DIR / "repos.json").read_text())

def load_prs(repo_name: str) -> list[dict]:
    path = DATA_DIR / "prs" / f"{repo_name}.json"
    if not path.exists():
        return []
    return json.loads(path.read_text())

def load_all_prs() -> dict[str, list[dict]]:
    prs_dir = DATA_DIR / "prs"
    result = {}
    if prs_dir.exists():
        for f in sorted(prs_dir.glob("*.json")):
            result[f.stem] = json.loads(f.read_text())
    return result

def load_code_frequency(repo_name: str) -> list[list]:
    path = DATA_DIR / "code_frequency" / f"{repo_name}.json"
    if not path.exists():
        return []
    return json.loads(path.read_text())

def load_all_code_frequency() -> dict[str, list[list]]:
    cf_dir = DATA_DIR / "code_frequency"
    result = {}
    if cf_dir.exists():
        for f in sorted(cf_dir.glob("*.json")):
            result[f.stem] = json.loads(f.read_text())
    return result

def build_merged_pr_counts(all_prs: dict[str, list[dict]]) -> dict[str, int]:
    """Return {login: count_of_merged_prs_across_all_repos} for non-bot authors."""
    counts: dict[str, int] = {}
    for prs in all_prs.values():
        for pr in prs:
            if pr.get("state") != "MERGED":
                continue
            login = (pr.get("author") or {}).get("login")
            if login and not is_bot(login):
                counts[login] = counts.get(login, 0) + 1
    return counts

def classify_author(login: str | None, author_association: str, merged_pr_counts: dict[str, int]) -> str:
    """Classify PR author into one of five kinds. First matching rule wins."""
    if login is None or is_bot(login):
        return "Bot"
    if author_association in {"OWNER", "MEMBER", "COLLABORATOR"}:
        return "Maintainer"
    count = merged_pr_counts.get(login, 0)
    if count <= 1:
        return "First Time Contributor"
    if count <= 9:
        return "Early Contributor"
    return "Seasoned Contributor"

def base_argparser(description: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--as-of", help="Reference date YYYY-MM-DD (default: today UTC)")
    p.add_argument("--window", default=12, type=int, help="Window in months (default: 12)")
    return p

def resolve_as_of(args) -> datetime | None:
    if getattr(args, "as_of", None):
        return datetime.fromisoformat(args.as_of).replace(tzinfo=timezone.utc)
    return None

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
