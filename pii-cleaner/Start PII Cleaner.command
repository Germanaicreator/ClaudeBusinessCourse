#!/bin/bash
# ── PII Cleaner — one-click launcher ──────────────────────────────────────
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo ""
echo "  ╔══════════════════════════════════╗"
echo "  ║        PII Cleaner               ║"
echo "  ║  Document Anonymizer             ║"
echo "  ╚══════════════════════════════════╝"
echo ""

# Kill any old instance on port 5055
if lsof -ti:5055 &>/dev/null; then
  echo "  → Stopping previous instance..."
  kill $(lsof -ti:5055) 2>/dev/null || true
  sleep 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
  echo "  → Creating virtual environment (first run only)..."
  python3 -m venv venv
fi

source venv/bin/activate

# Install / update dependencies
echo "  → Installing dependencies..."
pip install -r requirements.txt -q --upgrade

echo ""
echo "  Starting server at http://127.0.0.1:5055"
echo "  Chrome will open automatically."
echo ""
echo "  Press Ctrl+C to stop."
echo ""

python app.py
