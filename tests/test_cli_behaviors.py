"""Focused tests for patched CLI behaviors.

Covers:
  - Error handler: SDK metadata preservation, rate-limit single-sleep,
    auth recovery retry, non-retryable path.
  - Chat handler: prefix mode does not mutate self.messages,
    raw mode suppresses panel, JSON mode sets system message.
  - Command handler: /history, /fim, /cache, /balance, and help text alignment.
  - CLI: --no-stream flag, prepare_chat_request called fresh on retry.
"""

import sys
import os
import time
import types
import unittest
from unittest.mock import MagicMock, patch, call

# ---------------------------------------------------------------------------
# Ensure src is importable when running from project root
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from config.settings import DEFAULT_RETRY_DELAY, DEFAULT_MAX_RETRY_DELAY
from utils.exceptions import DeepSeekError
from handlers.error_handler import ErrorHandler
from handlers.chat_handler import ChatHandler
from handlers.command_handler import CommandHandler


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_openai_error(cls, status_code=None, headers=None, code=None, message="err"):
    """Create a minimal OpenAI SDK error with the given attributes."""
    err = cls.__new__(cls)
    Exception.__init__(err, message)
    err.status_code = status_code
    err.headers = headers or {}
    err.code = code
    err.message = message
    return err


def _make_api_client_mock():
    client = MagicMock()
    client.beta_mode = False
    return client


def _make_chat_handler():
    with patch("handlers.chat_handler.check_version", return_value=(False, "1.0.0", "1.0.0")):
        return ChatHandler(stream=False)


def _make_command_handler():
    api_client = _make_api_client_mock()
    chat_handler = _make_chat_handler()
    return CommandHandler(api_client, chat_handler), api_client, chat_handler


# ---------------------------------------------------------------------------
# ErrorHandler tests
# ---------------------------------------------------------------------------

class TestErrorHandlerMetadataPreservation(unittest.TestCase):
    """SDK error metadata (status_code, code, headers) must survive through handle_error."""

    def setUp(self):
        self.eh = ErrorHandler(max_retries=1)
        self.eh.console = MagicMock()

    def test_rate_limit_reads_retry_after_header(self):
        from openai import RateLimitError
        err = _make_openai_error(RateLimitError, status_code=429, headers={"retry-after": "7"})
        with patch("handlers.error_handler.time.sleep") as mock_sleep:
            result = self.eh.handle_error(err)
        mock_sleep.assert_called_once_with(7)
        self.assertEqual(result, "retry")

    def test_rate_limit_falls_back_to_default_when_no_header(self):
        from openai import RateLimitError
        err = _make_openai_error(RateLimitError, status_code=429, headers={})
        with patch("handlers.error_handler.time.sleep") as mock_sleep:
            result = self.eh.handle_error(err)
        mock_sleep.assert_called_once_with(DEFAULT_RETRY_DELAY)
        self.assertEqual(result, "retry")

    def test_rate_limit_by_status_code_only(self):
        """status_code==429 on a plain Exception still triggers rate-limit path."""
        from openai import APIError
        err = _make_openai_error(APIError, status_code=429, headers={"retry-after": "3"})
        with patch("handlers.error_handler.time.sleep") as mock_sleep:
            result = self.eh.handle_error(err)
        mock_sleep.assert_called_once_with(3)
        self.assertEqual(result, "retry")

    def test_auth_error_no_client_returns_none(self):
        from openai import AuthenticationError
        err = _make_openai_error(AuthenticationError, status_code=401)
        result = self.eh.handle_error(err, api_client=None)
        self.assertIsNone(result)

    def test_auth_error_with_client_user_accepts_returns_retry(self):
        from openai import AuthenticationError
        err = _make_openai_error(AuthenticationError, status_code=401)
        api_client = MagicMock()
        with patch("builtins.input", side_effect=["y", "new-key-abc"]):
            result = self.eh.handle_error(err, api_client=api_client)
        self.assertEqual(result, "retry")
        api_client.update_api_key.assert_called_once_with("new-key-abc")

    def test_auth_error_with_client_user_declines_returns_none(self):
        from openai import AuthenticationError
        err = _make_openai_error(AuthenticationError, status_code=401)
        api_client = MagicMock()
        with patch("builtins.input", return_value="n"):
            result = self.eh.handle_error(err, api_client=api_client)
        self.assertIsNone(result)

    def test_unknown_error_code_displayed(self):
        from openai import APIError
        err = _make_openai_error(APIError, status_code=418, code="teapot")
        self.eh.handle_error(err)
        # Should mention the error code in output
        printed = " ".join(str(c) for c in self.eh.console.print.call_args_list)
        self.assertIn("teapot", printed)


