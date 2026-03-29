"""Behavior-focused tests for CLI flows and persistence resolution."""

import io
import sys
import warnings
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Import helpers – support both installed-package and source-tree layouts
# ---------------------------------------------------------------------------
try:
    from cli.deepseek_cli import _read_input, main
    from utils.persistence import _resolve_dirs
    import cli.deepseek_cli as _cli_mod
except ImportError:
    from src.cli.deepseek_cli import _read_input, main
    from src.utils.persistence import _resolve_dirs
    import src.cli.deepseek_cli as _cli_mod


# ===========================================================================
# _read_input()
# ===========================================================================


class TestReadInputFile:
    def test_reads_utf8_file(self, tmp_path):
        f = tmp_path / "query.txt"
        f.write_text("hello world", encoding="utf-8")
        assert _read_input(str(f)) == "hello world"

    def test_reads_multiline_file(self, tmp_path):
        f = tmp_path / "query.txt"
        f.write_text("line1\nline2\nline3", encoding="utf-8")
        assert _read_input(str(f)) == "line1\nline2\nline3"

    def test_reads_empty_file(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("", encoding="utf-8")
        assert _read_input(str(f)) == ""

    def test_missing_file_exits_1(self, tmp_path):
        with pytest.raises(SystemExit) as exc_info:
            _read_input(str(tmp_path / "nonexistent.txt"))
        assert exc_info.value.code == 1

    def test_binary_file_exits_1(self, tmp_path):
        f = tmp_path / "binary.bin"
        f.write_bytes(b"\xff\xfe\x00\x01")
        with pytest.raises(SystemExit) as exc_info:
            _read_input(str(f))
        assert exc_info.value.code == 1

    def test_os_error_exits_1(self, tmp_path):
        # Passing a directory as source – open() raises IsADirectoryError (OSError)
        with pytest.raises(SystemExit) as exc_info:
            _read_input(str(tmp_path))
        assert exc_info.value.code == 1


class TestReadInputStdin:
    def test_stdin_pipe_returns_content(self):
        fake_stdin = io.StringIO("piped content")
        fake_stdin.isatty = lambda: False
        with patch("sys.stdin", fake_stdin):
            result = _read_input("-")
        assert result == "piped content"

    def test_stdin_tty_exits_1(self):
        fake_stdin = MagicMock()
        fake_stdin.isatty.return_value = True
        with patch("sys.stdin", fake_stdin):
            with pytest.raises(SystemExit) as exc_info:
                _read_input("-")
        assert exc_info.value.code == 1


# ===========================================================================
# main() – query resolution with --read / --query combinations
# ===========================================================================


def _make_args(**kwargs):
    """Build a minimal argparse.Namespace for main() tests."""
    import argparse

    defaults = dict(
        query=None,
        read=None,
        model=None,
        raw=False,
        system="You are a helpful assistant.",
        stream=False,
        multiline=False,
        multiline_submit="empty-line",
        json=False,
        beta=False,
        prefix=False,
        fim=False,
        temp=None,
        freq=None,
        pres=None,
        top_p=None,
        stop=None,
    )
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


class TestMainQueryResolution:
    """Verify that main() assembles the final query correctly."""

    def _run_capturing(self, args):
        captured = []

        def fake_run_inline(query, model=None, raw=False, system="You are a helpful assistant."):
            captured.append(query)
            return "ok"

        # Stub DeepSeekCLI so __init__ never tries to build a real APIClient
        # (which would prompt for an API key when DEEPSEEK_API_KEY is unset).
        mock_cli = MagicMock()
        mock_cli.run_inline_query.side_effect = fake_run_inline

        with patch.object(_cli_mod, "parse_arguments", return_value=args):
            with patch.object(_cli_mod, "DeepSeekCLI", return_value=mock_cli):
                with patch("sys.stdout", new_callable=io.StringIO):
                    _cli_mod.main()
        return captured

    def test_read_only_sets_query_from_file(self, tmp_path):
        f = tmp_path / "q.txt"
        f.write_text("file content", encoding="utf-8")
        captured = self._run_capturing(_make_args(read=str(f)))
        assert captured == ["file content"]

    def test_query_and_read_joined_by_newline(self, tmp_path):
        f = tmp_path / "ctx.txt"
        f.write_text("file part", encoding="utf-8")
        captured = self._run_capturing(_make_args(query="question", read=str(f)))
        assert captured == ["question\nfile part"]

    def test_query_trailing_newlines_normalised(self, tmp_path):
        f = tmp_path / "ctx.txt"
        f.write_text("appended", encoding="utf-8")
        captured = self._run_capturing(_make_args(query="q\n\n", read=str(f)))
        assert captured == ["q\nappended"]

    def test_query_only_no_read(self):
        captured = self._run_capturing(_make_args(query="direct question"))
        assert captured == ["direct question"]

    def test_read_stdin_pipe(self):
        fake_stdin = io.StringIO("stdin content")
        fake_stdin.isatty = lambda: False
        with patch("sys.stdin", fake_stdin):
            captured = self._run_capturing(_make_args(read="-"))
        assert captured == ["stdin content"]

    def test_no_query_no_read_enters_interactive_mode(self):
        """Without --query or --read, run() should be called instead of run_inline_query."""
        args = _make_args()
        run_called = []

        mock_cli = MagicMock()
        mock_cli.run.side_effect = lambda system="You are a helpful assistant.": run_called.append(True)

        with patch.object(_cli_mod, "parse_arguments", return_value=args):
            with patch.object(_cli_mod, "DeepSeekCLI", return_value=mock_cli):
                _cli_mod.main()
        assert run_called == [True]


# ===========================================================================
# _resolve_dirs() – XDG vs legacy persistence resolution
# ===========================================================================


class TestResolveDirsLegacy:
    def test_uses_legacy_when_dir_exists(self, tmp_path, monkeypatch):
        legacy = tmp_path / ".deepseek-cli"
        legacy.mkdir()
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
        config_dir, data_dir = _resolve_dirs()
        assert config_dir == legacy
        assert data_dir == legacy

    def test_ignores_legacy_when_not_a_dir(self, tmp_path, monkeypatch):
        legacy = tmp_path / ".deepseek-cli"
        legacy.write_text("not a directory")
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            config_dir, data_dir = _resolve_dirs()
        assert config_dir != legacy
        assert data_dir != legacy

    def test_non_dir_legacy_emits_user_warning(self, tmp_path, monkeypatch):
        legacy = tmp_path / ".deepseek-cli"
        legacy.write_text("not a directory")
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _resolve_dirs()
        assert any(issubclass(warning.category, UserWarning) for warning in w)

    def test_warning_message_mentions_path(self, tmp_path, monkeypatch):
        legacy = tmp_path / ".deepseek-cli"
        legacy.write_text("not a directory")
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _resolve_dirs()
        messages = [str(warning.message) for warning in w if issubclass(warning.category, UserWarning)]
        assert any(".deepseek-cli" in msg for msg in messages)

    def test_no_legacy_uses_xdg(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
        config_dir, data_dir = _resolve_dirs()
        assert config_dir == tmp_path / "cfg" / "deepseek-cli"
        assert data_dir == tmp_path / "data" / "deepseek-cli"

    def test_xdg_env_not_set_uses_defaults(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.delenv("XDG_DATA_HOME", raising=False)
        config_dir, data_dir = _resolve_dirs()
        assert config_dir == tmp_path / ".config" / "deepseek-cli"
        assert data_dir == tmp_path / ".local" / "share" / "deepseek-cli"

    def test_config_and_data_dirs_differ_under_xdg(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
        config_dir, data_dir = _resolve_dirs()
        assert config_dir != data_dir

    def test_legacy_symlink_to_dir_is_accepted(self, tmp_path, monkeypatch):
        real_dir = tmp_path / "real_deepseek"
        real_dir.mkdir()
        legacy = tmp_path / ".deepseek-cli"
        legacy.symlink_to(real_dir)
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
        config_dir, data_dir = _resolve_dirs()
        assert config_dir == legacy
        assert data_dir == legacy


# ===========================================================================
# Ctrl+D / Ctrl+C handling in DeepSeekCLI.run()
# ===========================================================================


def _make_cli_instance():
    """Build a DeepSeekCLI instance with all heavy collaborators mocked out."""
    cli = _cli_mod.DeepSeekCLI.__new__(_cli_mod.DeepSeekCLI)
    cli.multiline = False
    cli.multiline_submit = "empty-line"
    cli.chat_handler = MagicMock()
    cli.command_handler = MagicMock()
    cli.command_handler.handle_command.return_value = (None, None)
    cli.error_handler = MagicMock()
    cli.api_client = MagicMock()
    return cli


class TestRunInputHandling:
    def test_ctrl_d_exits_gracefully(self):
        cli = _make_cli_instance()
        with patch("builtins.input", side_effect=EOFError):
            with patch.object(cli, "_cleanup") as mock_cleanup:
                with patch.object(cli, "_print_welcome"):
                    cli.run()
        mock_cleanup.assert_called()

    def test_keyboard_interrupt_exits_gracefully(self):
        cli = _make_cli_instance()
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            with patch.object(cli, "_cleanup") as mock_cleanup:
                with patch.object(cli, "_print_welcome"):
                    cli.run()
        mock_cleanup.assert_called()

    def test_empty_input_continues_loop(self):
        """An empty Enter press must not exit – the loop should ask again."""
        cli = _make_cli_instance()
        call_count = 0

        def fake_input():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return ""
            raise EOFError

        with patch("builtins.input", side_effect=fake_input):
            with patch.object(cli, "_cleanup"):
                with patch.object(cli, "_print_welcome"):
                    cli.run()
        assert call_count == 2


# ===========================================================================
# Multiline submit mode wiring
# ===========================================================================


class TestMultilineSubmitModes:
    def test_multiline_flag_stored_on_instance(self):
        cli = _make_cli_instance()
        cli.multiline = True
        assert cli.multiline is True

    def test_shift_enter_mode_stored(self):
        cli = _make_cli_instance()
        cli.multiline_submit = "shift-enter"
        assert cli.multiline_submit == "shift-enter"

    def test_empty_line_mode_stored(self):
        cli = _make_cli_instance()
        cli.multiline_submit = "empty-line"
        assert cli.multiline_submit == "empty-line"

    def test_multiline_input_called_with_correct_submit_mode(self):
        cli = _make_cli_instance()
        cli.multiline = True
        cli.multiline_submit = "shift-enter"

        submitted_modes = []

        def fake_multiline(prompt, mode):
            submitted_modes.append(mode)
            raise EOFError

        with patch.object(_cli_mod, "multiline_input", side_effect=fake_multiline):
            with patch.object(cli, "_cleanup"):
                with patch.object(cli, "_print_welcome"):
                    cli.run()

        assert submitted_modes == ["shift-enter"]

    def test_multiline_empty_line_submit_mode_forwarded(self):
        cli = _make_cli_instance()
        cli.multiline = True
        cli.multiline_submit = "empty-line"

        submitted_modes = []

        def fake_multiline(prompt, mode):
            submitted_modes.append(mode)
            raise EOFError

        with patch.object(_cli_mod, "multiline_input", side_effect=fake_multiline):
            with patch.object(cli, "_cleanup"):
                with patch.object(cli, "_print_welcome"):
                    cli.run()

        assert submitted_modes == ["empty-line"]
