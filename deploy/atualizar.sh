#!/usr/bin/env bash
# Põe no ar o que está no GitHub. Como root, no servidor:
#
#     bash /opt/deltacare/deploy/atualizar.sh
#
# Backup antes de tudo, código novo, dependências, telas e reinício. O banco
# migra sozinho ao subir. O site fica fora do ar só os segundos do reinício.
#
# Tudo dentro de main(): o `git pull` pode trocar este próprio arquivo, e o
# bash lê o script aos poucos enquanto roda. Dentro de uma função, ele já
# leu tudo antes de começar.

set -euo pipefail

main() {
  APP=/opt/deltacare
  [ "$(id -u)" -eq 0 ] || { echo "Rode como root."; exit 1; }

  echo "==> Backup"
  sudo -u deltacare -H bash -c "cd $APP/backend && set -a && . /etc/deltacare.env && set +a && ../.venv/bin/python scripts/backup.py"

  echo "==> Código novo"
  sudo -u deltacare -H git -C "$APP" pull --ff-only
  sudo -u deltacare -H "$APP/.venv/bin/pip" install -q -r "$APP/backend/requirements.txt"
  (cd "$APP/frontend" && sudo -u deltacare -H npm ci --no-audit --no-fund && sudo -u deltacare -H npm run build)

  echo "==> Reinício"
  cp "$APP/deploy/deltacare.service" /etc/systemd/system/deltacare.service
  systemctl daemon-reload
  systemctl restart deltacare

  for _ in $(seq 1 20); do
    if curl -fs http://127.0.0.1:8000/saude >/dev/null; then
      # Como deltacare, dono do repositório: o git do root recusa ler
      # ("dubious ownership") e a linha saía sem a versão.
      echo "No ar: $(sudo -u deltacare -H git -C "$APP" log -1 --format='%h %s')"
      return 0
    fi
    sleep 1
  done
  echo "O serviço não respondeu. Veja o log: journalctl -u deltacare -n 50"
  exit 1
}

main "$@"
