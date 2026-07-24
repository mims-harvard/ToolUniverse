# ToolUniverse Installation Guide

Detailed installation options and troubleshooting.

## Installation Methods

### Method 1: PyPI (Recommended for Users)

Standard installation from Python Package Index:

```bash
pip install tooluniverse
```

**Pros**: Simple, stable, latest release
**Cons**: May not have cutting-edge features

### Method 2: UV (Recommended for MCP)

Installation with uv package manager for better isolation:

```bash
# Install uv first
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create dedicated environment
mkdir -p ~/tooluniverse-env
cd ~/tooluniverse-env

# Install ToolUniverse
uv pip install tooluniverse
```

**Pros**: Better isolation, faster dependency resolution, works well with MCP
**Cons**: Requires uv installation

### Method 3: Development (For Contributors)

Install from source for development:

```bash
git clone https://github.com/mims-harvard/ToolUniverse.git
cd ToolUniverse
pip install -e .
```

**Pros**: Latest features, can modify code
**Cons**: May have bugs, requires git

## Optional Dependencies

### All Features

```bash
pip install tooluniverse[all]
```

### Specific Features

```bash
# Single-cell analysis
pip install tooluniverse[singlecell]

# Machine learning and embeddings
pip install tooluniverse[ml,embedding]

# Visualization tools
pip install tooluniverse[visualization]

# Graph analysis
pip install tooluniverse[graph]

# Bioinformatics tools
pip install tooluniverse[bioinformatics]

# Development tools
pip install tooluniverse[dev]
```

## Python Version Requirements

- **Required**: Python 3.10 - 3.13
- **Not supported**: Python <3.10 or >=3.14

### Installing Specific Python Version

#### macOS (Homebrew)

```bash
brew install python@3.12
python3.12 -m pip install tooluniverse
```

#### Ubuntu/Debian

```bash
sudo apt update
sudo apt install python3.12 python3.12-pip
python3.12 -m pip install tooluniverse
```

#### Windows

Download from [python.org](https://www.python.org/downloads/) and select version 3.12.

## Virtual Environment (Recommended)

Create isolated environment:

```bash
# Create virtual environment
python3 -m venv tooluniverse-venv

# Activate
source tooluniverse-venv/bin/activate  # macOS/Linux
# or
tooluniverse-venv\Scripts\activate  # Windows

# Install
pip install tooluniverse
```

## Verification

After installation, verify:

```bash
# Check installation
pip show tooluniverse

# Test import
python3 -c "from tooluniverse import ToolUniverse; print('✓ Import successful')"

# Check CLI commands
which tooluniverse-smcp-stdio
```

## Common Installation Issues

### Issue: pip not found

```bash
# macOS/Linux
python3 -m ensurepip --upgrade

# Windows
py -m ensurepip --upgrade
```

### Issue: Permission denied

```bash
# Use user installation
pip install --user tooluniverse

# Or use virtual environment (recommended)
```

### Issue: SSL certificate error

```bash
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org tooluniverse
```

### Issue: Outdated pip

```bash
pip install --upgrade pip
pip install tooluniverse
```

## Uninstallation

```bash
pip uninstall tooluniverse
```

To remove all data:

```bash
# Remove cache (if exists)
rm -rf ~/.cache/tooluniverse
```

## Upgrading

```bash
pip install --upgrade tooluniverse
```

## Platform-Specific Notes

### macOS

- Use Homebrew Python recommended
- May need Xcode Command Line Tools: `xcode-select --install`

### Windows

- Use official Python installer
- Add Python to PATH during installation
- May need Microsoft C++ Build Tools for some dependencies

### Linux

- Most distros work out of the box
- May need `python3-dev` package for compiling dependencies
