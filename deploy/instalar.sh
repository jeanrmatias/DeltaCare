#!/usr/bin/env bash
# Instala o Delta Care num servidor Ubuntu 24.04 novo, do zero. Como root:
#
#     DOMINIO=deltacare.duckdns.org bash instalar.sh
#
# Faz os passos da seção "Implantação" do README: pacotes, usuário, código,
# build das telas, Ollama (só para os embeddings), serviço, Caddy com HTTPS,
# firewall e as rotinas diárias. Pode rodar de novo: o que já existe fica.
#
# Duas coisas ficam de fora, de propósito, e o script avisa no fim:
#   - preencher /etc/deltacare.env (e-mail SMTP, chave do Ollama Cloud);
#   - criar a primeira administração (scripts/criar_admin.py pergunta a
#     senha no terminal, e ela não deve passar por mais ninguém).

set -euo pipefail

main() {
  : "${DOMINIO:?Defina o domínio. Ex.: DOMINIO=deltacare.duckdns.org bash instalar.sh}"
  REPO="${REPO:-https://github.com/jeanrmatias/DeltaCare.git}"
  APP=/opt/deltacare
  DADOS=/var/lib/deltacare

  [ "$(id -u)" -eq 0 ] || { echo "Rode como root."; exit 1; }

  echo "==> Pacotes do sistema"
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -q
  apt-get install -y -q python3-venv git curl sqlite3 ufw gpg debian-keyring debian-archive-keyring apt-transport-https

  # Memória de troca: o build das telas e o Ollama dividem 4 GB. Sem swap, um
  # pico durante o build derruba o processo em vez de só ficar mais lento.
  if ! swapon --show | grep -q /swapfile; then
    fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
    grep -q /swapfile /etc/fstab || echo "/swapfile none swap sw 0 0" >> /etc/fstab
  fi

  # Node 22: o Vite 8 pede Node 20.19 ou mais, e o do Ubuntu é mais velho. Só
  # serve para compilar as telas; o sistema no ar não usa Node.
  if ! command -v node >/dev/null || [ "$(node -p 'process.versions.node.split(".")[0]')" -lt 22 ]; then
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
    apt-get install -y -q nodejs
  fi

  if ! command -v caddy >/dev/null; then
    curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/gpg.key | gpg --dearmor --yes -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt > /etc/apt/sources.list.d/caddy-stable.list
    apt-get update -q && apt-get install -y -q caddy
  fi

  # Ollama local só para os embeddings (nomic-embed-text, leve, roda sem GPU).
  # A resposta do chat vai para o Ollama Cloud (OLLAMA_CHAT_URL no .env).
  if ! command -v ollama >/dev/null; then
    curl -fsSL https://ollama.com/install.sh | sh
  fi
  systemctl enable --now ollama
  for _ in $(seq 1 30); do curl -fs http://127.0.0.1:11434/api/tags >/dev/null && break; sleep 1; done
  ollama pull nomic-embed-text

  echo "==> Usuário e pastas"
  id deltacare >/dev/null 2>&1 || useradd --system --create-home --home-dir /home/deltacare --shell /usr/sbin/nologin deltacare
  mkdir -p "$DADOS/uploads" "$DADOS/backups"
  chown -R deltacare:deltacare "$DADOS"

  echo "==> Código"
  if [ ! -d "$APP/.git" ]; then
    git clone "$REPO" "$APP"
  fi
  chown -R deltacare:deltacare "$APP"
  [ -d "$APP/.venv" ] || sudo -u deltacare -H python3 -m venv "$APP/.venv"
  sudo -u deltacare -H "$APP/.venv/bin/pip" install -q -r "$APP/backend/requirements.txt"
  (cd "$APP/frontend" && sudo -u deltacare -H npm ci --no-audit --no-fund && sudo -u deltacare -H npm run build)

  echo "==> Configuração"
  if [ ! -f /etc/deltacare.env ]; then
    cp "$APP/deploy/deltacare.env.exemplo" /etc/deltacare.env
  fi
  # 640 e grupo deltacare: o serviço lê como root, mas o backup e a
  # anonimização rodam no crontab do usuário deltacare e também precisam ler.
  chown root:deltacare /etc/deltacare.env
  chmod 640 /etc/deltacare.env

  echo "==> Serviço"
  cp "$APP/deploy/deltacare.service" /etc/systemd/system/deltacare.service
  systemctl daemon-reload
  systemctl enable deltacare
  systemctl restart deltacare

  echo "==> HTTPS (Caddy)"
  sed "s/^deltacare\.instituicao\.edu\.br {/$DOMINIO {/" "$APP/deploy/Caddyfile" > /etc/caddy/Caddyfile
  systemctl enable caddy
  systemctl reload caddy || systemctl restart caddy

  echo "==> Firewall"
  ufw allow OpenSSH >/dev/null
  ufw allow 80/tcp >/dev/null
  ufw allow 443/tcp >/dev/null
  ufw --force enable >/dev/null

  echo "==> Rotinas diárias (backup e LGPD)"
  local ambiente="cd $APP/backend && set -a && . /etc/deltacare.env && set +a"
  crontab -u deltacare - <<CRON
30 3 * * * $ambiente && ../.venv/bin/python scripts/backup.py >> $DADOS/backup.log 2>&1
45 3 * * * $ambiente && ../.venv/bin/python scripts/anonimizar_vencidas.py >> $DADOS/lgpd.log 2>&1
CRON

  echo
  echo "Instalado. Falta:"
  echo "  1. Preencher /etc/deltacare.env (SMTP e OLLAMA_API_KEY) e: systemctl restart deltacare"
  echo "  2. Criar a primeira administração:"
  echo "     sudo -u deltacare -H bash -c 'cd $APP/backend && set -a && . /etc/deltacare.env && set +a && ../.venv/bin/python scripts/criar_admin.py'"
  echo "  3. Abrir https://$DOMINIO/saude"
}

main "$@"
