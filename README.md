# DeepSeek CLI

A powerful command-line interface for interacting with DeepSeek's AI models.

[@PierrunoYT/deepseek-cli](https://github.com/PierrunoYT/deepseek-cli)

## Features

- 🤖 Multiple Model Support
  - DeepSeek-V3.1 (deepseek-chat) - Non-thinking Mode
  - DeepSeek-V3.1 (deepseek-reasoner) - Thinking Mode with Chain of Thought
  - DeepSeek-V2.5 Coder (deepseek-coder)

- 🔄 Advanced Conversation Features
  - Multi-round conversations with context preservation
  - System message customization
  - Conversation history tracking
  - Context caching for better performance and cost savings
  - Inline mode for quick queries
  - 128K context window for all models

- 🧪 Beta Features
  - Prefix Completion: Complete assistant messages from a given prefix
  - Fill-in-the-Middle (FIM): Complete content between a prefix and suffix
  - Context Caching: Automatic disk-based caching with up to 90% cost savings
  - Anthropic API Compatibility: Use DeepSeek models with Anthropic API format

- 🛠️ Advanced Controls
  - Temperature control with presets
  - JSON output mode
  - Streaming responses (enabled by default)
  - Function calling (up to 128 functions)
  - Stop sequences
  - Top-p sampling
  - Frequency and presence penalties

- 📦 Package Management
  - Automatic version checking
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
deepseek -q "Write a Python function to calculate factorial" -m deepseek-coder

# Get raw output without token usage information
deepseek -q "Write a Python function to calculate factorial" -r

# Combine options
deepseek -q "Write a Python function to calculate factorial" -m deepseek-coder -r
```

Available inline mode options:
- `-q, --query`: The query to send to the model
- `-m, --model`: The model to use (deepseek-chat, deepseek-coder, deepseek-reasoner)
- `-r, --raw`: Output raw response without token usage information
- `-s, --stream`: Enable streaming mode (enabled by default)
- `--no-stream`: Disable streaming mode

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
- `/model X` - Switch model (deepseek-chat, deepseek-coder, deepseek-reasoner)
- `/clear` - Clear conversation history
- `/history` - Display conversation history
- `/about` - Show API information
- `/balance` - Check account balance

Model Settings:
- `/temp X` - Set temperature (0-2) or use preset (coding/data/chat/translation/creative)
- `/freq X` - Set frequency penalty (-2 to 2)
- `/pres X` - Set presence penalty (-2 to 2)
- `/top_p X` - Set top_p sampling (0 to 1)

Beta Features:
- `/beta` - Toggle beta features
- `/prefix` - Toggle prefix completion mode
- `/fim` - Toggle Fill-in-the-Middle completion
- `/cache` - Toggle context caching

Output Control:
- `/json` - Toggle JSON output mode
- `/stream` - Toggle streaming mode (streaming is enabled by default)
- `/stop X` - Add stop sequence
- `/clearstop` - Clear stop sequences

Function Calling:
- `/function {}` - Add function definition (JSON format)
- `/clearfuncs` - Clear registered functions

### Model-Specific Features

#### DeepSeek-V3.1 (deepseek-chat)
- **Version**: DeepSeek-V3.1 (Non-thinking Mode)
- **Context Length**: 128K tokens (128,000 tokens)
- **Output Length**: Default 4K, Maximum 8K tokens
- **Supports all features**:
  - JSON Output ✓
  - Function Calling ✓ (up to 128 functions)
  - Chat Prefix Completion (Beta) ✓
  - Fill-in-the-Middle (Beta) ✓
- General-purpose chat model
- Latest improvements:
  - Enhanced instruction following (77.6% IFEval accuracy)
  - Improved JSON output (97% parsing rate)
  - Advanced reasoning capabilities
  - Role-playing capabilities

#### DeepSeek-V3.1 (deepseek-reasoner)
- **Version**: DeepSeek-V3.1 (Thinking Mode)
- **Context Length**: 128K tokens (128,000 tokens)
- **Output Length**: Default 32K, Maximum 64K tokens
- **Chain of Thought**: Displays reasoning process before final answer
- **Supported features**:
  - JSON Output ✓
  - Chat Prefix Completion (Beta) ✓
- **Unsupported features**:
  - Function Calling ✗ (automatically falls back to deepseek-chat if tools provided)
  - Fill-in-the-Middle ✗
  - Temperature, top_p, presence/frequency penalties ✗
- Excels at complex reasoning and problem-solving tasks

#### DeepSeek-V2.5 Coder (deepseek-coder)
- **Context Length**: 128K tokens
- **Output Length**: Default 4K, Maximum 8K tokens
- **Supports all features**:
  - JSON Output ✓
  - Function Calling ✓
  - Chat Prefix Completion (Beta) ✓
  - Fill-in-the-Middle (Beta) ✓
- Optimized for code generation and analysis

### Feature Details

#### Fill-in-the-Middle (FIM)
Use XML-style tags to define the gap:
```
<fim_prefix>def calculate_sum(a, b):</fim_prefix><fim_suffix>    return result</fim_suffix>
```

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
export ANTHROPIC_MODEL=deepseek-chat
export ANTHROPIC_SMALL_FAST_MODEL=deepseek-chat

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
    model="deepseek-chat",
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
- Rate limit handling
- Clear error messages
- API status feedback

## Support

For support, please open an issue on the [GitHub repository](https://github.com/PierrunoYT/deepseek-cli/issues).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.