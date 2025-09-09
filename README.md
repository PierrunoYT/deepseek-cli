# DeepSeek CLI

A powerful command-line interface for interacting with DeepSeek's AI models.

[@PierrunoYT/deepseek-cli](https://github.com/PierrunoYT/deepseek-cli)

## Features

- 🤖 Multiple Model Support
  - DeepSeek-V3 (deepseek-chat)
  - DeepSeek-R1 (deepseek-reasoner)
  - DeepSeek Coder (deepseek-coder)

- 🔄 Advanced Conversation Features
  - Multi-round conversations with context preservation
  - System message customization
  - Conversation history tracking
  - Context caching for better performance
  - Inline mode for quick queries

- 🧪 Beta Features
  - Prefix Completion: Complete assistant messages from a given prefix
  - Fill-in-the-Middle (FIM): Complete content between a prefix and suffix
  - Context Caching: Automatic caching for better performance

- 🛠️ Advanced Controls
  - Temperature control with presets
  - JSON output mode
  - Streaming responses (enabled by default)
  - Function calling
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

#### DeepSeek-V3 (deepseek-chat)
- 64K context length (64,000 tokens)
- Default max output: 4096 tokens
- Beta max output: 8192 tokens (requires beta mode)
- Supports all features
- General-purpose chat model
- Latest improvements:
  - Enhanced instruction following (77.6% IFEval accuracy)
  - Improved JSON output (97% parsing rate)
  - Advanced reasoning capabilities
  - Role-playing capabilities

#### DeepSeek-R1 (deepseek-reasoner)
- 64K context length
- 8K output tokens
- 32K Chain of Thought output
- Excels at complex reasoning
- Unsupported features: function calling, JSON output, FIM
- Unsupported parameters: temperature, top_p, presence/frequency penalties

#### DeepSeek Coder (deepseek-coder)
- Default max output: 4096 tokens
- Beta max output: 8192 tokens (requires beta mode)
- Optimized for code generation
- Supports all features

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
- Automatically caches context for better performance
- Minimum cache size: 64 tokens
- Cache hits reduce token costs
- Enabled by default

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