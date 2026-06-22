#!/usr/bin/env bash
# Atalho no VPS — sempre usa o venv ubvenv (não o python do sistema)
set -euo pipefail

APP_DIR="/home/capitalcredito/sistema-capitalcredito"
PY="$APP_DIR/ubvenv/bin/python"

if [[ ! -x "$PY" ]]; then
  echo "Erro: venv não encontrado em $PY"
  echo "Crie/reinstale: python3 -m venv ubvenv && ubvenv/bin/pip install -r requirements.txt"
  exit 1
fi

cd "$APP_DIR"
exec "$PY" manage.py "$@"
