"""Tests for deprecation notices when ftl-reasons is installed."""

from unittest.mock import patch

from beliefs_lib.cli import _reasons_deprecation_notice, _DEPRECATED_COMMANDS


class TestDeprecationNotice:
    """Deprecation notice prints only when reasons CLI is on PATH."""

    @patch("beliefs_lib.cli.shutil.which", return_value="/usr/local/bin/reasons")
    def test_notice_when_reasons_installed(self, mock_which, capsys):
        _reasons_deprecation_notice("add")
        assert "deprecated" in capsys.readouterr().err

    @patch("beliefs_lib.cli.shutil.which", return_value=None)
    def test_no_notice_when_reasons_absent(self, mock_which, capsys):
        _reasons_deprecation_notice("add")
        assert capsys.readouterr().err == ""

    @patch("beliefs_lib.cli.shutil.which", return_value="/usr/local/bin/reasons")
    def test_no_notice_for_non_deprecated_command(self, mock_which, capsys):
        _reasons_deprecation_notice("list")
        assert capsys.readouterr().err == ""

    @patch("beliefs_lib.cli.shutil.which", return_value="/usr/local/bin/reasons")
    def test_notice_suggests_replacement(self, mock_which, capsys):
        _reasons_deprecation_notice("check-stale")
        err = capsys.readouterr().err
        assert "reasons check-stale" in err

    def test_all_deprecated_commands_have_replacements(self):
        expected = {"add", "add-batch", "update", "check-stale", "hash-sources"}
        assert set(_DEPRECATED_COMMANDS.keys()) == expected
