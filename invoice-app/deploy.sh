#!/usr/bin/env bash
# ─── AI Experts Invoice App — Deployment Script ───────────────────────────
# Usage: bash deploy.sh
# Deploys the invoice app to root@YOUR_SERVER_IP → /var/www/invoice/
set -e

SERVER="root@YOUR_SERVER_IP"
REMOTE_DIR="/var/www/invoice"
LOCAL_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVER_PASS="YOUR_SERVER_PASSWORD"

# Required: sshpass  →  brew install hudochenkov/sshpass/sshpass
SCP="sshpass -p '$SERVER_PASS' scp -o StrictHostKeyChecking=no"
SSH="sshpass -p '$SERVER_PASS' ssh -o StrictHostKeyChecking=no $SERVER"

echo "──────────────────────────────────────────"
echo "  Deploying AI Experts Invoice Dashboard"
echo "──────────────────────────────────────────"

# ── 1. Create remote directory structure ────────────────────────────────────
echo "▸ Setting up directories…"
$SSH "mkdir -p $REMOTE_DIR/static $REMOTE_DIR/templates $REMOTE_DIR/invoices"

# ── 2. Upload Python app + templates + static ──────────────────────────────
echo "▸ Uploading app files…"
sshpass -p "$SERVER_PASS" scp -o StrictHostKeyChecking=no \
    "$LOCAL_DIR/app.py" \
    "$LOCAL_DIR/requirements.txt" \
    "$SERVER:$REMOTE_DIR/"

sshpass -p "$SERVER_PASS" scp -o StrictHostKeyChecking=no -r \
    "$LOCAL_DIR/templates" \
    "$LOCAL_DIR/static" \
    "$SERVER:$REMOTE_DIR/"

# ── 3. Upload logo ──────────────────────────────────────────────────────────
echo "▸ Uploading logo…"
LOGO_PATH="$(dirname "$LOCAL_DIR")/logo_big_white.png"
if [ -f "$LOGO_PATH" ]; then
    sshpass -p "$SERVER_PASS" scp -o StrictHostKeyChecking=no \
        "$LOGO_PATH" "$SERVER:$REMOTE_DIR/static/logo.png"
    echo "  ✓ Logo uploaded"
else
    echo "  ⚠ Logo not found at $LOGO_PATH — skipping"
fi

# ── 4. Create .env on server (if not exists) ──────────────────────────────
echo "▸ Configuring .env…"
$SSH "cat > $REMOTE_DIR/.env << 'ENVEOF'
# AI Experts Invoice Dashboard Configuration
DASHBOARD_PASSWORD=changeme123
SECRET_KEY=$(openssl rand -hex 32 2>/dev/null || echo 'please-change-this-secret-key')
STARTING_INVOICE_NUMBER=2026001

# Company Details (shown on invoices)
COMPANY_NAME=AI Experts
COMPANY_ADDRESS=Musterstraße 1 · 10115 Berlin · Germany
COMPANY_TAX_NUMBER=000/000/00000
COMPANY_VAT_ID=DE000000000
COMPANY_EMAIL=YOUR_EMAIL
COMPANY_PHONE=+49 000 000 0000
COMPANY_IBAN=DE13 1001 0000 0628 1929 21
COMPANY_BIC=FINOM DE82
COMPANY_BANK=FINOM PAYMENTS
COMPANY_WEBSITE=https://YOUR_DOMAIN

# Email Configuration (set SMTP_USER + SMTP_PASSWORD to enable email sending)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
FROM_EMAIL=
ENVEOF"
echo "  ✓ .env written (please update passwords + company details!)"

# ── 5. Install system dependencies for WeasyPrint ──────────────────────────
echo "▸ Installing system dependencies…"
$SSH "apt-get update -q && apt-get install -y -q \
    python3 python3-pip python3-venv \
    libpango-1.0-0 libpangocairo-1.0-0 libcairo2 \
    libgdk-pixbuf2.0-0 libffi-dev shared-mime-info \
    > /dev/null 2>&1" && echo "  ✓ System packages installed"

# ── 6. Create Python venv + install requirements ───────────────────────────
echo "▸ Setting up Python environment…"
$SSH "cd $REMOTE_DIR && \
    python3 -m venv venv && \
    venv/bin/pip install --upgrade pip --quiet && \
    venv/bin/pip install -r requirements.txt --quiet" && \
    echo "  ✓ Python dependencies installed"

# ── 7. Initialize database ─────────────────────────────────────────────────
echo "▸ Initialising database…"
$SSH "cd $REMOTE_DIR && \
    venv/bin/python -c 'import app; app.init_db(); print(\"  DB OK\")"

# ── 8. Fix permissions ─────────────────────────────────────────────────────
echo "▸ Setting permissions…"
$SSH "chown -R www-data:www-data $REMOTE_DIR && \
    chmod -R 755 $REMOTE_DIR && \
    chmod 600 $REMOTE_DIR/.env"

# ── 9. Install + start systemd service ────────────────────────────────────
echo "▸ Installing systemd service…"
sshpass -p "$SERVER_PASS" scp -o StrictHostKeyChecking=no \
    "$LOCAL_DIR/invoice-app.service" \
    "$SERVER:/etc/systemd/system/invoice-app.service"
$SSH "systemctl daemon-reload && \
    systemctl enable invoice-app && \
    systemctl restart invoice-app" && \
    echo "  ✓ Service started"

# ── 10. Configure Nginx ────────────────────────────────────────────────────
echo "▸ Configuring Nginx…"
sshpass -p "$SERVER_PASS" scp -o StrictHostKeyChecking=no \
    "$LOCAL_DIR/nginx.conf" \
    "$SERVER:/etc/nginx/sites-available/invoice"
$SSH "ln -sf /etc/nginx/sites-available/invoice /etc/nginx/sites-enabled/invoice 2>/dev/null || true"

# ── 11. SSL Certificate ────────────────────────────────────────────────────
echo "▸ Obtaining SSL certificate…"
$SSH "certbot --nginx -d invoice.YOUR_DOMAIN --non-interactive \
    --agree-tos -m YOUR_EMAIL 2>&1 | tail -5" && \
    echo "  ✓ SSL certificate obtained"

# Reload nginx
$SSH "nginx -t && systemctl reload nginx" && echo "  ✓ Nginx reloaded"

# ── Done ───────────────────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════"
echo "  ✅  Deployment complete!"
echo ""
echo "  Dashboard: https://invoice.YOUR_DOMAIN"
echo ""
echo "  ⚠ NEXT STEPS:"
echo "  1. Set a strong DASHBOARD_PASSWORD in $REMOTE_DIR/.env"
echo "  2. Fill in your COMPANY details in $REMOTE_DIR/.env"
echo "  3. Set SMTP_USER + SMTP_PASSWORD to enable email"
echo "  4. Restart: systemctl restart invoice-app"
echo "══════════════════════════════════════════"
