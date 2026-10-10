#!/usr/bin/env bash
set -e

# ANSI Color Codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check for --fix flag
if [ "$1" == "--fix" ]; then
    echo -e "${YELLOW}==> Auto-fixing code formatting, import sorting, and lint issues...${NC}"
    uvx ruff check --fix src/ tests/
    uvx ruff format src/ tests/
    echo
fi

echo -e "${BLUE}==> [1/6] Installing/syncing dependencies (uv sync)...${NC}"
uv sync --all-extras --dev

echo -e "${BLUE}==> [2/6] Checking code formatting (ruff)...${NC}"
uvx ruff format --check src/ tests/

echo -e "${BLUE}==> [3/6] Checking import sorting (ruff isort)...${NC}"
uvx ruff check --select I src/ tests/

echo -e "${BLUE}==> [4/6] Linting code (ruff)...${NC}"
uvx ruff check src/ tests/


echo -e "${BLUE}==> [5/6] Type checking (mypy)...${NC}"
uvx mypy src --explicit-package-bases --ignore-missing-imports

echo -e "${BLUE}==> [6/6] Running unit tests (pytest)...${NC}"
GOOGLE_API_KEY="${GOOGLE_API_KEY:-goofy-ahh-google-key}" \
LANGCHAIN_API_KEY="${LANGCHAIN_API_KEY:-goofy-ahh-langchain-key}" \
uv run pytest tests

echo -e "\n${GREEN}All checks passed successfully!${NC}"
