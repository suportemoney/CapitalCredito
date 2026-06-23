#!/usr/bin/env bash
# Deploy automático — executado no VPS após push na branch primeira-versao
set -euo pipefail

APP_DIR="/home/capitalcredito/sistema-capitalcredito"
VENV="$APP_DIR/ubvenv/bin"
BRANCH="primeira-versao"

cd "$APP_DIR"

echo "==> [1/8] Atualizando código ($BRANCH)"
git fetch origin "$BRANCH"
git checkout "$BRANCH"
# Descarta alterações locais no VPS — o repositório remoto é a fonte de verdade
git reset --hard "origin/$BRANCH"
chmod +x vps/deploy.sh vps/install.sh vps/django.sh vps/sync.sh vps/setup-git-deploy-key.sh

echo "==> [2/8] Dependências Python"
"$VENV/pip" install -r requirements.txt --quiet

echo "==> [3/8] Migrate (sem makemigrations)"
"$VENV/python" manage.py migrate --noinput

echo "==> [4/8] Collectstatic"
"$VENV/python" manage.py collectstatic --noinput

echo "==> [5/8] Sincronizando nginx"
sudo cp vps/capitalcredito-nginx.conf /etc/nginx/sites-available/capitalcredito
sudo ln -sf /etc/nginx/sites-available/capitalcredito /etc/nginx/sites-enabled/capitalcredito
sudo nginx -t
sudo systemctl reload nginx

echo "==> [6/8] Sincronizando systemd e reiniciando Django"
sudo cp vps/capitalcredito.service /etc/systemd/system/capitalcredito.service
sudo systemctl daemon-reload
sudo systemctl restart capitalcredito

echo "==> [7/8] Django check"
"$VENV/python" manage.py check

echo "==> [8/8] Django test"
"$VENV/python" manage.py test

echo "==> Deploy concluído com sucesso"
