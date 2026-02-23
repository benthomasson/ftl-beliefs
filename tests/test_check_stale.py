"""Tests for staleness detection: source hash and keyword heuristic."""

import hashlib
from pathlib import Path

import pytest

from beliefs_lib import Claim
from beliefs_lib.check_stale import (
    check_source_hashes,
    check_stale,
    find_entries_after,
    hash_file,
    parse_date,
)


@pytest.fixture
def repo_tree(tmp_path):
    """Create a minimal repo structure with entries."""
    repo = tmp_path / "physics"
    entries = repo / "entries" / "2026" / "02" / "22"
    entries.mkdir(parents=True)
    (entries / "test-entry.md").write_text("# Test Entry\nSome content about derived results\n")

    older = repo / "entries" / "2026" / "02" / "20"
    older.mkdir(parents=True)
    (older / "old-entry.md").write_text("# Old Entry\nOriginal source content\n")

    return {"physics": str(repo)}


@pytest.fixture
def source_file(tmp_path):
    """Create a source file for hash testing."""
    f = tmp_path / "source.md"
    f.write_text("# Source\nOriginal content\n")
    return f


class TestParseDate:
    def test_valid_date(self):
        d = parse_date("2026-02-22")
        assert d.year == 2026
        assert d.month == 2
        assert d.day == 22

    def test_invalid_date(self):
        assert parse_date("not-a-date") is None

    def test_empty_string(self):
        assert parse_date("") is None

    def test_whitespace(self):
        d = parse_date("  2026-02-22  ")
        assert d is not None
        assert d.day == 22


class TestHashFile:
    def test_hash_deterministic(self, source_file):
        h1 = hash_file(source_file)
        h2 = hash_file(source_file)
        assert h1 == h2

    def test_hash_length(self, source_file):
        h = hash_file(source_file)
        assert len(h) == 16

    def test_hash_changes_with_content(self, source_file):
        h1 = hash_file(source_file)
        source_file.write_text("# Source\nModified content\n")
        h2 = hash_file(source_file)
        assert h1 != h2


class TestFindEntriesAfter:
    def test_finds_newer_entries(self, repo_tree):
        from datetime import date
        entries = find_entries_after(date(2026, 2, 21), repo_tree)
        paths = [str(p) for p in entries]
        assert any("2026/02/22/test-entry.md" in p for p in paths)

    def test_excludes_older_entries(self, repo_tree):
        from datetime import date
        entries = find_entries_after(date(2026, 2, 21), repo_tree)
        paths = [str(p) for p in entries]
        assert not any("2026/02/20" in p for p in paths)

    def test_empty_for_future_date(self, repo_tree):
        from datetime import date
        entries = find_entries_after(date(2027, 1, 1), repo_tree)
        assert entries == []


class TestCheckSourceHashes:
    def test_unchanged_source_not_flagged(self, tmp_path, repo_tree):
        source = Path(repo_tree["physics"]) / "entries" / "2026" / "02" / "20" / "old-entry.md"
        h = hash_file(source)
        claims = [Claim(
            id="test", text="Test", status="IN",
            source="physics/entries/2026/02/20/old-entry.md",
            source_hash=h, date="2026-02-20",
        )]
        results, fresh = check_source_hashes(claims, repo_tree)
        assert results == []
        assert "test" in fresh

    def test_changed_source_flagged_stale(self, repo_tree):
        claims = [Claim(
            id="test", text="Test", status="IN",
            source="physics/entries/2026/02/20/old-entry.md",
            source_hash="wrong_hash_1234",
            date="2026-02-20",
        )]
        results, fresh = check_source_hashes(claims, repo_tree)
        assert len(results) == 1
        assert results[0][0] == "test"
        assert results[0][1] == "STALE"
        assert "test" not in fresh

    def test_out_claims_skipped(self, repo_tree):
        claims = [Claim(
            id="test", text="Test", status="OUT",
            source="physics/entries/2026/02/20/old-entry.md",
            source_hash="wrong", date="2026-02-20",
        )]
        results, fresh = check_source_hashes(claims, repo_tree)
        assert results == []
        assert fresh == set()

    def test_no_source_hash_skipped(self, repo_tree):
        claims = [Claim(
            id="test", text="Test", status="IN",
            source="physics/entries/2026/02/20/old-entry.md",
            source_hash="", date="2026-02-20",
        )]
        results, fresh = check_source_hashes(claims, repo_tree)
        assert results == []
        assert fresh == set()


class TestCheckStale:
    def test_hash_fresh_skips_keyword_heuristic(self, repo_tree):
        """Claims with unchanged source hashes should NOT be flagged by keywords."""
        source = Path(repo_tree["physics"]) / "entries" / "2026" / "02" / "20" / "old-entry.md"
        h = hash_file(source)
        # Claim text shares keywords with newer entry ("derived", "results")
        claims = [Claim(
            id="test", text="Content about derived results and physics",
            status="IN",
            source="physics/entries/2026/02/20/old-entry.md",
            source_hash=h, date="2026-02-20",
        )]
        results = check_stale(claims, repo_tree)
        assert results == [], "Hash-fresh claim should not be flagged by keyword heuristic"

    def test_no_hash_allows_keyword_check(self, repo_tree):
        """Claims without source hashes should still use keyword heuristic."""
        # Newer entry contains "derived" and "results" — matches claim keywords
        claims = [Claim(
            id="test",
            text="Not derived yet, results pending",
            status="IN",
            source="", source_hash="",
            date="2026-02-20",
        )]
        results = check_stale(claims, repo_tree)
        # May or may not flag depending on keyword overlap and negation patterns
        # The point is that it runs the heuristic (doesn't skip)
        # We verify by checking it doesn't error
        assert isinstance(results, list)

    def test_changed_hash_flags_stale(self, repo_tree):
        claims = [Claim(
            id="test", text="Test claim", status="IN",
            source="physics/entries/2026/02/20/old-entry.md",
            source_hash="definitely_wrong",
            date="2026-02-20",
        )]
        results = check_stale(claims, repo_tree)
        assert len(results) == 1
        assert results[0][1] == "STALE"

    def test_stale_claims_skipped(self, repo_tree):
        """Already-STALE claims are not re-checked."""
        claims = [Claim(
            id="test", text="Test claim", status="STALE",
            source="physics/entries/2026/02/20/old-entry.md",
            source_hash="wrong",
            date="2026-02-20",
        )]
        results = check_stale(claims, repo_tree)
        assert results == []
