#!/usr/bin/env bash
# ─── AI Experts Business Command Center — Deployment Script ──────────────────
# Deploys to root@YOUR_SERVER_IP → /var/www/controlcenter/
set -e

SERVER="root@YOUR_SERVER_IP"
REMOTE_DIR="/var/www/controlcenter"
LOCAL_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$LOCAL_DIR")"
SERVER_PASS="YOUR_SERVER_PASSWORD"

SCP="sshpass -p '$SERVER_PASS' scp -o StrictHostKeyChecking=no"
SSH="sshpass -p '$SERVER_PASS' ssh -o StrictHostKeyChecking=no $SERVER"

echo "════════════════════════════════════════════"
echo "  Deploying Business Command Center"
echo "════════════════════════════════════════════"

# ── 1. Directory structure ─────────────────────────────────────────────────
echo "▸ Setting up directories…"
$SSH "mkdir -p $REMOTE_DIR/templates $REMOTE_DIR/static $REMOTE_DIR/media/linkedin $REMOTE_DIR/media/blog"

# ── 2. Upload app files ────────────────────────────────────────────────────
echo "▸ Uploading app files…"
sshpass -p "$SERVER_PASS" scp -o StrictHostKeyChecking=no \
    "$LOCAL_DIR/app.py" \
    "$LOCAL_DIR/pii_blueprint.py" \
    "$LOCAL_DIR/requirements.txt" \
    "$SERVER:$REMOTE_DIR/"

sshpass -p "$SERVER_PASS" scp -o StrictHostKeyChecking=no -r \
    "$LOCAL_DIR/templates" \
    "$LOCAL_DIR/static" \
    "$SERVER:$REMOTE_DIR/"

# ── 3. Upload media content ────────────────────────────────────────────────
echo "▸ Uploading media content…"

# LinkedIn posts JSON
if [ -f "$PROJECT_DIR/linkedin/posts.json" ]; then
    sshpass -p "$SERVER_PASS" scp -o StrictHostKeyChecking=no \
        "$PROJECT_DIR/linkedin/posts.json" \
        "$SERVER:$REMOTE_DIR/media/"
    echo "  ✓ LinkedIn posts.json uploaded"
fi

# LinkedIn images
if [ -d "$PROJECT_DIR/linkedin/images" ]; then
    sshpass -p "$SERVER_PASS" scp -o StrictHostKeyChecking=no -r \
        "$PROJECT_DIR/linkedin/images/." \
        "$SERVER:$REMOTE_DIR/media/linkedin/"
    echo "  ✓ LinkedIn images uploaded"
fi

# YouTube videos JSON
if [ -f "$PROJECT_DIR/youtube/videos.json" ]; then
    sshpass -p "$SERVER_PASS" scp -o StrictHostKeyChecking=no \
        "$PROJECT_DIR/youtube/videos.json" \
        "$SERVER:$REMOTE_DIR/media/"
    echo "  ✓ YouTube videos.json uploaded"
fi

# Blog posts data (generate from existing blog directory)
echo "▸ Generating blog posts data from live site…"
$SSH "python3 - << 'PYEOF'
import json, os, re
from pathlib import Path

posts_dir = Path('/var/www/aiexperts/blog/posts')
posts = []
if posts_dir.exists():
    for slug_dir in sorted(posts_dir.iterdir()):
        index_file = slug_dir / 'index.html'
        if not index_file.exists():
            continue
        html = index_file.read_text(errors='ignore')
        title_m = re.search(r'<title[^>]*>([^<]+)</title>', html)
        title = title_m.group(1).split('|')[0].strip() if title_m else slug_dir.name
        img_m = re.search(r'header\.jpg|header\.png|og:image.*?content=\"([^\"]+)\"', html)
        posts.append({
            'slug': slug_dir.name,
            'blog_title': title,
            'blog_url': f'https://YOUR_DOMAIN/blog/posts/{slug_dir.name}/',
            'image_url': f'/media/blog/{slug_dir.name}/header.jpg',
        })

data = {'posts': posts}
out = Path('$REMOTE_DIR/media/blog_posts.json')
out.write_text(json.dumps(data, indent=2))
print(f'  wrote {len(posts)} blog posts to blog_posts.json')
PYEOF"

# Copy blog header images to media/blog/
$SSH "for d in /var/www/aiexperts/blog/posts/*/; do
  slug=\$(basename \$d)
  mkdir -p $REMOTE_DIR/media/blog/\$slug
  [ -f \$d/header.jpg ] && cp \$d/header.jpg $REMOTE_DIR/media/blog/\$slug/ 2>/dev/null || true
  [ -f \$d/header.png ] && cp \$d/header.png $REMOTE_DIR/media/blog/\$slug/ 2>/dev/null || true
