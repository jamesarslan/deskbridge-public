#!/usr/bin/env bash
# Interactive Fedora setup; run from a terminal in your graphical session.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
python3 tools/install-fedora.py
python3 src/deskbridge setup
python3 src/deskbridge start
