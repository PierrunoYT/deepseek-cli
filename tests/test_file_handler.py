"""Tests for the file attachment feature."""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest

try:
    from handlers import file_handler as fh_mod
    from handlers.file_handler import FileHandler
    from handlers.command_handler import CommandHandler
except ImportError:
    from src.handlers import file_handler as fh_mod
    from src.handlers.file_handler import FileHandler
    from src.handlers.command_handler import CommandHandler


# ===========================================================================
# FileHandler.attach
# ===========================================================================


class TestFileHandlerAttach:
    def test_attach_single_file(self, tmp_path):
        f = tmp_path / "a.txt"
        f.write_text("hello", encoding="utf-8")

        fh = FileHandler()
        attached, errors = fh.attach(str(f))

        assert attached == [os.path.abspath(str(f))]
        assert errors == []
        assert len(fh.list_attachments()) == 1
        assert fh.attached_files[0]["content"] == "hello"
        assert fh.attached_files[0]["size"] == 5

    def test_attach_glob_pattern(self, tmp_path):
        (tmp_path / "x.py").write_text("# x", encoding="utf-8")
        (tmp_path / "y.py").write_text("# y", encoding="utf-8")
        (tmp_path / "z.txt").write_text("not py", encoding="utf-8")

        fh = FileHandler()
        attached, errors = fh.attach(str(tmp_path / "*.py"))

        assert len(attached) == 2
        assert errors == []
        names = sorted(os.path.basename(p) for p in attached)
        assert names == ["x.py", "y.py"]

    def test_attach_nonexistent_returns_error(self, tmp_path):
        fh = FileHandler()
        attached, errors = fh.attach(str(tmp_path / "nope.txt"))
        assert attached == []
        assert len(errors) == 1
        assert "No files matching" in errors[0]

    def test_attach_directory_skipped(self, tmp_path):
        sub = tmp_path / "subdir"
        sub.mkdir()
        fh = FileHandler()
        attached, errors = fh.attach(str(sub))
        assert attached == []
        assert any("Skipping directory" in e for e in errors)

    def test_attach_binary_extension_rejected(self, tmp_path):
        f = tmp_path / "image.png"
        f.write_bytes(b"\x89PNG\r\n\x1a\n")
        fh = FileHandler()
        attached, errors = fh.attach(str(f))
        assert attached == []
        assert any("Binary file rejected" in e for e in errors)

    def test_attach_non_utf8_rejected(self, tmp_path):
        f = tmp_path / "weird.dat"
        f.write_bytes(b"\xff\xfe\x00\x01\x02")
        fh = FileHandler()
        attached, errors = fh.attach(str(f))
        assert attached == []
        assert any("Not a UTF-8" in e for e in errors)

    def test_attach_too_large_rejected(self, tmp_path, monkeypatch):
        # Patch size limit down for the test
        monkeypatch.setattr(fh_mod, "MAX_FILE_SIZE", 10, raising=False)

        f = tmp_path / "big.txt"
        f.write_text("x" * 100, encoding="utf-8")
        fh = FileHandler()
        attached, errors = fh.attach(str(f))
        assert attached == []
        assert any("File too large" in e for e in errors)

    def test_duplicate_path_rejected(self, tmp_path):
        f = tmp_path / "a.txt"
        f.write_text("hi", encoding="utf-8")
        fh = FileHandler()
        fh.attach(str(f))
        attached, errors = fh.attach(str(f))
        assert attached == []
        assert any("Already attached" in e for e in errors)

    def test_max_files_cap(self, tmp_path, monkeypatch):
        monkeypatch.setattr(fh_mod, "MAX_FILES", 2, raising=False)

        for i in range(5):
            (tmp_path / f"f{i}.txt").write_text("x", encoding="utf-8")

        fh = FileHandler()
        attached, errors = fh.attach(str(tmp_path / "*.txt"))
        assert len(attached) == 2
        assert any("Maximum" in e for e in errors)


# ===========================================================================
# FileHandler bookkeeping
# ===========================================================================


class TestFileHandlerBookkeeping:
    def test_clear_resets_state(self, tmp_path):
        f = tmp_path / "a.txt"
        f.write_text("hi", encoding="utf-8")
        fh = FileHandler()
        fh.attach(str(f))
        assert fh.has_attachments()
        fh.clear()
        assert not fh.has_attachments()
        assert fh.total_size() == 0

    def test_remove_by_index(self, tmp_path):
        for n in ("a.txt", "b.txt"):
            (tmp_path / n).write_text("x", encoding="utf-8")
        fh = FileHandler()
        fh.attach(str(tmp_path / "*.txt"))
        assert len(fh.list_attachments()) == 2

        assert fh.remove("0") is True
        assert len(fh.list_attachments()) == 1

    def test_remove_by_path(self, tmp_path):
        f = tmp_path / "only.txt"
        f.write_text("x", encoding="utf-8")
        fh = FileHandler()
        fh.attach(str(f))
        assert fh.remove(str(f)) is True
        assert not fh.has_attachments()

    def test_remove_unknown_returns_false(self, tmp_path):
        fh = FileHandler()
        assert fh.remove("nope") is False
        assert fh.remove("999") is False


