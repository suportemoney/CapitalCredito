#!/usr/bin/env bash
# Sincronização manual no VPS — descarta alterações locais (igual ao deploy automático)
set -euo pipefail

APP_DIR="/home/capitalcredito/sistema-capitalcredito"
VENV="$APP_DIR/ubvenv/bin"
BRANCH="primeira-versao"
REPO_USER="capitalcredito"

cd "$APP_DIR"

# Git recusa operar se root alterou arquivos e o dono do .git não é o usuário atual
if [[ -d "$APP_DIR/.git" ]]; then
  repo_owner="$(stat -c '%U' "$APP_DIR/.git" 2>/dev/null || echo "")"
  current_user="$(id -un)"
  if [[ -n "$repo_owner" && "$repo_owner" != "$current_user" ]]; then
    echo "Erro: repositório pertence a '$repo_owner', mas você está como '$current_user'."
    echo "Corrija uma vez como root:"
    echo "  chown -R $REPO_USER:$REPO_USER $APP_DIR"
    echo "  sudo -u $REPO_USER git config --global --add safe.directory $APP_DIR"
    exit 1
  fi
fi

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
