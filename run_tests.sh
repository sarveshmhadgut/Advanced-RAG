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
    echo -e "${YELLOW}==> Auto-fixing code formatting and import sorting...${NC}"
    uvx ruff check --select I --fix src/
    uvx ruff format src/
    echo
fi

echo -e "${BLUE}==> [1/5] Checking code formatting (ruff)...${NC}"
uvx ruff format --check src/

echo -e "${BLUE}==> [2/5] Checking import sorting (ruff isort)...${NC}"
uvx ruff check --select I src/

echo -e "${BLUE}==> [3/5] Linting code (ruff)...${NC}"
uvx ruff check src/

echo -e "${BLUE}==> [4/5] Type checking (mypy)...${NC}"
uvx mypy src --explicit-package-bases --ignore-missing-imports

echo -e "${BLUE}==> [5/5] Running unit tests (pytest)...${NC}"
uv run pytest tests

echo -e "\n${GREEN}✔ All checks passed successfully!${NC}"
