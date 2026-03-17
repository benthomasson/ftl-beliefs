"""Detect circular dependencies in the belief registry."""

from . import Claim


def find_cycles(claims: list[Claim]) -> list[list[str]]:
    """Find all circular dependency chains among IN claims.

    Returns a list of cycles, where each cycle is a list of claim IDs
    forming the loop (e.g., ["a", "b", "c", "a"]).
    """
    # Build adjacency list from depends_on (IN claims only)
    in_claims = {c.id: c for c in claims if c.status == "IN"}
    adj: dict[str, list[str]] = {}
    for cid, claim in in_claims.items():
        adj[cid] = [dep for dep in claim.depends_on if dep in in_claims]

    # DFS with coloring: WHITE=unvisited, GRAY=in progress, BLACK=done
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {cid: WHITE for cid in in_claims}
    parent: dict[str, str | None] = {}
    cycles: list[list[str]] = []
    seen_cycles: set[frozenset[str]] = set()  # deduplicate

    def dfs(node: str) -> None:
        color[node] = GRAY
        for neighbor in adj.get(node, []):
            if color[neighbor] == GRAY:
                # Found a cycle — reconstruct it
                cycle = [neighbor]
                cur = node
                while cur != neighbor:
                    cycle.append(cur)
                    cur = parent.get(cur, neighbor)
                cycle.append(neighbor)
                cycle.reverse()

                # Deduplicate (same cycle can be found from different start nodes)
                cycle_set = frozenset(cycle[:-1])
                if cycle_set not in seen_cycles:
                    seen_cycles.add(cycle_set)
                    cycles.append(cycle)

            elif color[neighbor] == WHITE:
                parent[neighbor] = node
                dfs(neighbor)

        color[node] = BLACK

    for cid in in_claims:
        if color[cid] == WHITE:
            parent[cid] = None
            dfs(cid)

    return cycles


def find_self_dependencies(claims: list[Claim]) -> list[str]:
    """Find IN claims that depend on themselves."""
    return [
        c.id for c in claims
        if c.status == "IN" and c.id in c.depends_on
    ]
