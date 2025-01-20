from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="deepseek-cli",
    version="0.1.0",
    author="DeepSeek",
    author_email="api-service@deepseek.com",
    description="A command-line interface for the DeepSeek API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://platform.deepseek.com",
    packages=find_packages(include=['src', 'src.*']),
    package_data={
        'src': ['**/*.py'],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=[
        "openai==1.6.1",
        "typing-extensions>=4.5.0",
        "requests>=2.31.0",
        "argparse>=1.4.0",
    ],
    entry_points={
        "console_scripts": [
            "deepseek=src.cli.deepseek_cli:main",
        ],
    },
) 