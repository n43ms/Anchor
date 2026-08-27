from pathlib import Path
from unittest.mock import patch

import pytest

from anchor.cli import main


def test_cli_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    with patch("sys.argv", ["anchor", "version"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "v1.5.1" in captured.out


def test_cli_status_flag(capsys: pytest.CaptureFixture[str]) -> None:
    with patch("sys.argv", ["anchor", "status"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "Healthy" in captured.out


def test_cli_init_command(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    with patch("sys.argv", ["anchor", "init"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
        assert (tmp_path / "docker-compose.yml").exists()
        assert (tmp_path / "app.py").exists()
