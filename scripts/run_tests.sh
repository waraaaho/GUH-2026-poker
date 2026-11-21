#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

PYTHON_EXEC=""
for candidate in ".venv/bin/python" "python3.13" "python3.12" "python3.11" "python3.10" "python3"; do
  if command -v "$candidate" >/dev/null 2>&1 || [ -x "$candidate" ]; then
    if "$candidate" -c "import sys; assert sys.version_info >= (3, 10)" >/dev/null 2>&1; then
      PYTHON_EXEC="$candidate"
      break
    fi
  fi
done

if [ -z "$PYTHON_EXEC" ]; then
  echo "[ERROR] Python 3.10+ not found on PATH or in .venv/." >&2
  exit 1
fi

echo "==> Using Python: $PYTHON_EXEC ($("$PYTHON_EXEC" --version))"
"$PYTHON_EXEC" -m pytest tests -q
echo "==> Verifying offline dashboard export..."
"$PYTHON_EXEC" scripts/serve_dashboard.py --build-only --deals 5 --regenerate
echo "==> All offline baseline checks passed."
