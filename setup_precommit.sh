#!/bin/bash
# Auto-setup script for pre-commit hooks and development environment
# Run this after cloning the repository.
#
# What it does:
#   1. Installs the pre-commit framework and hooks

set -e

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_ROOT"

echo "🔧 Setting up development environment for ToolUniverse..."

# --- 1. Pre-commit hooks ---

# Check if .pre-commit-config.yaml exists
if [ ! -f ".pre-commit-config.yaml" ]; then
    echo "❌ .pre-commit-config.yaml not found in current directory"
    exit 1
fi

# Check if pre-commit is installed
if ! command -v pre-commit &> /dev/null; then
    echo "Installing pre-commit..."
    pip install pre-commit
    echo "✅ pre-commit installed successfully"
else
    echo "✅ pre-commit is already installed"
fi

# Install pre-commit hooks
echo "Installing pre-commit hooks..."
pre-commit install
echo "✅ pre-commit hooks installed successfully"

echo ""
echo "🎉 Setup completed successfully!"
echo "📝 Pre-commit hooks will now run automatically on every commit."
echo "💡 To run hooks manually: pre-commit run --all-files"