# ===========================================================================
# format_for_message
# ===========================================================================


class TestFormatForMessage:
    def test_no_files_returns_input_unchanged(self):
        fh = FileHandler()
        assert fh.format_for_message("hi") == "hi"

    def test_includes_each_file_with_markers(self, tmp_path):
        f1 = tmp_path / "one.txt"
        f1.write_text("ALPHA", encoding="utf-8")
        f2 = tmp_path / "two.txt"
        f2.write_text("BETA", encoding="utf-8")
        fh = FileHandler()
        fh.attach(str(f1))
        fh.attach(str(f2))

        out = fh.format_for_message("summarize these")
        assert "ALPHA" in out
        assert "BETA" in out
        assert "--- File:" in out
        assert "--- End of file:" in out
        assert "summarize these" in out
        assert out.count("--- File:") == 2


# ===========================================================================
# CommandHandler integration
# ===========================================================================


def _make_command_handler():
    api_client = MagicMock()
    chat_handler = MagicMock()
    fh = FileHandler()
    return CommandHandler(api_client, chat_handler, fh), fh


class TestCommandHandlerFileCommands:
    def test_files_when_empty(self):
        ch, _ = _make_command_handler()
        cont, msg = ch.handle_command("/files")
        assert cont is True
        assert "No files attached" in msg

    def test_file_without_args_shows_usage(self):
        ch, _ = _make_command_handler()
        cont, msg = ch.handle_command("/file")
        assert cont is True
        assert "Usage:" in msg

    def test_file_attaches(self, tmp_path):
        f = tmp_path / "code.py"
        f.write_text("print('hi')", encoding="utf-8")
        ch, fh = _make_command_handler()
        cont, msg = ch.handle_command(f"/file {f}")
        assert cont is True
        assert "Attached 1 file(s)" in msg
        assert len(fh.list_attachments()) == 1

    def test_file_glob_expands(self, tmp_path):
        for n in ("a.py", "b.py"):
            (tmp_path / n).write_text("x", encoding="utf-8")
        ch, fh = _make_command_handler()
        cont, msg = ch.handle_command(f"/file {tmp_path / '*.py'}")
        assert cont is True
        assert len(fh.list_attachments()) == 2

    def test_file_multiple_paths(self, tmp_path):
        f1 = tmp_path / "a.txt"
        f1.write_text("A", encoding="utf-8")
        f2 = tmp_path / "b.txt"
        f2.write_text("B", encoding="utf-8")
        ch, fh = _make_command_handler()
        cont, msg = ch.handle_command(f"/file {f1} {f2}")
        assert cont is True
        assert len(fh.list_attachments()) == 2

    def test_files_lists_attachments(self, tmp_path):
        f = tmp_path / "code.py"
        f.write_text("x", encoding="utf-8")
        ch, fh = _make_command_handler()
        ch.handle_command(f"/file {f}")
        cont, msg = ch.handle_command("/files")
        assert cont is True
        assert "Attached files" in msg
        assert str(f.resolve()) in msg or os.path.abspath(str(f)) in msg

    def test_clearfiles_clears(self, tmp_path):
        f = tmp_path / "code.py"
        f.write_text("x", encoding="utf-8")
        ch, fh = _make_command_handler()
        ch.handle_command(f"/file {f}")
        assert fh.has_attachments()
        cont, msg = ch.handle_command("/clearfiles")
        assert cont is True
        assert "Cleared 1" in msg
        assert not fh.has_attachments()

    def test_dropfile_by_index(self, tmp_path):
        f = tmp_path / "code.py"
        f.write_text("x", encoding="utf-8")
        ch, fh = _make_command_handler()
        ch.handle_command(f"/file {f}")
        cont, msg = ch.handle_command("/dropfile 0")
        assert cont is True
        assert "Removed attachment" in msg
        assert not fh.has_attachments()

    def test_dropfile_unknown_fails_gracefully(self):
        ch, _ = _make_command_handler()
        cont, msg = ch.handle_command("/dropfile 99")
        assert cont is True
        assert "No attachment matching" in msg

    def test_help_includes_file_commands(self):
        ch, _ = _make_command_handler()
        cont, msg = ch.handle_command("/help")
        assert cont is True
        assert "/file" in msg
        assert "/pick" in msg
        assert "/files" in msg
        assert "/clearfiles" in msg
