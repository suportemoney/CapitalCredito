#!/usr/bin/env bash
# Setup único no VPS — executar uma vez após clonar o repositório
set -euo pipefail

APP_DIR="/home/capitalcredito/sistema-capitalcredito"

cd "$APP_DIR"

echo "==> Configurando permissões dos scripts de deploy"
chmod +x vps/deploy.sh
chmod +x vps/install.sh

echo "==> Instalando unit systemd capitalcredito"
sudo cp vps/capitalcredito.service /etc/systemd/system/capitalcredito.service
sudo systemctl daemon-reload
sudo systemctl enable capitalcredito

echo "==> Instalando config nginx"
sudo cp vps/capitalcredito-nginx.conf /etc/nginx/sites-available/capitalcredito
sudo ln -sf /etc/nginx/sites-available/capitalcredito /etc/nginx/sites-enabled/capitalcredito
sudo nginx -t
sudo systemctl enable nginx

echo "==> Iniciando serviços"
sudo systemctl restart capitalcredito
sudo systemctl reload nginx

echo ""
echo "============================================================"
echo "  PRÓXIMOS PASSOS — GitHub Actions (deploy automático)"
echo "============================================================"
echo ""
echo "1. Gerar chave SSH dedicada para o GitHub Actions (no VPS):"
echo "   ssh-keygen -t ed25519 -C 'github-actions-deploy' -f ~/.ssh/github_actions_deploy -N ''"
echo ""
echo "2. Autorizar a chave pública no VPS:"
echo "   cat ~/.ssh/github_actions_deploy.pub >> ~/.ssh/authorized_keys"
echo "   chmod 600 ~/.ssh/authorized_keys"
echo ""
echo "3. Copiar a chave PRIVADA e cadastrar no GitHub:"
echo "   Repositório → Settings → Secrets and variables → Actions → New repository secret"
echo ""
echo "   Secret              | Valor"
echo "   --------------------|------------------------------------------"
echo "   VPS_HOST            | 168.231.97.235 (ou sistema.capitalcredito.net)"
echo "   VPS_USER            | capitalcredito"
echo "   VPS_SSH_KEY         | conteúdo de ~/.ssh/github_actions_deploy"
echo ""
echo "4. Testar o deploy:"
echo "   git push origin primeira-versao"
echo "   Acompanhar em: GitHub → Actions → Deploy VPS"
echo "   Logs do serviço: journalctl -u capitalcredito -f"
echo ""
echo "Setup concluído."
