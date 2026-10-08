"""Cópia de segurança do banco e dos arquivos enviados.

    python scripts/backup.py        (de dentro de backend/)

Agendado uma vez por dia (cron no Linux, Agendador de Tarefas no Windows —
ver o README). Cria uma pasta com data e hora contendo o banco e os uploads, e
apaga as mais antigas além de DELTACARE_BACKUPS_MANTER.

**O banco é copiado pela API de backup do SQLite, e não copiando o arquivo.**
Com o servidor no ar, o .db pode estar no meio de uma escrita, e no modo WAL
parte dos dados recentes nem está nele ainda (está no -wal ao lado). Copiar o
arquivo daria uma cópia que parece boa e não abre — descoberto só no dia de
precisar dela. A API do SQLite tira a foto consistente com o banco em uso.

Depois de copiar, confere a cópia (PRAGMA integrity_check). Backup que não foi
conferido é esperança, não backup. Sai com código 1 se algo falhar, para o
agendador poder avisar.

    DELTACARE_BACKUPS          pasta dos backups (padrão: backups/, ao lado do banco)
    DELTACARE_BACKUPS_MANTER   quantos guardar (padrão: 14)

Restaurar: com o servidor parado, apague deltacare.db-wal e deltacare.db-shm
se existirem (sobram quando o servidor caiu; deixados lá, o SQLite aplicaria
essas escritas antigas sobre o banco restaurado), copie deltacare.db da pasta
escolhida sobre o banco em uso e a pasta uploads/ sobre a atual. Testado:
restaurado assim, o banco volta ao estado do backup e os PDFs abrem.
"""

import os
import shutil
import sqlite3
import sys
from datetime import datetime

import _app  # noqa: F401  (põe backend/app no caminho de import)
from infra.arquivos import RAIZ_UPLOADS
from infra.database import CAMINHO_DB

PREFIXO = "deltacare_"


def pasta_de_backups() -> str:
    padrao = os.path.join(os.path.dirname(os.path.abspath(CAMINHO_DB)), "backups")
    return os.environ.get("DELTACARE_BACKUPS", padrao)


def fazer_backup(destino_raiz: str | None = None, manter: int | None = None) -> str:
    """Faz o backup e devolve a pasta criada. Lança se a cópia não passar na conferência."""
    destino_raiz = destino_raiz or pasta_de_backups()
    manter = manter if manter is not None else int(os.environ.get("DELTACARE_BACKUPS_MANTER", "14"))

    carimbo = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    destino = os.path.join(destino_raiz, PREFIXO + carimbo)
    os.makedirs(destino, exist_ok=False)

    copia_do_banco = os.path.join(destino, "deltacare.db")
    origem = sqlite3.connect(CAMINHO_DB)
    copia = sqlite3.connect(copia_do_banco)
    try:
        origem.backup(copia)
        resultado = copia.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        copia.close()
        origem.close()

    if resultado != "ok":
        raise RuntimeError(f"A cópia do banco não passou na conferência: {resultado}")

    # Os arquivos não mudam depois de gravados (o nome é um uuid novo a cada
    # envio), então copiar a pasta é seguro com o servidor no ar.
    if os.path.isdir(RAIZ_UPLOADS):
        shutil.copytree(RAIZ_UPLOADS, os.path.join(destino, "uploads"))

    _apagar_antigos(destino_raiz, manter)
    return destino


def _apagar_antigos(destino_raiz: str, manter: int) -> None:
    """Fica com os `manter` mais recentes. O nome com data ordena sozinho."""
    if manter < 1:
        return
    pastas = sorted(
        nome for nome in os.listdir(destino_raiz)
        if nome.startswith(PREFIXO) and os.path.isdir(os.path.join(destino_raiz, nome))
    )
    for nome in pastas[:-manter]:
        shutil.rmtree(os.path.join(destino_raiz, nome), ignore_errors=True)


if __name__ == "__main__":
    try:
        pasta = fazer_backup()
    except Exception as erro:
        print(f"[Delta Care] BACKUP FALHOU: {erro}")
        sys.exit(1)
    print(f"[Delta Care] Backup feito e conferido em {pasta}")
