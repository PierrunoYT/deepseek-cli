# Changelog

All notable changes to the DeepSeek CLI project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-01-04

### Added

#### DeepSeek V3.1 API Support

- **Updated Model Configurations**:
  - DeepSeek-V3.1 (deepseek-chat) - Non-thinking Mode with 128K context
  - DeepSeek-V3.1 (deepseek-reasoner) - Thinking Mode with 128K context
  - All models now support 128K context window (128,000 tokens)

- **Enhanced Output Limits**:
  - deepseek-chat: Default 4K, Maximum 8K tokens
  - deepseek-reasoner: Default 32K, Maximum 64K tokens
  - deepseek-coder: Default 4K, Maximum 8K tokens

- **Reasoning Model Enhancements**:
  - Added support for `reasoning_content` field in deepseek-reasoner responses
  - Display Chain of Thought reasoning process in both streaming and non-streaming modes
  - Automatic fallback to deepseek-chat when function calling is requested with deepseek-reasoner

- **Anthropic API Compatibility**:
  - Added support for Anthropic API format at `https://api.deepseek.com/anthropic`
  - New `use_anthropic` parameter in APIClient for Anthropic API mode
  - `toggle_anthropic()` method to switch between standard and Anthropic API
  - Compatible with Claude Code and other Anthropic-based tools

- **Enhanced Context Caching**:
  - Updated pricing information: $0.014/M tokens for cache hits, $0.14/M tokens for cache misses
  - Documented disk-based caching with up to 90% cost savings
  - Performance improvements: 128K prompt latency reduced from 13s to 500ms

### Changed

- **Model Configuration Updates**:
  - Updated all model configs with version information and feature support flags
  - Added `context_length`, `default_max_tokens`, and feature support indicators
  - Reorganized model metadata for better clarity

- **API Client Improvements**:
  - Enhanced `_create_client()` to support Anthropic API base URL
  - Updated `toggle_beta()` to respect Anthropic API mode
  - Improved error handling for API initialization

- **Chat Handler Updates**:
  - Enhanced `handle_response()` to display reasoning content from deepseek-reasoner
  - Updated `stream_response()` to handle reasoning_content in streaming mode
  - Added visual distinction for Chain of Thought output (yellow panel)

- **Configuration Updates**:
  - Moved API URLs to top of settings file for better organization
  - Added `ANTHROPIC_BASE_URL` constant
  - Enhanced context cache configuration with pricing details

### Documentation

- **README Updates**:
  - Updated feature list to reflect V3.1 capabilities
  - Added detailed model specifications with 128K context information
  - Documented Anthropic API compatibility with setup examples
  - Enhanced context caching documentation with pricing and use cases
  - Updated model-specific features section with comprehensive details

- **API Documentation**:
  - Added examples for Anthropic API integration
  - Documented supported and unsupported fields for Anthropic compatibility
  - Included Claude Code integration guide

### Technical Details

- All changes maintain backward compatibility
- No breaking changes to existing API
- Automatic handling of new features without user intervention
- Enhanced error messages for better debugging

## [0.1.24] - 2025-01-04

### Changed

#### Code Quality Improvements

- **Simplified Import Handling**: Reduced all triple-nested try-except import blocks to cleaner two-level fallback chains across all modules
  - `src/cli/deepseek_cli.py`
  - `src/api/client.py`
  - `src/handlers/command_handler.py`
  - `src/handlers/error_handler.py`
  - `src/handlers/chat_handler.py`

- **Comprehensive Type Hints**: Added proper type annotations throughout the entire codebase
  - All function return types now properly annotated (`-> None`, `-> str`, `-> Optional[str]`, etc.)
  - All function parameters properly typed
  - Complex types properly defined (e.g., `Dict[str, Any]`, `List[Dict[str, Any]]`)
  - Improved IDE support and code maintainability

- **Improved Error Handling**:
  - Replaced generic `Exception` catches with specific exception types (`KeyError`, `ValueError`, `TypeError`)
  - Added descriptive error messages using Rich console formatting
  - Enhanced error context and actionable solutions
  - Better error propagation with detailed docstrings

#### Deprecated Package Replacement

- **Version Checker (`src/utils/version_checker.py`)**:
  - Replaced deprecated `pkg_resources` with modern `importlib.metadata`
  - Eliminates deprecation warnings when running the CLI
  - Maintains backward compatibility
  - Improved performance and reliability

#### Code Cleanup

- **Removed Dead Code**:
  - Removed all commented-out code blocks
  - Cleaned up unused imports
  - Removed redundant code sections

- **Consistent Output Formatting**:
  - Replaced all `print()` calls with Rich `console.print()` for uniform styling
  - Consistent error message formatting across all modules
  - Better visual feedback for users

#### Documentation Enhancements

- **Enhanced Docstrings**:
  - Added comprehensive docstrings to all public methods
  - Included Args, Returns, and Raises sections where applicable
  - Improved code documentation for better maintainability
  - Clear explanations of complex logic

#### Module-Specific Improvements

**CLI Module (`src/cli/deepseek_cli.py`)**:
- Enhanced `_print_welcome()` method with proper parameter documentation
- Improved command-line argument parsing with better type hints
- Consistent error handling throughout

**API Client (`src/api/client.py`)**:
- Added input validation for API keys (empty check, strip whitespace)
- Enhanced error messages for all API operations
- Better error handling in `list_models()` and `create_chat_completion()`
- Improved `update_api_key()` with validation

**Command Handler (`src/handlers/command_handler.py`)**:
- Improved return type documentation for `handle_command()`
- Enhanced help message formatting
- Better command parsing and validation

**Error Handler (`src/handlers/error_handler.py`)**:
- Added type hints for status message dictionary
- Enhanced `retry_with_backoff()` with comprehensive documentation
- Improved error message formatting

**Chat Handler (`src/handlers/chat_handler.py`)**:
- Added `_check_version_cached()` method implementation
- Improved type hints for all attributes and methods
- Enhanced token usage display formatting
- Better streaming response handling

### Fixed

- Fixed deprecation warning from `pkg_resources` usage
- Fixed inconsistent error message formatting
- Fixed missing type hints causing IDE warnings
- Fixed potential issues with empty API key inputs

### Technical Debt

- Reduced code complexity by simplifying import chains
- Improved code maintainability with better type hints
- Enhanced error handling consistency across all modules
- Better separation of concerns in error handling

## [0.1.23] - Previous Release

Previous version before code quality improvements.

---

## Migration Guide

### For Users

No breaking changes. Simply update to the latest version:

```bash
pip install --upgrade deepseek-cli
```

### For Developers

If you're extending or modifying the codebase:

1. **Import Changes**: The import structure has been simplified but remains backward compatible
2. **Type Hints**: All functions now have proper type hints - update your IDE settings to leverage this
3. **Error Handling**: Use specific exception types instead of generic `Exception` where possible
4. **Console Output**: Use `console.print()` from Rich instead of `print()` for consistency

---

## Notes

- All changes maintain backward compatibility
- No API changes or breaking changes for end users
- Improved developer experience with better type hints and documentation
- Enhanced code quality and maintainability