class TestRetryWithBackoff(unittest.TestCase):
    """retry_with_backoff must not double-sleep on RateLimitError."""

    def setUp(self):
        self.eh = ErrorHandler(max_retries=3)
        self.eh.console = MagicMock()

    def test_rate_limit_no_extra_sleep(self):
        from openai import RateLimitError
        call_count = 0

        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise _make_openai_error(RateLimitError, status_code=429, headers={"retry-after": "1"})
            return "ok"

        sleep_calls = []
        with patch("handlers.error_handler.time.sleep", side_effect=lambda s: sleep_calls.append(s)):
            result = self.eh.retry_with_backoff(flaky)

        self.assertEqual(result, "ok")
        # Each rate-limit sleep is exactly 1s from the header; no extra backoff sleeps
        self.assertEqual(sleep_calls, [1, 1])

    def test_non_rate_limit_server_error_applies_backoff(self):
        from openai import APIError
        call_count = 0

        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise _make_openai_error(APIError, status_code=500)
            return "ok"

        sleep_calls = []
        with patch("handlers.error_handler.time.sleep", side_effect=lambda s: sleep_calls.append(s)):
            with patch("builtins.input", return_value="y"):
                result = self.eh.retry_with_backoff(flaky)

        self.assertEqual(result, "ok")
        # Backoff sleeps should be present (exponential)
        self.assertTrue(len(sleep_calls) > 0)

    def test_max_retries_exceeded_re_raises(self):
        from openai import RateLimitError

        def always_fail():
            raise _make_openai_error(RateLimitError, status_code=429, headers={})

        with patch("handlers.error_handler.time.sleep"):
            with self.assertRaises(Exception):
                self.eh.retry_with_backoff(always_fail)


# ---------------------------------------------------------------------------
# ChatHandler tests
# ---------------------------------------------------------------------------

class TestPrefixModeNoMutation(unittest.TestCase):
    """prepare_chat_request must not mutate self.messages in prefix mode."""

    def setUp(self):
        self.ch = _make_chat_handler()
        self.ch.prefix_mode = True

    def test_prefix_mode_does_not_mutate_messages(self):
        self.ch.messages = [{"role": "user", "content": "Hello"}]
        original_messages = [m.copy() for m in self.ch.messages]

        kwargs = self.ch.prepare_chat_request()

        # self.messages must be unchanged
        self.assertEqual(self.ch.messages, original_messages)

        # The API messages list must have the prefix-transformed message
        api_msgs = kwargs["messages"]
        self.assertEqual(len(api_msgs), 1)
        self.assertEqual(api_msgs[0]["role"], "assistant")
        self.assertEqual(api_msgs[0]["content"], "Hello")
        self.assertTrue(api_msgs[0].get("prefix"))

    def test_prefix_mode_off_passes_messages_unchanged(self):
        self.ch.prefix_mode = False
        self.ch.messages = [{"role": "user", "content": "Hi"}]
        kwargs = self.ch.prepare_chat_request()
        self.assertIs(kwargs["messages"], self.ch.messages)

    def test_prefix_not_applied_when_last_message_is_not_user(self):
        self.ch.prefix_mode = True
        self.ch.messages = [{"role": "assistant", "content": "I said something"}]
        kwargs = self.ch.prepare_chat_request()
        # Should pass through unchanged — last msg is assistant, not user
        self.assertEqual(kwargs["messages"][0]["role"], "assistant")
        self.assertNotIn("prefix", kwargs["messages"][0])

    def test_repeated_prepare_chat_request_is_idempotent(self):
        """Calling prepare_chat_request multiple times (as in retries) must give same result."""
        self.ch.messages = [{"role": "user", "content": "Retry me"}]
        kwargs1 = self.ch.prepare_chat_request()
        kwargs2 = self.ch.prepare_chat_request()
        self.assertEqual(kwargs1["messages"], kwargs2["messages"])


