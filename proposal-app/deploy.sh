#!/usr/bin/env bash
# ─── Proposal & Contract Generator — Deployment Script ───────────────────────
# Usage: bash deploy.sh
# Deploys the proposal app to root@YOUR_SERVER_IP → /var/www/proposals/
set -e

SERVER="root@YOUR_SERVER_IP"
REMOTE_DIR="/var/www/proposals"
LOCAL_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVER_PASS="YOUR_SERVER_PASSWORD"

SCP="sshpass -p '$SERVER_PASS' scp -o StrictHostKeyChecking=no"
SSH="sshpass -p '$SERVER_PASS' ssh -o StrictHostKeyChecking=no $SERVER"

echo "══════════════════════════════════════════════════"
echo "  Deploying Proposal & Contract Generator"
echo "══════════════════════════════════════════════════"

# ── 1. Create remote directory structure ─────────────────────────────────────
echo "▸ Setting up directories…"
$SSH "mkdir -p $REMOTE_DIR/static $REMOTE_DIR/templates"

# ── 2. Upload app files ───────────────────────────────────────────────────────
echo "▸ Uploading app files…"
sshpass -p "$SERVER_PASS" scp -o StrictHostKeyChecking=no \
    "$LOCAL_DIR/app.py" \
    "$LOCAL_DIR/requirements.txt" \
    "$SERVER:$REMOTE_DIR/"

sshpass -p "$SERVER_PASS" scp -o StrictHostKeyChecking=no -r \
    "$LOCAL_DIR/templates" \
    "$SERVER:$REMOTE_DIR/"

# ── 3. Copy logo from invoice app (already on server) ────────────────────────
echo "▸ Copying logo…"
$SSH "cp /var/www/invoice/static/logo.png $REMOTE_DIR/static/logo.png && echo '  ✓ Logo copied'"

# ── 4. Copy Google OAuth client_secret.json ──────────────────────────────────
echo "▸ Uploading Google client secret…"
CLIENT_SECRET=$(ls "$LOCAL_DIR/../client_secret_"*.json 2>/dev/null | head -1)
if [ -n "$CLIENT_SECRET" ]; then
    sshpass -p "$SERVER_PASS" scp -o StrictHostKeyChecking=no \
        "$CLIENT_SECRET" "$SERVER:$REMOTE_DIR/client_secret.json"
    echo "  ✓ Client secret uploaded"
else
    echo "  ⚠ No client_secret_*.json found — skipping"
fi

# ── 5. Write .env on server ───────────────────────────────────────────────────
echo "▸ Writing .env…"

# Read values from local .env
source "$LOCAL_DIR/../.env" 2>/dev/null || true

sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no "$SERVER" bash << SSHEOF
cat > $REMOTE_DIR/.env << 'ENVEOF'
# Proposal & Contract Generator

PROPOSALS_SECRET_KEY=$(openssl rand -hex 32)

# Fireflies
Fireflies_API_Key=${Fireflies_API_Key}
# Set FIREFLIES_WEBHOOK_SECRET after creating the webhook in Fireflies dashboard:
FIREFLIES_WEBHOOK_SECRET=

# Azure OpenAI (GPT-4.1)
AZURE_OPENAI_API_KEY=${AZURE_OPENAI_API_KEY}
AZURE_OPENAI_ENDPOINT=${AZURE_OPENAI_ENDPOINT}
AZURE_OPENAI_API_VERSION=${AZURE_OPENAI_API_VERSION}

ENVEOF
chmod 600 $REMOTE_DIR/.env
echo "  ✓ .env written"
SSHEOF

# ── 6. Install Python + venv ──────────────────────────────────────────────────
echo "▸ Installing Python dependencies…"
$SSH "cd $REMOTE_DIR && \
    python3 -m venv venv && \
    venv/bin/pip install --upgrade pip --quiet && \
    venv/bin/pip install -r requirements.txt --quiet" && \
    echo "  ✓ Dependencies installed"

# ── 7. Fix permissions ────────────────────────────────────────────────────────
echo "▸ Setting permissions…"
$SSH "chown -R www-data:www-data $REMOTE_DIR && \
    chmod -R 755 $REMOTE_DIR && \
    chmod 600 $REMOTE_DIR/.env"

# ── 8. Install systemd service ────────────────────────────────────────────────
echo "▸ Installing systemd service…"
sshpass -p "$SERVER_PASS" scp -o StrictHostKeyChecking=no \
    "$LOCAL_DIR/proposal-app.service" \
    "$SERVER:/etc/systemd/system/proposal-app.service"
$SSH "systemctl daemon-reload && \
    systemctl enable proposal-app && \
    systemctl restart proposal-app" && \
    echo "  ✓ Service started"

# ── 9. Configure Nginx ────────────────────────────────────────────────────────
echo "▸ Configuring Nginx…"
sshpass -p "$SERVER_PASS" scp -o StrictHostKeyChecking=no \
    "$LOCAL_DIR/nginx.conf" \
    "$SERVER:/etc/nginx/sites-available/proposals"
$SSH "ln -sf /etc/nginx/sites-available/proposals /etc/nginx/sites-enabled/proposals 2>/dev/null || true"

# ── 10. SSL certificate ───────────────────────────────────────────────────────
echo "▸ Obtaining SSL certificate…"
$SSH "certbot --nginx -d proposals.YOUR_DOMAIN --non-interactive \
    --agree-tos -m YOUR_EMAIL 2>&1 | tail -5" && \
    echo "  ✓ SSL obtained"

# Reload nginx
$SSH "nginx -t && systemctl reload nginx" && echo "  ✓ Nginx reloaded"

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════════"
echo "  ✅  Deployment complete!"
echo ""
echo "  Dashboard:  https://proposals.YOUR_DOMAIN"
echo "  Webhook:    https://proposals.YOUR_DOMAIN/webhook/fireflies"
echo "  Trigger:    https://proposals.YOUR_DOMAIN/trigger"
echo ""
echo "  NEXT STEPS:"
echo "  1. Visit https://proposals.YOUR_DOMAIN/auth/google to connect Google"
echo "  2. Set FIREFLIES_WEBHOOK_SECRET in $REMOTE_DIR/.env after creating"
echo "     the webhook in Fireflies → then: systemctl restart proposal-app"
echo "══════════════════════════════════════════════════"
