#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# deploy.sh — Deploy Email Analyzer to server
# Usage: bash deploy.sh
# Requires: sshpass (brew install sshpass)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# Load credentials from .env
if [ -f "$REPO_ROOT/.env" ]; then
  export $(grep -v '^#' "$REPO_ROOT/.env" | xargs)
fi

SERVER_IP="YOUR_SERVER_IP"
SERVER_USER="root"
SERVER_PASS="${Password}"
REMOTE_DIR="/opt/emailanalyzer"

echo "▶  Deploying Email Analyzer to $SERVER_USER@$SERVER_IP:$REMOTE_DIR"

# ── Copy files to server ──────────────────────────────────────────────────────
echo "▶  Uploading files …"
sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_IP" \
  "mkdir -p $REMOTE_DIR"

for FILE in email_analyzer.py whitelist.txt requirements.txt; do
  sshpass -p "$SERVER_PASS" scp -o StrictHostKeyChecking=no \
    "$SCRIPT_DIR/$FILE" "$SERVER_USER@$SERVER_IP:$REMOTE_DIR/"
done

# Copy logo from invoice-app static folder (same logo, same brand)
LOGO_SRC="$REPO_ROOT/invoice-app/static/logo.png"
if [ -f "$LOGO_SRC" ]; then
  echo "▶  Uploading logo from invoice-app …"
  sshpass -p "$SERVER_PASS" scp -o StrictHostKeyChecking=no \
    "$LOGO_SRC" "$SERVER_USER@$SERVER_IP:$REMOTE_DIR/logo.png"
else
  echo "⚠   Logo not found at $LOGO_SRC — fetching from server invoice-app …"
  sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_IP" \
    "cp /var/www/invoice/static/logo.png $REMOTE_DIR/logo.png 2>/dev/null || echo 'WARNING: logo not found on server either'"
fi

# Copy .env so the app can load credentials
echo "▶  Uploading .env …"
sshpass -p "$SERVER_PASS" scp -o StrictHostKeyChecking=no \
  "$REPO_ROOT/.env" "$SERVER_USER@$SERVER_IP:$REMOTE_DIR/.env"

# ── Remote setup ─────────────────────────────────────────────────────────────
echo "▶  Running remote setup …"
sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_IP" << 'REMOTE'
set -e
cd /opt/emailanalyzer

# Create virtualenv if it doesn't exist
if [ ! -d venv ]; then
  echo "  Creating virtualenv …"
  python3 -m venv venv
fi

# Install / upgrade dependencies
echo "  Installing Python dependencies …"
venv/bin/pip install --quiet --upgrade pip
venv/bin/pip install --quiet -r requirements.txt

# Install / update systemd service
echo "  Installing systemd service …"
REMOTE
sshpass -p "$SERVER_PASS" scp -o StrictHostKeyChecking=no \
  "$SCRIPT_DIR/email_analyzer.service" \
  "$SERVER_USER@$SERVER_IP:/etc/systemd/system/email-analyzer.service"

sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_IP" << 'REMOTE'
systemctl daemon-reload
systemctl enable email-analyzer
systemctl restart email-analyzer
sleep 2
echo ""
echo "─── Service status ───────────────────────────────────────"
systemctl status email-analyzer --no-pager -l | head -30
echo "──────────────────────────────────────────────────────────"
echo ""
echo "✓  Email Analyzer deployed and running."
echo "   Logs: journalctl -u email-analyzer -f"
echo "   File: /opt/emailanalyzer/email_analyzer.log"
REMOTE
