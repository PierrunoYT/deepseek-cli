# DeepSeek CLI

A powerful command-line interface for interacting with DeepSeek's AI models.

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

- 🧪 Beta Features
  - Prefix Completion: Complete assistant messages from a given prefix
  - Fill-in-the-Middle (FIM): Complete content between a prefix and suffix
  - Context Caching: Automatic caching for better performance

- 🛠️ Advanced Controls
  - Temperature control with presets
  - JSON output mode
  - Streaming responses
  - Function calling
  - Stop sequences
  - Top-p sampling
  - Frequency and presence penalties

## Installation

### Prerequisites
- Python 3.7 or higher
- Git (for cloning the repository)
- pip (Python package installer)

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/deepseek-cli.git
cd deepseek-cli
```

### Step 2: Install Dependencies

```bash
pip install openai
```

### Step 3: Set Up API Key

#### macOS/Linux
In your terminal:
```bash
echo 'export DEEPSEEK_API_KEY="your-api-key"' >> ~/.bashrc    # For Bash
echo 'export DEEPSEEK_API_KEY="your-api-key"' >> ~/.zshrc     # For Zsh
source ~/.bashrc  # or source ~/.zshrc
```

#### Windows
In Command Prompt (Run as Administrator):
```cmd
setx DEEPSEEK_API_KEY "your-api-key"
```
Or in PowerShell (Run as Administrator):
```powershell
[Environment]::SetEnvironmentVariable("DEEPSEEK_API_KEY", "your-api-key", "User")
```

### Step 4: Verify Installation

```bash
# macOS/Linux
echo $DEEPSEEK_API_KEY

# Windows Command Prompt
echo %DEEPSEEK_API_KEY%

# Windows PowerShell
echo $env:DEEPSEEK_API_KEY
```

### Troubleshooting

#### macOS/Linux
- If the API key is not recognized, try:
  ```bash
  source ~/.bashrc  # or source ~/.zshrc
  ```
- If you get permission errors:
  ```bash
  chmod +x deepseek_cli.py
  ```

#### Windows
- If you get execution policy errors in PowerShell:
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```
- If the environment variable is not recognized, close and reopen your terminal

## Usage

Start the CLI:
```bash
python deepseek_cli.py
```

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
- `/stream` - Toggle streaming mode
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