done
echo '  ✓ Blog images copied'"

# ── 4. Read existing .env values for the CC_SSO_SECRET ────────────────────
echo "▸ Configuring .env…"
# Read existing password from server if it exists, otherwise set defaults
$SSH "if [ ! -f $REMOTE_DIR/.env ]; then
cat > $REMOTE_DIR/.env << 'ENVEOF'
# Business Command Center Configuration
CC_PASSWORD=changeme123
CC_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
CC_SSO_SECRET=$(python3 -c 'import secrets; print(secrets.token_hex(32))')

# Invoice app URL for SSO
INVOICE_URL=https://invoice.YOUR_DOMAIN

# Azure OpenAI (for PII Cleaner)
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2024-12-01-preview
ENVEOF
echo '  ✓ .env created (update CC_PASSWORD, CC_SSO_SECRET, and Azure keys!)'
else
echo '  ✓ .env already exists — not overwriting'
fi"

# ── 5. Install system dependencies ────────────────────────────────────────
echo "▸ Installing system dependencies…"
$SSH "apt-get update -q && apt-get install -y -q python3 python3-pip python3-venv > /dev/null 2>&1"
echo "  ✓ System packages ready"

# ── 6. Python venv ────────────────────────────────────────────────────────
echo "▸ Setting up Python environment…"
$SSH "cd $REMOTE_DIR && \
    python3 -m venv venv && \
    venv/bin/pip install --upgrade pip --quiet && \
    venv/bin/pip install -r requirements.txt --quiet"
echo "  ✓ Python dependencies installed"

# ── 7. Permissions ────────────────────────────────────────────────────────
echo "▸ Setting permissions…"
$SSH "chown -R www-data:www-data $REMOTE_DIR && \
    chmod -R 755 $REMOTE_DIR && \
    chmod 600 $REMOTE_DIR/.env"

# ── 8. Systemd service ────────────────────────────────────────────────────
echo "▸ Installing systemd service…"
sshpass -p "$SERVER_PASS" scp -o StrictHostKeyChecking=no \
    "$LOCAL_DIR/command-center.service" \
    "$SERVER:/etc/systemd/system/command-center.service"
$SSH "systemctl daemon-reload && \
    systemctl enable command-center && \
    systemctl restart command-center"
echo "  ✓ Service started"

# ── 9. Nginx ──────────────────────────────────────────────────────────────
echo "▸ Configuring Nginx…"
sshpass -p "$SERVER_PASS" scp -o StrictHostKeyChecking=no \
    "$LOCAL_DIR/nginx.conf" \
    "$SERVER:/etc/nginx/sites-available/controlcenter"
$SSH "ln -sf /etc/nginx/sites-available/controlcenter /etc/nginx/sites-enabled/controlcenter 2>/dev/null || true"

# ── 10. SSL Certificate ───────────────────────────────────────────────────
echo "▸ Obtaining SSL certificate…"
$SSH "certbot --nginx -d controlcenter.YOUR_DOMAIN --non-interactive \
    --agree-tos -m YOUR_EMAIL 2>&1 | tail -5"
echo "  ✓ SSL certificate obtained"

$SSH "nginx -t && systemctl reload nginx"
echo "  ✓ Nginx reloaded"

# ── 11. Sync the CC_SSO_SECRET to the invoice app ────────────────────────
echo "▸ Syncing SSO secret to invoice app…"
$SSH "CC_SSO_SECRET=\$(grep CC_SSO_SECRET $REMOTE_DIR/.env | cut -d= -f2)
if grep -q 'CC_SSO_SECRET' /var/www/invoice/.env 2>/dev/null; then
    sed -i \"s|CC_SSO_SECRET=.*|CC_SSO_SECRET=\$CC_SSO_SECRET|\" /var/www/invoice/.env
else
    echo \"CC_SSO_SECRET=\$CC_SSO_SECRET\" >> /var/www/invoice/.env
fi
systemctl restart invoice-app
echo '  ✓ SSO secret synced to invoice app'"

# ── Done ──────────────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════"
echo "  ✅  Deployment complete!"
echo ""
echo "  Dashboard: https://controlcenter.YOUR_DOMAIN"
echo ""
echo "  ⚠ NEXT STEPS:"
echo "  1. Set a strong CC_PASSWORD in $REMOTE_DIR/.env"
echo "  2. Set Azure OpenAI keys in $REMOTE_DIR/.env (for PII Cleaner)"
echo "  3. Restart: systemctl restart command-center"
echo "════════════════════════════════════════════"
