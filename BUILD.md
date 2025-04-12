# Building and Publishing the Package

## Modern Build Process

Use Python's build module instead of setup.py directly:

```bash
# Install build tools
pip install build twine

# Clean previous builds
rm -rf build/ dist/ src/deepseek_cli.egg-info/

# Build the package
python -m build

# Check distribution files
twine check dist/*

# Upload to PyPI (requires PyPI token)
# Set token as environment variable for security
export TWINE_PASSWORD="your-pypi-token"
twine upload dist/* --username __token__
```

## Package Configuration

This project now uses pyproject.toml for modern Python packaging. The configuration includes:

- Package metadata (name, version, description)
- License information (MIT)
- Python version requirements (>=3.7)
- Dependencies
- Entry points for the CLI tool
- Package discovery settings

The pyproject.toml approach is preferred over setup.py as it follows PEP 621 standards and avoids setuptools deprecation warnings.