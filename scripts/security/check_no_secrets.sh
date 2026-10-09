#!/usr/bin/env bash
set -euo pipefail
# Markdown is included; value exceptions and redaction live in the Python scanner.
if command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
else
  PYTHON=python
fi
exec "$PYTHON" "$(dirname "${BASH_SOURCE[0]}")/scan_tracked_secrets.py"
