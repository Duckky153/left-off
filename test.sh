#!/bin/sh
# Left Off: every test. No key, no model, no network.
cd "$(dirname "$0")" || exit 1
set -e
python3 tests/test_rules.py
for s in practice scored fresh fresh2 fresh3 fresh4 fresh5 fresh6; do python3 tests/key_check.py "$s"; done
python3 tests/test_page.py
echo "all tests passed"
