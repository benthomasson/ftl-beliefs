"""Nogood database operations."""

from . import Nogood


def list_nogoods(nogoods: list[Nogood]) -> str:
    """Format all nogoods for display."""
    if not nogoods:
        return "No nogoods recorded."

    lines = [f"{len(nogoods)} recorded nogoods:", ""]
    for ng in nogoods:
        affected = len(ng.affects)
        status = "Resolved" if ng.resolution else "Open"
        lines.append(f"  {ng.id}  {ng.description}")
        lines.append(f"{'':10}Discovered: {ng.discovered}  |  Affected: {affected} claim{'s' if affected != 1 else ''}  |  Status: {status}")
        lines.append("")
    return "\n".join(lines)


def filter_nogoods(nogoods: list[Nogood], affecting: str | None = None) -> list[Nogood]:
    """Filter nogoods by affected claim ID."""
    if affecting is None:
        return nogoods
    return [ng for ng in nogoods if affecting in ng.affects]


def detail_nogood(ng: Nogood) -> str:
    """Format a single nogood with full detail."""
    lines = [
        f"  {ng.id}  {ng.description}",
        f"{'':10}Discovery:   {ng.discovered_by}, {ng.discovered}",
    ]
    if ng.resolution:
        lines.append(f"{'':10}Resolution:  {ng.resolution}")
    if ng.affects:
        lines.append(f"{'':10}Affected:    {', '.join(ng.affects)}")
    return "\n".join(lines)


def next_nogood_id(nogoods: list[Nogood]) -> str:
    """Generate next nogood ID (nogood-NNN)."""
    if not nogoods:
        return "nogood-001"
    max_num = 0
    for ng in nogoods:
        try:
            num = int(ng.id.split("-")[1])
            max_num = max(max_num, num)
        except (IndexError, ValueError):
            pass
    return f"nogood-{max_num + 1:03d}"
