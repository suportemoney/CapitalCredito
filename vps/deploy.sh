#!/usr/bin/env bash
# Deploy automático — executado no VPS após push na branch primeira-versao
set -euo pipefail

APP_DIR="/home/capitalcredito/sistema-capitalcredito"
VENV="$APP_DIR/ubvenv/bin"
BRANCH="primeira-versao"

cd "$APP_DIR"

echo "==> [1/7] Atualizando código ($BRANCH)"
git fetch origin "$BRANCH"
git checkout "$BRANCH"
# Descarta alterações locais no VPS — o repositório remoto é a fonte de verdade
git reset --hard "origin/$BRANCH"
chmod +x vps/deploy.sh vps/install.sh vps/django.sh vps/sync.sh vps/setup-git-deploy-key.sh

echo "==> [2/7] Migrate (sem makemigrations)"
"$VENV/python" manage.py migrate --noinput

echo "==> [3/7] Collectstatic"
"$VENV/python" manage.py collectstatic --noinput

echo "==> [4/7] Sincronizando nginx"
sudo cp vps/capitalcredito-nginx.conf /etc/nginx/sites-available/capitalcredito
sudo ln -sf /etc/nginx/sites-available/capitalcredito /etc/nginx/sites-enabled/capitalcredito
sudo nginx -t
sudo systemctl reload nginx

echo "==> [5/7] Sincronizando systemd e reiniciando Django"
sudo cp vps/capitalcredito.service /etc/systemd/system/capitalcredito.service
sudo systemctl daemon-reload
sudo systemctl restart capitalcredito

echo "==> [6/7] Django check"
"$VENV/python" manage.py check

echo "==> [7/7] Django test"
"$VENV/python" manage.py test

echo "==> Deploy concluído com sucesso"
