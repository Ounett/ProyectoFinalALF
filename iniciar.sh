#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: Instala Python 3 con: sudo apt install python3" >&2
  exit 2
fi
python3 - <<'PY'
import sys
if sys.version_info < (3, 9):
    raise SystemExit('ERROR: Python 3.9 o superior es necesario.')
PY
exec python3 -m erafd.web.server "$@"
