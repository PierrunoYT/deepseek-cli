from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="deepseek-cli",
    version="0.2.0",
    author="PierrunoYT",
    author_email="pierrebruno@hotmail.ch",
    description="A powerful CLI for interacting with DeepSeek's AI models",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/PierrunoYT/deepseek-cli",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.7",
    install_requires=[
        "openai>=1.0.0",
        "requests>=2.31.0",
        "typing-extensions>=4.7.0",
        "pydantic>=2.0.0",
        "setuptools>=42.0.0",
        "rich>=14.0.0",
        "pyfiglet>=1.0.3"
    ],
        entry_points={
        "console_scripts": [
            "deepseek=deepseek_cli.cli.deepseek_cli:main",
        ],
    },
    package_data={
        "": ["*.py", "*.json"],
    },
    include_package_data=True,
)