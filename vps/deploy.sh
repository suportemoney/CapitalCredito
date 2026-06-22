#!/usr/bin/env bash
# Deploy automático — executado no VPS após push na branch primeira-versao
set -euo pipefail

APP_DIR="/home/capitalcredito/sistema-capitalcredito"
VENV="$APP_DIR/ubvenv/bin"
BRANCH="primeira-versao"

cd "$APP_DIR"
clear

git fetch origin "$BRANCH"
git checkout "$BRANCH"
git pull origin "$BRANCH"

# Apenas migrate — nunca makemigrations no VPS
"$VENV/python" manage.py migrate --noinput
"$VENV/python" manage.py collectstatic --noinput

# Sincronizar configs do repo para o sistema
sudo cp vps/capitalcredito-nginx.conf /etc/nginx/sites-available/capitalcredito
sudo ln -sf /etc/nginx/sites-available/capitalcredito /etc/nginx/sites-enabled/capitalcredito
sudo nginx -t
sudo systemctl reload nginx

sudo cp vps/capitalcredito.service /etc/systemd/system/capitalcredito.service
sudo systemctl daemon-reload
sudo systemctl restart capitalcredito

"$VENV/python" manage.py check
"$VENV/python" manage.py test
