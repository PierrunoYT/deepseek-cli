# AI CLI - Multi-Provider AI Interface

A powerful command-line interface for interacting with multiple AI models from different providers through a unified interface powered by LiteLLM.

[@PierrunoYT/deepseek-cli](https://github.com/PierrunoYT/deepseek-cli)

## 🌟 Features

### 🤖 Multi-Provider Support
- **DeepSeek**: deepseek-chat, deepseek-coder, deepseek-reasoner
- **OpenAI**: GPT-4o, GPT-4o Mini, GPT-4 Turbo
- **Anthropic**: Claude 3.5 Sonnet, Claude 3.5 Haiku
- **Google**: Gemini 2.0 Flash, Gemini 1.5 Pro
- **Ollama**: Local models (Llama 3.2, Qwen 2.5, etc.)

### 🔄 Advanced Features
- **Streaming Responses**: Real-time token streaming with rich formatting
- **Function Calling**: Support for up to 128 functions
- **JSON Mode**: Force valid JSON output
- **Context Preservation**: Multi-round conversations with history
- **Reasoning Mode**: Chain-of-thought display for reasoning models
- **Temperature Presets**: Quick settings for different use cases
- **Flexible Parameters**: Control temperature, top_p, penalties, and more

### 🎨 Rich Terminal UI
- Markdown rendering for responses
- Colored output with syntax highlighting
- Styled panels and prompts
- Token usage statistics
- Provider and model information display

## 📦 Installation

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

### Updating

```bash
pip install --upgrade deepseek-cli
```

## 🔑 API Key Setup

Set up API keys for the providers you want to use:

### Linux/macOS
```bash
export DEEPSEEK_API_KEY="your-deepseek-key"
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key"
export GEMINI_API_KEY="your-gemini-key"
```

### Windows (PowerShell)
```powershell
$env:DEEPSEEK_API_KEY="your-deepseek-key"
$env:OPENAI_API_KEY="your-openai-key"
$env:ANTHROPIC_API_KEY="your-anthropic-key"
$env:GEMINI_API_KEY="your-gemini-key"
```

### Windows (CMD)
```cmd
set DEEPSEEK_API_KEY=your-deepseek-key
set OPENAI_API_KEY=your-openai-key
set ANTHROPIC_API_KEY=your-anthropic-key
set GEMINI_API_KEY=your-gemini-key
```

**Note**: Ollama models run locally and don't require API keys. Make sure you have [Ollama](https://ollama.ai) installed and running.

## 🚀 Usage

### Interactive Mode

Start the CLI in interactive mode:

```bash
deepseek
```

Or with a specific model:

```bash
deepseek -m gpt-4o
deepseek -m claude-3-5-sonnet-20241022
deepseek -m deepseek/deepseek-chat
```

### Inline Mode

Get quick answers without starting an interactive session:

```bash
# Basic usage
deepseek -q "What is the capital of France?"

# Specify a model
deepseek -q "Write a Python function to calculate factorial" -m deepseek/deepseek-coder

# Get raw output without token usage
deepseek -q "Explain quantum computing" -m gpt-4o -r

# Enable streaming
deepseek -q "Tell me a story" -m claude-3-5-sonnet-20241022 -s
```

### Command-Line Options

| Option | Description |
|--------|-------------|
| `-q, --query` | Run in inline mode with the specified query |
| `-m, --model` | Specify the model to use |
| `-r, --raw` | Output raw response without token usage info |
| `-s, --stream` | Enable streaming mode |

## 📋 Available Commands

### Model Management

| Command | Description |
|---------|-------------|
| `/models` | List all available models grouped by provider |
| `/provider <name>` | List models for a specific provider |
| `/model <name>` | Switch to a specific model |
| `/apikey <provider> <key>` | Set API key for a provider |

Example:
```
/models                                    # See all models
/provider openai                           # See OpenAI models
/model gpt-4o                             # Switch to GPT-4o
/apikey openai sk-...                     # Set OpenAI API key
```

### Output Control

| Command | Description |
|---------|-------------|
| `/json` | Toggle JSON output mode |
| `/stream` | Toggle streaming mode |
| `/beta` | Toggle beta features (DeepSeek only) |
| `/prefix` | Toggle prefix completion (requires beta) |

### Model Parameters

| Command | Description |
|---------|-------------|
| `/temp <value>` | Set temperature (0-2) or use preset |
| `/freq <value>` | Set frequency penalty (-2 to 2) |
| `/pres <value>` | Set presence penalty (-2 to 2) |
| `/top_p <value>` | Set top_p sampling (0 to 1) |
| `/stop <text>` | Add stop sequence |
| `/clearstop` | Clear all stop sequences |

### Function Calling

| Command | Description |
|---------|-------------|
| `/function <json>` | Add a function definition |
| `/clearfuncs` | Clear all registered functions |

### General

| Command | Description |
|---------|-------------|
| `/clear` | Clear conversation history |
| `/help` | Show help message |
| `/about` | Show API information |
| `quit` or `exit` | Exit the program |

## 🎯 Temperature Presets

Quick temperature settings for different use cases:

| Preset | Value | Best For |
|--------|-------|----------|
| `coding` | 0.0 | Code generation, deterministic output |
| `data` | 1.0 | Data analysis, balanced responses |
| `chat` | 1.3 | Conversational interactions |
| `translation` | 1.3 | Language translation |
| `creative` | 1.5 | Creative writing, brainstorming |

Usage: `/temp coding` or `/temp 0.7`

## 🤖 Supported Models

### DeepSeek Models

| Model | Description | Context | Max Output |
|-------|-------------|---------|------------|
| `deepseek/deepseek-chat` | General chat model (V3.1) | 128K | 8K |
| `deepseek/deepseek-coder` | Code-optimized model (V2.5) | 128K | 8K |
| `deepseek/deepseek-reasoner` | Reasoning model with CoT (V3.1) | 128K | 64K |

### OpenAI Models

| Model | Description | Context | Max Output |
|-------|-------------|---------|------------|
| `gpt-4o` | Most advanced multimodal model | 128K | 16K |
| `gpt-4o-mini` | Fast and affordable model | 128K | 16K |
| `gpt-4-turbo` | GPT-4 Turbo | 128K | 4K |

### Anthropic Models

| Model | Description | Context | Max Output |
|-------|-------------|---------|------------|
| `claude-3-5-sonnet-20241022` | Most intelligent Claude model | 200K | 8K |
| `claude-3-5-haiku-20241022` | Fastest Claude model | 200K | 8K |

### Google Models

| Model | Description | Context | Max Output |
|-------|-------------|---------|------------|
| `gemini/gemini-2.0-flash-exp` | Latest Gemini 2.0 Flash | 1M | 8K |
| `gemini/gemini-1.5-pro` | Gemini 1.5 Pro with huge context | 2M | 8K |

### Ollama (Local Models)

| Model | Description | Context | Max Output |
|-------|-------------|---------|------------|
| `ollama/llama3.2` | Meta's Llama 3.2 (local) | 128K | 4K |
| `ollama/qwen2.5` | Alibaba's Qwen 2.5 (local) | 128K | 4K |

**Note**: For Ollama models, make sure Ollama is installed and the model is pulled:
```bash
ollama pull llama3.2
ollama pull qwen2.5
```

## 💡 Usage Examples

### Switching Between Providers

```bash
# Start with DeepSeek
deepseek

# Switch to OpenAI
> /model gpt-4o

# Switch to Anthropic
> /model claude-3-5-sonnet-20241022

# Switch to local Ollama
> /model ollama/llama3.2
```

### Using Different Models for Different Tasks

```bash
# Code generation with DeepSeek Coder
deepseek -m deepseek/deepseek-coder -q "Write a binary search algorithm in Python"

# Creative writing with Claude
deepseek -m claude-3-5-sonnet-20241022 -q "Write a short sci-fi story"

# Fast responses with GPT-4o Mini
deepseek -m gpt-4o-mini -q "Summarize quantum computing in 3 sentences"

# Local inference with Ollama
deepseek -m ollama/llama3.2 -q "Explain machine learning"
```

### Advanced Configuration

```bash
# Set temperature for creative output
> /temp creative
> Write a poem about AI

# Use JSON mode for structured output
> /json
> List 5 programming languages with their use cases

# Enable streaming for long responses
> /stream
> Explain the history of computing
```

## 🔧 Advanced Features

### Function Calling

Define functions that the AI can call:

```bash
> /function {"name": "get_weather", "description": "Get weather for a location", "parameters": {"type": "object", "properties": {"location": {"type": "string"}}, "required": ["location"]}}
> What's the weather in Paris?
```

### Reasoning Mode (DeepSeek)

The DeepSeek Reasoner model shows its chain of thought:

```bash
> /model deepseek/deepseek-reasoner
> Solve this logic puzzle: If all roses are flowers and some flowers fade quickly, can we conclude that some roses fade quickly?
```

### Local Models with Ollama

Run models locally without API costs:

```bash
# Make sure Ollama is running
ollama serve

# Use local models
deepseek -m ollama/llama3.2 -q "Hello, how are you?"
```

## 🐛 Troubleshooting

### API Key Issues

If API keys aren't recognized:
```bash
# Check if key is set
echo $DEEPSEEK_API_KEY  # Linux/macOS
echo %DEEPSEEK_API_KEY%  # Windows CMD
$env:DEEPSEEK_API_KEY   # Windows PowerShell

# Set key in-session
> /apikey deepseek your-key-here
```

### Import Errors

```bash
# Reinstall dependencies
pip install --force-reinstall deepseek-cli

# For development
pip install -e . --upgrade
```

### Ollama Connection Issues

```bash
# Check if Ollama is running
ollama list

# Start Ollama server
ollama serve

# Pull required model
ollama pull llama3.2
```

## 🌐 Provider-Specific Notes

### DeepSeek
- Supports beta features like prefix completion
- Reasoner model provides chain-of-thought reasoning
- Context caching available for cost savings

### OpenAI
- Supports vision capabilities (not yet exposed in CLI)
- Function calling fully supported
- JSON mode available

### Anthropic
- Extended context windows (200K tokens)
- Strong performance on reasoning tasks
- Function calling supported

### Google Gemini
- Massive context windows (up to 2M tokens)
- Experimental models available
- Multimodal capabilities

### Ollama
- Runs completely locally
- No API costs
- Requires local installation and model downloads

## 📊 Token Usage

The CLI displays token usage after each response:
- **Input tokens**: Tokens in your prompt
- **Output tokens**: Tokens in the response
- **Total tokens**: Combined usage
- **Character estimates**: Approximate English/Chinese characters

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [LiteLLM](https://github.com/BerriAI/litellm) for multi-provider support
- Uses [Rich](https://github.com/Textualize/rich) for beautiful terminal output
- Inspired by the need for a unified AI model interface

## 📞 Support

For issues, questions, or contributions, please visit the [GitHub repository](https://github.com/PierrunoYT/deepseek-cli/issues).

---

**Note**: This CLI was originally designed for DeepSeek but has been expanded to support multiple AI providers through LiteLLM. The package name remains `deepseek-cli` for compatibility, but it now works with any LiteLLM-supported provider.