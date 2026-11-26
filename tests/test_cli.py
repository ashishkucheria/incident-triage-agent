"""Tests for the command line: arguments, errors and exit codes."""
import pytest

from incident_triage import cli

LINE = "081109 203615 148 WARN dfs.DataNode: Got exception while serving blk_1 to /10.0.0.1:\n"


@pytest.fixture
def logfile(tmp_path, monkeypatch):
    # Never read the developer's real .env during tests.
    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    path = tmp_path / "sample.log"
    path.write_text(LINE, encoding="utf-8")
    return path


def test_no_llm_run_succeeds(logfile):
    assert cli.main([str(logfile), "--no-llm"]) == cli.EXIT_OK


def test_missing_file_is_a_usage_error(logfile):
    assert cli.main([str(logfile) + ".missing", "--no-llm"]) == cli.EXIT_USAGE


@pytest.mark.parametrize("top", ["0", "-1", "abc"])
def test_top_must_be_positive(logfile, top, capsys):
    with pytest.raises(SystemExit) as exit_info:
        cli.main([str(logfile), "--no-llm", "--top", top])
    assert exit_info.value.code == cli.EXIT_USAGE
    assert "1 or more" in capsys.readouterr().err
