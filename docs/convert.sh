#!/bin/bash
# convert.sh - Excel转DBC脚本

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

python3 "$PROJECT_ROOT/src/cli.py" convert "$@"
