"""Em que dia e em que mês as coisas acontecem: no fuso da instituição.

O sistema grava todo horário em UTC, e isso fica. Mas o dia que a pessoa vive
é o do relógio dela: o que um aluno faz às 22h de segunda em Porto Alegre
(01h de terça em UTC) é estudo de segunda. Agrupar por dia ou por mês em UTC
empurrava as três últimas horas de cada dia para o seguinte — a sequência de
dias de estudo quebrava, o teto diário de XP contava errado e o relatório da
turma punha a noite do último dia do mês no mês seguinte. O calendário teve
o mesmo defeito antes (um prazo às 23:59 aparecia no outro dia).

    DELTACARE_FUSO_HORAS   diferença para UTC, em horas (padrão: -3)
"""

import os
from datetime import date, datetime, timedelta, timezone

HORAS = int(os.environ.get("DELTACARE_FUSO_HORAS", "-3"))
FUSO = timezone(timedelta(hours=HORAS))

# Para o SQLite: `date(coluna, ?)` com este parâmetro dá o dia no fuso da
# instituição. Vale para horário com fuso gravado e sem (sem = UTC, como o
# sistema grava). Só serve para coluna que sempre tem hora: numa data pura,
# o SQLite a trataria como meia-noite em UTC e voltaria um dia.
AJUSTE_SQL = f"{HORAS:+d} hours"


def local(texto) -> datetime | None:
    """Horário do banco no fuso da instituição. Sem fuso gravado = UTC. Só
    data, vazio ou ilegível: None."""
    texto = str(texto or "")
    if len(texto) < 16:
        return None
    try:
        data = datetime.fromisoformat(texto.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (data if data.tzinfo else data.replace(tzinfo=timezone.utc)).astimezone(FUSO)


def dia(texto) -> str | None:
    """O dia (AAAA-MM-DD) no fuso da instituição. Data pura passa como está."""
    if not texto:
        return None
    convertido = local(texto)
    return convertido.strftime("%Y-%m-%d") if convertido else str(texto)[:10]


def mes(texto) -> str | None:
    """O mês (AAAA-MM) no fuso da instituição."""
    convertido = dia(texto)
    return convertido[:7] if convertido else None


def hoje() -> date:
    return datetime.now(FUSO).date()
