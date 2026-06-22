#!/usr/bin/env bash
# Configura chave SSH do usuário capitalcredito para git fetch (deploy + sync)
# Executar UMA VEZ no VPS como root:
#   bash vps/setup-git-deploy-key.sh
set -euo pipefail

APP_DIR="/home/capitalcredito/sistema-capitalcredito"
USER="capitalcredito"
KEY="$HOME/.ssh/github_repo_deploy"

if [[ "$(id -un)" == "root" ]]; then
  HOME="/home/capitalcredito"
  KEY="/home/capitalcredito/.ssh/github_repo_deploy"
fi

echo "==> Usuário: $USER"
echo "==> Repositório: $APP_DIR"

sudo -u "$USER" mkdir -p "/home/capitalcredito/.ssh"
sudo -u "$USER" chmod 700 "/home/capitalcredito/.ssh"

if [[ ! -f "$KEY" ]]; then
  echo "==> Gerando chave SSH para GitHub (read-only deploy key)"
  sudo -u "$USER" ssh-keygen -t ed25519 -C "vps-capitalcredito-deploy" -f "$KEY" -N ""
else
  echo "==> Chave já existe: $KEY"
fi

sudo -u "$USER" bash -c "grep -q 'Host github.com' ~/.ssh/config 2>/dev/null || cat >> ~/.ssh/config << 'EOF'
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/github_repo_deploy
  IdentitiesOnly yes
EOF"
sudo -u "$USER" chmod 600 "/home/capitalcredito/.ssh/config"

sudo -u "$USER" git config --global --add safe.directory "$APP_DIR"

# Remote SSH (padrão GitHub)
sudo -u "$USER" git -C "$APP_DIR" remote set-url origin git@github.com:suportemoney/CapitalCredito.git

echo ""
echo "============================================================"
echo "  ADICIONAR DEPLOY KEY NO GITHUB (somente leitura)"
echo "============================================================"
echo ""
echo "GitHub → Repositório CapitalCredito → Settings → Deploy keys → Add deploy key"
echo "Título: VPS capitalcredito"
echo "Chave pública:"
echo ""
sudo -u "$USER" cat "${KEY}.pub"
echo ""
echo "Depois teste:"
echo "  sudo -u capitalcredito ssh -T git@github.com"
echo "  sudo -u capitalcredito bash $APP_DIR/vps/sync.sh"
echo ""
