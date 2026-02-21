"""Staleness detection: compare IN claims against newer entries."""

import re
from datetime import date
from pathlib import Path

from . import Claim
from .check_refs import extract_keywords

NEGATION_PAIRS = [
    ("not derived", "derived"),
    ("hasn't derived", "derived"),
    ("open problem", "resolved"),
    ("unresolved", "resolved"),
    ("not yet tested", "tested"),
    ("not yet tested", "completed"),
    ("unknown", "determined"),
    ("contradicts", "confirmed"),
]


def parse_date(date_str: str) -> date | None:
    """Parse YYYY-MM-DD date string."""
    try:
        parts = date_str.strip().split("-")
        return date(int(parts[0]), int(parts[1]), int(parts[2]))
    except (ValueError, IndexError):
        return None


def find_entries_after(after_date: date, repos: dict[str, str]) -> list[Path]:
    """Walk entries/YYYY/MM/DD/ dirs across all repos, return paths newer than date."""
    results = []
    date_dir_re = re.compile(r'.*/entries/(\d{4})/(\d{2})/(\d{2})$')

    for repo_name, repo_path in repos.items():
        entries_dir = Path(repo_path).expanduser() / "entries"
        if not entries_dir.is_dir():
            continue

        for year_dir in sorted(entries_dir.iterdir()):
            if not year_dir.is_dir():
                continue
            for month_dir in sorted(year_dir.iterdir()):
                if not month_dir.is_dir():
                    continue
                for day_dir in sorted(month_dir.iterdir()):
                    if not day_dir.is_dir():
                        continue
                    m = date_dir_re.match(str(day_dir))
                    if not m:
                        continue
                    try:
                        entry_date = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                    except ValueError:
                        continue
                    if entry_date <= after_date:
                        continue
                    # Collect all .md files in this day dir
                    for md_file in sorted(day_dir.glob("*.md")):
                        results.append(md_file)

    return results


def check_stale(claims: list[Claim], repos: dict[str, str]) -> list[tuple[str, str, str, str]]:
    """Check IN claims for staleness against newer entries.

    Returns list of (claim_id, status, message, entry_path).
    """
    results = []
    flagged = set()  # One STALE flag per claim (first evidence wins)

    for claim in claims:
        if claim.status != "IN":
            continue

        claim_date = parse_date(claim.date)
        if claim_date is None:
            continue

        newer_entries = find_entries_after(claim_date, repos)
        keywords = extract_keywords(claim.text)

        for entry_path in newer_entries:
            if claim.id in flagged:
                break

            try:
                content = entry_path.read_text().lower()
            except Exception:
                continue

            overlap = [k for k in keywords if k in content]
            if len(overlap) < 2:
                continue

            # Check for negation patterns
            claim_lower = claim.text.lower()
            for neg, pos in NEGATION_PAIRS:
                if neg in claim_lower and pos in content:
                    results.append((
                        claim.id, "STALE",
                        f"Claim contains '{neg}', entry contains '{pos}'",
                        str(entry_path)
                    ))
                    flagged.add(claim.id)
                    break
                elif pos in claim_lower and neg in content:
                    results.append((
                        claim.id, "STALE",
                        f"Claim contains '{pos}', entry contains '{neg}'",
                        str(entry_path)
                    ))
                    flagged.add(claim.id)
                    break

    return results
