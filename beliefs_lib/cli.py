"""Belief tracker CLI — manage claims and contradictions across repos."""

import sys
import argparse
from datetime import date
from pathlib import Path

from . import Claim, Nogood
from .parser import (
    parse_registry, append_claim, update_claim_status,
    parse_nogoods, append_nogood,
)
from .check_refs import check_refs
from .check_stale import check_stale
from .resolve import compute_entrenchment, resolve_conflict, classify_source
from .nogoods_cmd import list_nogoods, filter_nogoods, detail_nogood
from .compact import compact


def default_path(name: str) -> Path:
    return Path.cwd() / name


def cmd_check_refs(args):
    repos, claims = parse_registry(args.registry)
    results = check_refs(claims, repos)

    ok = warn = fail = 0
    for claim_id, status, msg in results:
        if status == "OK":
            ok += 1
            if not args.quiet:
                print(f"OK    {claim_id}")
        elif status == "WARN":
            warn += 1
            if not args.quiet:
                print(f"WARN  {claim_id}")
                print(f"      {msg}")
        elif status == "FAIL":
            fail += 1
            if not args.quiet:
                print(f"FAIL  {claim_id}")
                print(f"      {msg}")
        if not args.quiet and status != "OK":
            print()

    if not args.quiet:
        print(f"Summary: {ok} OK, {warn} WARN, {fail} FAIL")

    sys.exit(1 if fail > 0 else 0)


def cmd_check_stale(args):
    repos, claims = parse_registry(args.registry)
    results = check_stale(claims, repos)

    in_claims = [c for c in claims if c.status == "IN"]
    stale_ids = set()
    for claim_id, status, msg, entry_path in results:
        stale_ids.add(claim_id)
        if not args.quiet:
            print(f"STALE {claim_id}")
            print(f"      {msg}")
            print(f"      Entry: {entry_path}")
            print()

    ok_count = len(in_claims) - len(stale_ids)
    if not args.quiet:
        print(f"Summary: {ok_count} OK, {len(stale_ids)} STALE")

    sys.exit(1 if stale_ids else 0)


def cmd_add(args):
    repos, claims = parse_registry(args.registry)

    # Check for duplicate ID
    for c in claims:
        if c.id == args.id:
            print(f"Error: claim '{args.id}' already exists", file=sys.stderr)
            sys.exit(1)

    claim = Claim(
        id=args.id,
        text=args.text,
        source=args.source or "",
        date=args.date or date.today().isoformat(),
        status="IN",
        type=args.type or "",
        assumes=args.assumes or [],
        depends_on=args.depends_on or [],
    )

    append_claim(args.registry, claim)

    if not args.quiet:
        print(f"Added claim '{claim.id}' (status: IN)")
        if claim.source:
            print(f"  Source:      {claim.source}")
        print(f"  Date:        {claim.date}")
        if claim.assumes:
            print(f"  Assumptions: {', '.join(claim.assumes)}")
        if claim.depends_on:
            print(f"  Depends on:  {', '.join(claim.depends_on)}")
        if claim.type:
            print(f"  Type:        {claim.type}")


def cmd_resolve(args):
    repos, claims = parse_registry(args.registry)

    claim_a = claim_b = None
    for c in claims:
        if c.id == args.claim_a:
            claim_a = c
        if c.id == args.claim_b:
            claim_b = c

    if claim_a is None:
        print(f"Error: claim '{args.claim_a}' not found", file=sys.stderr)
        sys.exit(1)
    if claim_b is None:
        print(f"Error: claim '{args.claim_b}' not found", file=sys.stderr)
        sys.exit(1)

    winner_id, loser_id, winner_score, loser_score = resolve_conflict(claim_a, claim_b)

    if not args.quiet:
        for c in [claim_a, claim_b]:
            source_type = classify_source(c.source)
            score = compute_entrenchment(c)
            print(f"  {c.id}")
            print(f"    Text:    \"{c.text[:70]}\"")
            print(f"    Source:  {c.source} ({source_type}: {score})")
            print(f"    Date:    {c.date}")
            if c.type:
                print(f"    Type:    {c.type}")
            print(f"    Score:   {score}")
            print()

        print(f"Resolution: {winner_id} wins ({winner_score} vs {loser_score})")
        print(f"  -> {loser_id} should be marked STALE")


def cmd_nogoods(args):
    nogoods = parse_nogoods(args.nogoods_file)

    if args.affecting:
        matched = filter_nogoods(nogoods, affecting=args.affecting)
        if not matched:
            print(f"No nogoods affecting '{args.affecting}'")
            return
        for ng in matched:
            print(detail_nogood(ng))
            print()
    else:
        print(list_nogoods(nogoods))


def cmd_compact(args):
    repos, claims = parse_registry(args.registry)
    nogoods = parse_nogoods(args.nogoods_file)
    print(compact(claims, nogoods, budget=args.budget))


def main():
    parser = argparse.ArgumentParser(
        prog="beliefs",
        description="Belief tracker — manage claims and contradictions across repos",
    )
    parser.add_argument(
        "--registry", type=Path, default=default_path("beliefs.md"),
        help="Path to beliefs.md (default: ./beliefs.md)",
    )
    parser.add_argument(
        "--nogoods-file", type=Path, default=default_path("nogoods.md"),
        help="Path to nogoods.md (default: ./nogoods.md)",
    )
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress detail, exit code only")

    sub = parser.add_subparsers(dest="command", required=True)

    # check-refs
    sub.add_parser("check-refs", help="Verify cross-references for all claims")

    # check-stale
    sub.add_parser("check-stale", help="Detect stale IN claims vs newer entries")

    # add
    add_p = sub.add_parser("add", help="Add a new claim to the registry")
    add_p.add_argument("--id", required=True, help="Claim ID (kebab-case)")
    add_p.add_argument("--text", required=True, help="Claim text (one line)")
    add_p.add_argument("--source", help="Source file path (repo/path)")
    add_p.add_argument("--date", help="Claim date YYYY-MM-DD (default: today)")
    add_p.add_argument("--assumes", nargs="*", help="Assumption labels")
    add_p.add_argument("--depends-on", nargs="*", help="Claim IDs this depends on")
    add_p.add_argument("--type", choices=["DERIVED", "PREDICTED", "MATCHED", "INHERITED", "AXIOM"],
                        help="Derivation type")

    # resolve
    resolve_p = sub.add_parser("resolve", help="Resolve conflict between two claims")
    resolve_p.add_argument("claim_a", help="First claim ID")
    resolve_p.add_argument("claim_b", help="Second claim ID")

    # nogoods
    nogoods_p = sub.add_parser("nogoods", help="List/query the nogoods database")
    nogoods_p.add_argument("--affecting", help="Filter by affected claim ID")

    # compact
    compact_p = sub.add_parser("compact", help="Produce a context summary")
    compact_p.add_argument("--budget", type=int, default=500, help="Token budget (default: 500)")

    args = parser.parse_args()

    commands = {
        "check-refs": cmd_check_refs,
        "check-stale": cmd_check_stale,
        "add": cmd_add,
        "resolve": cmd_resolve,
        "nogoods": cmd_nogoods,
        "compact": cmd_compact,
    }
    commands[args.command](args)
