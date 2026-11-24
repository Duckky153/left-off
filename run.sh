#!/bin/sh
# Left Off: the page at http://127.0.0.1:5141/ (PORT overrides). No key, no model: it shows the saved run.
cd "$(dirname "$0")"
PORT="${PORT:-5141}"
echo "Left Off: http://127.0.0.1:$PORT/"
exec python3 -m http.server "$PORT" --bind 127.0.0.1 --directory site