class TestRawModeHandleResponse(unittest.TestCase):
    """raw_mode=True must suppress the reasoning panel; content panel always printed."""

    def setUp(self):
        self.ch = _make_chat_handler()

    def _make_response(self, content="answer", reasoning=None):
        response = MagicMock()
        response.usage = MagicMock()
        response.usage.model_dump.return_value = {
            "prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15
        }
        choice = MagicMock()
        msg = MagicMock()
        msg.content = content
        msg.tool_calls = None
        msg.reasoning_content = reasoning
        choice.message = msg
        response.choices = [choice]
        return response

    def test_raw_mode_suppresses_reasoning_panel(self):
        self.ch.raw_mode = True
        self.ch.stream = False
        response = self._make_response(content="result", reasoning="thought process")
        with patch.object(self.ch.console, "print") as mock_print:
            result = self.ch.handle_response(response)
        self.assertEqual(result, "result")
        # No Panel containing "Chain of Thought" should have been printed
        for c in mock_print.call_args_list:
            arg = c[0][0] if c[0] else ""
            if hasattr(arg, "title"):  # rich Panel
                self.assertNotIn("Chain of Thought", str(arg.title))

    def test_non_raw_mode_shows_reasoning_panel(self):
        self.ch.raw_mode = False
        self.ch.stream = False
        response = self._make_response(content="result", reasoning="thought process")
        panel_titles = []
        original_print = self.ch.console.print

        def capture_print(*args, **kwargs):
            for a in args:
                if hasattr(a, "title"):
                    panel_titles.append(str(a.title))

        with patch.object(self.ch.console, "print", side_effect=capture_print):
            self.ch.handle_response(response)

        self.assertTrue(any("Chain of Thought" in t for t in panel_titles))


class TestJsonModeSystemMessage(unittest.TestCase):
    def setUp(self):
        self.ch = _make_chat_handler()

    def test_toggle_json_mode_on_sets_json_system_message(self):
        self.ch.toggle_json_mode()
        self.assertTrue(self.ch.json_mode)
        self.assertIn("JSON", self.ch.messages[0]["content"])

    def test_toggle_json_mode_off_restores_default_system_message(self):
        self.ch.toggle_json_mode()
        self.ch.toggle_json_mode()
        self.assertFalse(self.ch.json_mode)
        self.assertEqual(self.ch.messages[0]["content"], "You are a helpful assistant.")


# ---------------------------------------------------------------------------
# CommandHandler tests — advertised commands
# ---------------------------------------------------------------------------

