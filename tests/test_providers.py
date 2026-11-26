"""A missing API key must give a clear message, not a traceback."""
import os

import pytest

from incident_triage import cli
from incident_triage.llm import LLMError, get_provider


@pytest.fixture
def no_credentials(monkeypatch, tmp_path):
    for name in list(os.environ):
        if name.startswith(("ANTHROPIC_", "GEMINI_", "GOOGLE_")):
            monkeypatch.delenv(name)
    # Hide any saved login profile on this machine.
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    return tmp_path


@pytest.mark.parametrize("name", ["anthropic", "google"])
def test_missing_key_raises_llm_error(no_credentials, name):
    with pytest.raises(LLMError, match="API_KEY"):
        get_provider(name)


@pytest.mark.parametrize("name", ["anthropic", "google"])
def test_missing_key_gives_exit_code_3(no_credentials, name, capsys):
    log = no_credentials / "sample.log"
    log.write_text("081109 203615 148 WARN dfs.DataNode: boom\n", encoding="utf-8")
    assert cli.main([str(log), "--provider", name]) == cli.EXIT_LLM
    assert "error: triage failed" in capsys.readouterr().err
