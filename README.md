# DeepSeek CLI

A powerful command-line interface for interacting with DeepSeek's AI models.

[@PierrunoYT/deepseek-cli](https://github.com/PierrunoYT/deepseek-cli)

## Features

- 🤖 Multiple Model Support
  - DeepSeek-V4-Flash (`deepseek-v4-flash`) - 284B total / 13B active
  - DeepSeek-V4-Pro (`deepseek-v4-pro`) - 1.6T total / 49B active
  - DeepSeek-V4-Flash-Vision (`deepseek-v4-flash-vision-exp`) - experimental
  - Thinking mode with Chain of Thought on any V4 model, via `/think`

- 🔄 Advanced Conversation Features
  - Multi-round conversations with context preservation
  - System message customization
  - **Conversation history persistence** across sessions
  - **Settings persistence** for model preferences and configurations
  - Context caching for better performance and cost savings
  - Inline mode for quick queries
  - **Pipe / file input** — feed queries from stdin or a file with `--read`
  - **File attachments for analysis** — attach one or more files (with glob support and an interactive picker) so the model can analyse them, mirroring the DeepSeek app's file-upload feature
  - **Multiline input support** for complex prompts
  - **XDG Base Directory** support for clean home directory layout
  - 1M context window for all models, up to 384K output tokens

- 🚀 Advanced Features
  - Prefix Completion: Complete assistant messages from a given prefix (Stable)
  - Fill-in-the-Middle (FIM): Complete content between a prefix and suffix (Stable)
  - Context Caching: Automatic disk-based caching with up to 90% cost savings
  - Anthropic API Compatibility: the DeepSeek *platform* accepts the Anthropic API format, so tools like Claude Code can point at it ([details below](#anthropic-api-compatibility)). This is a property of the API, not a mode of this CLI.

- 🛠️ Advanced Controls
  - Temperature control with presets
  - Thinking mode with selectable reasoning effort (low / high / max)
  - Configurable output token cap (`/maxtokens`, `--max-tokens`)
  - JSON output mode
  - Streaming responses (disabled by default; enable with `-s` / `--stream`)
  - Function calling (up to 128 functions)
  - Stop sequences
  - Top-p sampling

- 📦 Package Management
  - Automatic version checking (cached for 24 hours, so startup is not blocked on a network call)
  - Update notifications
  - Easy installation and updates
  - Development mode support

## Installation

You can install DeepSeek CLI in two ways:

### Option 1: Install from PyPI (Recommended)

```bash
pip install deepseek-cli
```

### Option 2: Install from Source (Development)

```bash
git clone https://github.com/PierrunoYT/deepseek-cli.git
cd deepseek-cli
pip install -e .
```

To run the test suite from a source checkout:

```bash
pip install pytest
pytest
```

The package lives in `src/deepseek_cli/`; a root `conftest.py` puts `src/` on `sys.path` so the tests run without installing first.

### Updating the Package

To update to the latest version:

```bash
pip install --upgrade deepseek-cli
```

For development installation, pull the latest changes and reinstall:

```bash
git pull
pip install -e . --upgrade
```

The CLI will automatically check for updates on startup and notify you when a new version is available.

### API Key Setup

Set your DeepSeek API key as an environment variable:

#### macOS/Linux
```bash
export DEEPSEEK_API_KEY="your-api-key"
```

#### Windows
```cmd
set DEEPSEEK_API_KEY="your-api-key"
```

To make it permanent, add it to your environment variables through System Settings.

If the variable is not set, the CLI prompts for the key without echoing it, so it does not end up in your terminal scrollback or shell history. When there is no interactive terminal (a piped or scripted run), it exits with an error instead of blocking on a prompt — set `DEEPSEEK_API_KEY` for those.

### Where your data is stored

Conversation history and settings are written under `$XDG_DATA_HOME`/`$XDG_CONFIG_HOME` (or the legacy `~/.deepseek-cli` if it already exists). These files hold the full transcript, including the text of any attached files, and are created with owner-only permissions (`0600`, in a `0700` directory) on macOS and Linux. Use `/clear` to drop the stored history.

## Usage

DeepSeek CLI supports two modes of operation: interactive mode and inline mode.

### Interactive Mode

After installation, you can start the CLI in interactive mode in two ways:

### If installed from PyPI:
```bash
deepseek
```

### If installed in development mode:
```bash
deepseek
# or
python -m deepseek_cli
```

### Inline Mode

You can also use DeepSeek CLI in inline mode to get quick answers without starting an interactive session:

```bash
# Basic usage
deepseek -q "What is the capital of France?"

# Specify a model
deepseek -q "Write a Python function to calculate factorial" -m deepseek-v4-pro

# Get raw output without token usage information
deepseek -q "Write a Python function to calculate factorial" -r

# Set a custom system message
deepseek -S "You are a Rust expert." -q "Explain lifetimes"

# Enable JSON output mode
deepseek -q "List 3 European capitals" --json

# Set temperature and a stop sequence
deepseek -q "Tell me a story" --temp 1.3 --stop "The End"

# Multiple stop sequences
deepseek -q "Count to five" --stop "5" --stop "five"

# Start the REPL with prefix completion and a lower temperature
deepseek --prefix --temp 0.0

# Enable Fill-in-the-Middle mode via CLI
deepseek --fim -q "def add(<fim_prefix>):<fim_suffix>    pass"

# Enable multiline input mode for complex prompts
deepseek --multiline

# Use Shift+Enter to submit (requires a terminal that distinguishes Shift+Enter)
deepseek --multiline --multiline-submit shift-enter

# Combine options with multiline
deepseek --multiline --prefix --temp 0.0

# Read query from a file
deepseek --read prompt.txt

# Pipe query from stdin
echo "What is the time complexity of quicksort?" | deepseek --read -

# Combine piped input with a prefix query and a system message
git diff HEAD | deepseek --read - -q "Review this diff:" -S "You are a code reviewer."

# Combine options
deepseek -q "Write a Python function to calculate factorial" -m deepseek-v4-pro -r -S "You are an expert Python developer."

# Think before answering, with maximum reasoning effort
deepseek --think --reasoning-effort max -q "Prove that sqrt(2) is irrational."

# Multiline example
deepseek --multiline -q "
def calculate_sum(a, b):
    return a + b
print(calculate_sum(2, 3))
"

Available options (apply to both inline and interactive modes unless noted):

**Core**
- `-q, --query TEXT`: Run in inline mode with the given query
- `--read FILE`: Read query text from FILE, or `-` to read from stdin (pipe). When combined with `-q` the file/pipe content is appended after the query text.
- `--file PATH`: Attach a file (or glob pattern) for analysis; the file's text is folded into the next user message. Repeatable: `--file a.py --file 'src/*.py'`. Inside the REPL use `/file`, `/pick`, `/files`, `/clearfiles` for the same feature.
- `--allow-sensitive`: Permit `--file` to attach credential-shaped files (`.env`, `~/.ssh/id_rsa`, `*.pem`, `~/.aws/credentials`, …). These are refused by default because their contents would be uploaded to the API.
- `-m, --model MODEL`: Model to use (`deepseek-v4-flash`, `deepseek-v4-pro`, `deepseek-v4-flash-vision-exp`). The retired names `deepseek-chat`, `deepseek-reasoner` and `deepseek-coder` are still accepted and map to `deepseek-v4-flash` with a warning.
- `-r, --raw`: Output raw response without token usage information (inline only)
- `-S, --system TEXT`: Set the system message. When omitted, a system message saved from a previous session (via `/system`) is preserved; otherwise `"You are a helpful assistant."` is used.
- `-s, --stream`: Enable streaming mode
- `--no-stream`: Disable streaming mode

**Output / Mode**
- `--json`: Enable JSON output mode (`response_format: json_object`)
- `--beta`: Enable the beta API endpoint (required for `--prefix` and `--fim`; enabled automatically when either is used)
- `--prefix`: Enable prefix completion mode (last user message becomes the assistant prefix)
- `--fim`: Enable Fill-in-the-Middle mode (use `<fim_prefix>`/`<fim_suffix>` tags in your query). Uses the beta completions endpoint; output is capped at 4K tokens
- `--think`: Enable Thinking mode (a per-request parameter on the V4 models, replacing the retired `deepseek-reasoner`)
- `--reasoning-effort {low,high,max}`: Reasoning effort used when Thinking mode is on (default `high`)
- `--max-tokens N`: Maximum output tokens for the session (model maximum is 384000)
- `--multiline`: Enable multiline input mode (Enter for newlines, empty line or Ctrl+D to submit by default)
- `--multiline-submit MODE`: How to submit in multiline mode: `empty-line` (default, press Enter on a blank line) or `shift-enter` (Shift+Enter — requires a terminal that distinguishes Shift+Enter from Enter, e.g. Kitty, WezTerm)

**Sampling**
- `--temp FLOAT`: Set temperature (0–2)
- `--top-p FLOAT`: Set top-p sampling (0–1)

> `--freq` and `--pres` are still accepted so existing scripts do not break, but they are ignored: the DeepSeek API no longer supports `frequency_penalty` or `presence_penalty`.

**Stop Sequences**
- `--stop SEQ`: Add a stop sequence (can be repeated: `--stop A --stop B`)

### Troubleshooting

- If the API key is not recognized:
  - Make sure you've set the DEEPSEEK_API_KEY environment variable
  - Try closing and reopening your terminal
  - Check if the key is correct with: `echo $DEEPSEEK_API_KEY` (Unix) or `echo %DEEPSEEK_API_KEY%` (Windows)

- If you get import errors:
  - Ensure you've installed the package: `pip list | grep deepseek-cli`
  - Try reinstalling: `pip install --force-reinstall deepseek-cli`

- For development installation issues:
  - Make sure you're in the correct directory
  - Try: `pip install -e . --upgrade`

### Available Commands

Basic Commands:
- `/help` - Show help message
- `/models` - List available models
- `/model X` - Switch model (deepseek-v4-flash, deepseek-v4-pro, deepseek-v4-flash-vision-exp)
- `/system X` - Set a custom system message mid-session
- `/system` - Show the current system message
- `/clear` - Clear conversation history
- `/history` - Display conversation history
- `/about` - Show API information
- `/balance` - Show instructions for checking your account balance on the DeepSeek platform
- `/multiline` - Show multiline mode information (enable with --multiline flag)
- `/quit`, `/exit` (or `quit`, `exit`) - Exit the program

At the prompt, Ctrl+C cancels the line you are typing and returns you to the prompt; press it twice in a row (or use Ctrl+D) to exit.

Model Settings:
- `/temp X` - Set temperature (0-2) or use preset (coding/data/chat/translation/creative)
- `/top_p X` - Set top_p sampling (0 to 1)
- `/maxtokens N` - Set the maximum output tokens for this session
- `/think` - Toggle Thinking mode (Chain of Thought) on the current model
- `/effort X` - Set reasoning effort used by Thinking mode: `low`, `high`, or `max`

> `/freq` and `/pres` have been removed. The DeepSeek API no longer supports
> `frequency_penalty` or `presence_penalty`; running either command now prints
> an explanation instead.

Beta Features:
- `/beta` - Toggle beta features
- `/prefix` - Toggle prefix completion mode
- `/fim` - Toggle Fill-in-the-Middle completion
- `/cache` - Toggle context caching

Output Control:
- `/json` - Toggle JSON output mode
- `/stream` - Toggle streaming mode (streaming is disabled by default)
- `/stop X` - Add stop sequence
- `/clearstop` - Clear stop sequences

Function Calling:
- `/function {}` - Add function definition (JSON format)
- `/clearfuncs` - Clear registered functions

File Attachments (analyse local files):
- `/file PATH...` - Attach one or more files for the next message. Accepts literal paths, `~`-paths, and glob patterns (e.g. `/file src/*.py`). Add `--allow-sensitive` to attach credential-shaped files, which are refused by default
- `/pick` - Interactive file picker with tab completion (multi-select, space-separated)
- `/files` - List currently attached files
- `/dropfile X` - Remove an attached file by index (see `/files`) or by absolute path
- `/clearfiles` - Clear all attached files

Attached file contents are folded into the next outgoing user message and then automatically cleared, matching the DeepSeek app's file-upload UX. Limits: 1 MiB per file, 4 MiB total, up to 20 files; binary files are rejected.

Files that look like secrets — `.env` / `.env.*`, `*.pem`, `*.key`, `id_rsa`, `.netrc`, `.npmrc`, and anything under `.ssh/`, `.aws/`, `.gnupg/`, `.kube/`, `.docker/` — are refused so a broad glob such as `/file **/*` cannot silently upload credentials. Attach one deliberately with `/file --allow-sensitive <path>` (or `--allow-sensitive` on the command line).

Note that once attached, a file's text becomes part of the conversation and is stored in the local history file, so it is re-sent with subsequent messages until you run `/clear`.

### Model-Specific Features

All V4 models share a **1M token context window** and a **384K maximum output**,
and all of them support both Non-thinking and Thinking modes. Thinking is
selected per request with `/think` (or `--think`), not by switching model.

#### DeepSeek-V4-Flash (`deepseek-v4-flash`) — default

- **Parameters**: 284B total / 13B active
- **Context Length**: 1M tokens
- **Output Length**: up to 384K tokens (this CLI defaults to 8K; raise with `/maxtokens`)
- **Supported features**:
  - JSON Output ✓
  - Function Calling ✓ (up to 128 functions)
  - Chat Prefix Completion (Beta) ✓
  - Fill-in-the-Middle (Beta) ✓
  - Thinking mode ✓
- The general-purpose default: fastest and cheapest of the three.

#### DeepSeek-V4-Pro (`deepseek-v4-pro`)

- **Parameters**: 1.6T total / 49B active
- **Context Length**: 1M tokens
- **Output Length**: up to 384K tokens
- **Supported features**: same as V4-Flash (JSON, function calling, prefix, FIM, thinking)
- The strongest model; best for hard reasoning and code tasks. Pair with
  `/think` and `/effort max` for the most thorough answers.

#### DeepSeek-V4-Flash-Vision (`deepseek-v4-flash-vision-exp`)

> ⚠️ **Experimental.** Image input is billed as input tokens alongside your
> text. This CLI sends text only — attaching an image is not yet supported, so
> the model behaves like V4-Flash here.

- **Context Length**: 1M tokens
- **Output Length**: up to 384K tokens
- **Fill-in-the-Middle**: ✗

#### Retired models

`deepseek-chat`, `deepseek-reasoner` and `deepseek-coder` were fully retired on
**2026-07-24** and are no longer served. The CLI still accepts those names — from
a command, a `--model` flag, or a settings file written by an older version — and
maps them to `deepseek-v4-flash`, printing a warning. Update your scripts to the
V4 names.


### Feature Details

#### Pipe and File Input (`--read`)

Feed query content from a file or stdin pipe instead of (or in addition to) `-q`:

```bash
# Read the entire query from a file
deepseek --read prompt.txt

# Pipe from another command (use '-' as the filename)
echo "Explain this error:" | deepseek --read -
cat error.log | deepseek --read -

# Combine with -q — the -q text comes first, then the file/pipe content
git diff HEAD | deepseek --read - -q "Review this diff:"
cat report.md  | deepseek --read - -q "Summarise in one paragraph:"
```

When `--read -` is used but stdin is a terminal (not a pipe), the CLI exits with a clear error message.

#### XDG Base Directory Support

On fresh installations (no existing `~/.deepseek-cli` directory) the CLI follows the [XDG Base Directory specification](https://wiki.archlinux.org/title/XDG_Base_Directory):

| Data | Default path | Override |
|---|---|---|
| `settings.json` | `~/.config/deepseek-cli/` | `$XDG_CONFIG_HOME/deepseek-cli/` |
| `chat_history.json` | `~/.local/share/deepseek-cli/` | `$XDG_DATA_HOME/deepseek-cli/` |

**Existing users** who already have a `~/.deepseek-cli` directory are unaffected — that directory continues to be used automatically. No data migration is needed.

#### Thinking Mode

On the V4 models, reasoning is a per-request mode rather than a separate model.
Toggle it with `/think` in the REPL or `--think` on the command line, and choose
how hard the model works with `/effort` / `--reasoning-effort` (`low`, `high`,
the default, or `max`):

```bash
deepseek --think --reasoning-effort max -q "Prove that sqrt(2) is irrational."
```

The chain of thought arrives in a separate `reasoning_content` field and is
rendered above the answer in its own panel. Use `-r` / `/raw` to suppress it.

#### Fill-in-the-Middle (FIM)

Use XML-style tags to mark the gap you want filled. Closing tags are optional:

```
<fim_prefix>def calculate_sum(a, b):</fim_prefix><fim_suffix>    return result</fim_suffix>
```

```bash
deepseek --fim -q "<fim_prefix>def add(a, b):<fim_suffix>    return result"
```

Text before `<fim_suffix>` becomes the prompt and text after it becomes the
suffix. With no `<fim_suffix>` tag the whole input is treated as a prefix, which
makes FIM behave like a plain completion.

FIM is a Beta feature served from the legacy completions endpoint, so the CLI
switches to `https://api.deepseek.com/beta` automatically when `/fim` is on.
Its output is capped at **4K tokens** regardless of `/maxtokens`. FIM requests
are completions rather than conversation turns, so they are not added to the
chat history.

#### Prefix Completion

`/prefix` (or `--prefix`) re-sends your last message as the *start* of the
assistant's reply, so the model continues from it instead of responding to it.
Like FIM this is Beta-only, and the CLI enables the beta endpoint for you.

#### Multiline Input
Enable multiline input mode for complex prompts that span multiple lines:

**Usage:**
```bash
# Enable multiline mode for interactive sessions
deepseek --multiline

# Use multiline in inline mode
deepseek --multiline -q "
def calculate_sum(a, b):
    return a + b
print(calculate_sum(2, 3))
"
```

**Controls (default `empty-line` mode):**
- Enter: Add new line
- Empty line (press Enter twice): Submit input
- Ctrl+D: Submit input (alternative)
- Ctrl+C: Cancel input

**Controls (`--multiline-submit shift-enter` mode, requires terminal support):**
- Enter: Add new line
- Shift+Enter: Submit input
- Ctrl+D: Submit input (alternative)
- Ctrl+C: Cancel input

**Best for:**
- Code snippets and functions
- Long-form text generation
- Complex prompts with structure
- Multi-step instructions

#### JSON Mode
Forces model to output valid JSON. Example system message:
```json
{
    "response": "structured output",
    "data": {
        "field1": "value1",
        "field2": "value2"
    }
}
```

#### Context Caching
- **Automatic disk-based caching** for all users
- **No code changes required** - works automatically
- **Minimum cache size**: 64 tokens
- **Pricing**:
  - Cache hits: $0.014 per million tokens (90% savings)
  - Cache misses: $0.14 per million tokens (standard rate)
- **Performance benefits**:
  - Significantly reduces first token latency for long, repetitive inputs
  - Example: 128K prompt reduced from 13s to 500ms
- **Best use cases**:
  - Q&A assistants with long preset prompts
  - Role-play with extensive character settings
  - Data analysis with recurring queries on same documents
  - Code analysis and debugging with repeated repository references
  - Few-shot learning with multiple examples
- Enabled by default

#### Anthropic API Compatibility
DeepSeek API now supports Anthropic API format, enabling integration with tools like Claude Code:

**Setup for Claude Code:**
```bash
# Install Claude Code
npm install -g @anthropic-ai/claude-code

# Configure environment variables
export ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
export ANTHROPIC_AUTH_TOKEN=${DEEPSEEK_API_KEY}
export ANTHROPIC_MODEL=deepseek-v4-pro
export ANTHROPIC_SMALL_FAST_MODEL=deepseek-v4-flash

# Run in your project
cd my-project
claude
```

**Python SDK Example:**
```python
import anthropic

client = anthropic.Anthropic(
    base_url="https://api.deepseek.com/anthropic",
    api_key="your-deepseek-api-key"
)

message = client.messages.create(
    model="deepseek-v4-pro",
    max_tokens=1000,
    system="You are a helpful assistant.",
    messages=[
        {
            "role": "user",
            "content": [{"type": "text", "text": "Hi, how are you?"}]
        }
    ]
)
print(message.content)
```

**Supported Fields:**
- ✓ model, max_tokens, stop_sequences, stream, system
- ✓ temperature (range 0.0-2.0), top_p
- ✓ tools (function calling)
- ✗ thinking, top_k, mcp_servers (ignored)

## Temperature Presets

- `coding`: 0.0 (deterministic)
- `data`: 1.0 (balanced)
- `chat`: 1.3 (creative)
- `translation`: 1.3 (creative)
- `creative`: 1.5 (very creative)

## Error Handling

- Automatic retry with exponential backoff
- Rate limit handling, honouring the server's `Retry-After` header up to a bounded maximum
- Clear error messages
- API status feedback
- On a 401 the CLI offers to take a replacement API key (read without echo). In non-interactive runs it reports the error instead of blocking on a prompt.

## Support

For support, please open an issue on the [GitHub repository](https://github.com/PierrunoYT/deepseek-cli/issues).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Changelog

There is no changelog for this project. A `CHANGELOG.md` was started but removed partway through development, so any attempt to reconstruct one now would be incomplete and inaccurate. Refer to the [commit history](https://github.com/PierrunoYT/deepseek-cli/commits/main) for a record of changes.