class TestCommandHandlerAdvertisedCommands(unittest.TestCase):

    def setUp(self):
        self.cmd, self.api_client, self.chat_handler = _make_command_handler()

    # /history
    def test_history_empty(self):
        self.chat_handler.messages = []
        ok, msg = self.cmd.handle_command("/history")
        self.assertTrue(ok)
        self.assertIn("No conversation history", msg)

    def test_history_shows_messages(self):
        self.chat_handler.messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        ok, msg = self.cmd.handle_command("/history")
        self.assertTrue(ok)
        self.assertIn("User", msg)
        self.assertIn("Hello", msg)
        self.assertIn("Assistant", msg)
        self.assertIn("Hi there", msg)

    def test_history_truncates_long_content(self):
        long_content = "x" * 300
        self.chat_handler.messages = [{"role": "user", "content": long_content}]
        ok, msg = self.cmd.handle_command("/history")
        self.assertTrue(ok)
        self.assertIn("...", msg)

    # /fim
    def test_fim_toggle_on(self):
        self.chat_handler.fim_mode = False
        ok, msg = self.cmd.handle_command("/fim")
        self.assertTrue(ok)
        self.assertIn("enabled", msg)
        self.assertTrue(self.chat_handler.fim_mode)

    def test_fim_toggle_off(self):
        self.chat_handler.fim_mode = True
        ok, msg = self.cmd.handle_command("/fim")
        self.assertTrue(ok)
        self.assertIn("disabled", msg)
        self.assertFalse(self.chat_handler.fim_mode)

    # /cache
    def test_cache_informs_automatic(self):
        ok, msg = self.cmd.handle_command("/cache")
        self.assertTrue(ok)
        self.assertIn("automatic", msg.lower())

    # /balance
    def test_balance_provides_instructions(self):
        ok, msg = self.cmd.handle_command("/balance")
        self.assertTrue(ok)
        self.assertIn("platform.deepseek.com", msg)

    # /help mentions all advertised commands
    def test_help_mentions_fim(self):
        ok, msg = self.cmd.handle_command("/help")
        self.assertIn("/fim", msg)

    def test_help_mentions_history(self):
        ok, msg = self.cmd.handle_command("/help")
        self.assertIn("/history", msg)

    def test_help_mentions_balance(self):
        ok, msg = self.cmd.handle_command("/help")
        self.assertIn("/balance", msg)

    def test_help_mentions_cache(self):
        ok, msg = self.cmd.handle_command("/help")
        self.assertIn("/cache", msg)

    # existing commands still work
    def test_clear_command(self):
        self.chat_handler.messages = [{"role": "user", "content": "hi"}]
        ok, msg = self.cmd.handle_command("/clear")
        self.assertTrue(ok)
        self.assertEqual(self.chat_handler.messages, [])

    def test_json_toggle(self):
        ok, msg = self.cmd.handle_command("/json")
        self.assertTrue(ok)
        self.assertIn("JSON mode", msg)

    def test_prefix_toggle(self):
        ok, msg = self.cmd.handle_command("/prefix")
        self.assertTrue(ok)
        self.assertIn("Prefix mode", msg)

    def test_unknown_command_returns_none_none(self):
        result = self.cmd.handle_command("/nonexistent")
        self.assertEqual(result, (None, None))

    # /system
    def test_system_set_updates_message(self):
        ok, msg = self.cmd.handle_command("/system You are a pirate.")
        self.assertTrue(ok)
        self.assertIn("You are a pirate.", msg)
        self.assertEqual(self.chat_handler.messages[0]["content"], "You are a pirate.")

    def test_system_set_with_no_content_shows_current(self):
        # "/system " (trailing space) strips to "/system" → shows current message
        self.chat_handler.set_system_message("Initial message.")
        ok, msg = self.cmd.handle_command("/system ")
        self.assertTrue(ok)
        self.assertIn("Current system message", msg)

    def test_system_show_current(self):
        self.chat_handler.set_system_message("Be concise.")
        ok, msg = self.cmd.handle_command("/system")
        self.assertTrue(ok)
        self.assertIn("Be concise.", msg)

    def test_system_show_none_when_no_system_message(self):
        self.chat_handler.messages = []
        ok, msg = self.cmd.handle_command("/system")
        self.assertTrue(ok)
        self.assertIn("(none)", msg)

    def test_help_mentions_system(self):
        ok, msg = self.cmd.handle_command("/help")
        self.assertIn("/system", msg)


# ---------------------------------------------------------------------------
# CLI argument tests — --no-stream flag
# ---------------------------------------------------------------------------

class TestCLIArguments(unittest.TestCase):

    def _parse(self, args):
        # pyfiglet is an optional dependency for the fancy banner; stub it out
        # so the CLI module can be imported even when it is not installed.
        import sys as _sys
        pyfiglet_stub = types.ModuleType("pyfiglet")
        pyfiglet_stub.Figlet = MagicMock(return_value=MagicMock(renderText=MagicMock(return_value="")))
        with patch.dict(_sys.modules, {"pyfiglet": pyfiglet_stub}):
            with patch("sys.argv", ["deepseek"] + args):
                import importlib
                import cli.deepseek_cli as _m
                importlib.reload(_m)
                return _m.parse_arguments()

    def test_stream_flag_sets_true(self):
        args = self._parse(["-s"])
        self.assertTrue(args.stream)

    def test_no_stream_flag_sets_false(self):
        args = self._parse(["--no-stream"])
        self.assertFalse(args.stream)

    def test_default_stream_is_false(self):
        args = self._parse([])
        self.assertFalse(args.stream)

    def test_query_model_raw_flags(self):
        args = self._parse(["-q", "hello", "-m", "deepseek-chat", "-r"])
        self.assertEqual(args.query, "hello")
        self.assertEqual(args.model, "deepseek-chat")
        self.assertTrue(args.raw)

    def test_system_flag_long(self):
        args = self._parse(["--system", "You are a pirate."])
        self.assertEqual(args.system, "You are a pirate.")

    def test_system_flag_short(self):
        args = self._parse(["-S", "Be concise."])
        self.assertEqual(args.system, "Be concise.")

    def test_system_flag_default(self):
        args = self._parse([])
        self.assertEqual(args.system, "You are a helpful assistant.")


if __name__ == "__main__":
    unittest.main()
