#!/usr/bin/env bash
# Unix 兼容入口；实际校验与生成逻辑在跨平台 build-report.py。
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
exec "$PYTHON_BIN" "$SCRIPT_DIR/build-report.py" "$@"
