#!/usr/bin/env bash
# Sincronização manual no VPS — descarta alterações locais (igual ao deploy automático)
set -euo pipefail

APP_DIR="/home/capitalcredito/sistema-capitalcredito"
VENV="$APP_DIR/ubvenv/bin"
BRANCH="primeira-versao"

cd "$APP_DIR"

echo "==> Atualizando código ($BRANCH) — reset hard (descarta mudanças locais)"
git fetch origin "$BRANCH"
git checkout "$BRANCH"
git reset --hard "origin/$BRANCH"
chmod +x vps/deploy.sh vps/install.sh vps/django.sh vps/sync.sh 2>/dev/null || true

echo "==> Migrate"
"$VENV/python" manage.py migrate --noinput

echo "==> Collectstatic"
"$VENV/python" manage.py collectstatic --noinput

echo "==> Check"
"$VENV/python" manage.py check

echo ""
echo "Concluído. Reinicie o serviço:"
echo "  sudo systemctl restart capitalcredito"
