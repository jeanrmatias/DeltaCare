"""Calendário do professor: o semestre visto por data.

As telas de Materiais e Atividades respondem "o que eu publiquei". Esta
responde outra pergunta, que nenhuma das duas responde bem: **o que acontece
na semana que vem**.

Reúne quatro coisas que já existem espalhadas e só fazem sentido juntas numa
linha do tempo:

- material publicado numa data;
- material **agendado** para liberar depois;
- atividade liberada;
- **prazo** de entrega de atividade.

O prazo é o motivo de o módulo existir. Ele hoje está dentro da atividade, e
por isso o professor só descobre que marcou duas entregas no mesmo dia quando
os alunos reclamam.
"""

import calendar
import os
from datetime import datetime, timedelta, timezone

from regras.turmas import buscar_usuario, conectar, turma_pertence_ao_professor

# O fuso da instituição. O banco guarda tudo em UTC; o calendário mostra o dia
# e a hora de quem está na faculdade. Sem isto, um prazo às 23:59 de 20/10 em
# Porto Alegre (02:59 de 21/10 em UTC) aparecia no dia 21, e um material
# publicado às 19:53 aparecia às 22:53. Deslocamento fixo: o Brasil não tem
# horário de verão desde 2019, e o fuso por nome (zoneinfo) pede um pacote a
# mais no Windows.
FUSO = timezone(timedelta(hours=int(os.environ.get("DELTACARE_FUSO_HORAS", "-3"))))


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _local(texto):
    """Data do banco no fuso da instituição. Sem fuso gravado = UTC (é como o
    sistema grava). Só data, ou ilegível: None."""
    texto = str(texto or "")
    if len(texto) < 16:
        return None
    try:
        data = datetime.fromisoformat(texto.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (data if data.tzinfo else data.replace(tzinfo=timezone.utc)).astimezone(FUSO)


def _dia(texto) -> str | None:
    """O dia (AAAA-MM-DD) no fuso da instituição."""
    if not texto:
        return None
    local = _local(texto)
    return local.strftime("%Y-%m-%d") if local else str(texto)[:10]


def _hora(texto) -> str:
    """HH:MM no fuso da instituição, ou vazio quando o campo só tem data."""
    local = _local(texto)
    return local.strftime("%H:%M") if local else ""


def _limites_do_mes(ano: int, mes: int) -> tuple:
    ultimo = calendar.monthrange(ano, mes)[1]
    return "%04d-%02d-01" % (ano, mes), "%04d-%02d-%02d" % (ano, mes, ultimo)


def eventos_do_mes(professor_email: str, ano: int, mes: int, turma_id: int | None = None) -> dict:
    """Tudo o que cai num mês, nas turmas do professor."""
    if not 1 <= int(mes) <= 12:
        return {"sucesso": False, "mensagem": "Mês inválido.", "eventos": []}

    if turma_id and not turma_pertence_ao_professor(int(turma_id), professor_email):
        return {"sucesso": False, "mensagem": "Essa turma não é sua.", "eventos": []}

    conexao = conectar()
    professor = buscar_usuario(conexao, professor_email)

    if not professor or professor[1] != "professor":
        conexao.close()
        return {"sucesso": False, "mensagem": "Professor não encontrado.", "eventos": []}

    primeiro, ultimo = _limites_do_mes(int(ano), int(mes))
    fim_exclusivo = ultimo + "T23:59:59"
    agora = _agora()

    filtro_turma = " AND turma_id = ?" if turma_id else ""
    extra = [int(turma_id)] if turma_id else []

    eventos = []

    # ---- materiais ----
    # A data que interessa é a de liberação quando existe, senão a de criação:
    # material agendado pertence ao dia em que o aluno vai vê-lo, não ao dia em
    # que o professor o preparou.
    consulta_materiais = """
        SELECT m.id, m.titulo, m.tipo, m.rascunho, m.data_liberacao, m.criado_em,
               m.turma_id, t.nome
          FROM materiais m
          JOIN turmas t ON t.id = m.turma_id
         WHERE t.professor_id = ?
    """ + filtro_turma.replace("turma_id", "m.turma_id")

    for (id_, titulo, tipo, rascunho, liberacao, criado, turma, turma_nome) in conexao.execute(
        consulta_materiais, [professor[0]] + extra
    ).fetchall():
        if rascunho:
            continue  # rascunho não tem data no calendário: não acontece nada.

        quando = liberacao or criado
        if not (primeiro <= _dia(quando) <= ultimo):
            continue

        agendado = bool(liberacao and liberacao > agora)

        eventos.append({
            "dia": _dia(quando),
            "hora": _hora(quando),
            "tipo": "material_agendado" if agendado else "material",
            "id": id_,
            "titulo": titulo,
            "detalhe": "Material agendado" if agendado else "Material publicado",
            "turma_id": turma,
            "turma_nome": turma_nome,
            "link": "materiais.html",
        })

    # ---- atividades: liberação e prazo, que são dois eventos distintos ----
    consulta_atividades = """
        SELECT a.id, a.titulo, a.tipo, a.rascunho, a.data_liberacao, a.criado_em,
               a.prazo, a.turma_id, t.nome
          FROM atividades a
          JOIN turmas t ON t.id = a.turma_id
         WHERE a.professor_id = ?
    """ + filtro_turma.replace("turma_id", "a.turma_id")

    for (id_, titulo, tipo, rascunho, liberacao, criado, prazo, turma, turma_nome) in conexao.execute(
        consulta_atividades, [professor[0]] + extra
    ).fetchall():
        if rascunho:
            continue

        quando = liberacao or criado
        if primeiro <= _dia(quando) <= ultimo:
            agendada = bool(liberacao and liberacao > agora)
            eventos.append({
                "dia": _dia(quando),
                "hora": _hora(quando),
                "tipo": "atividade_agendada" if agendada else "atividade",
                "id": id_,
                "titulo": titulo,
                "detalhe": "Atividade agendada" if agendada else "Atividade liberada",
                "turma_id": turma,
                "turma_nome": turma_nome,
                "link": "atividades.html",
            })

        if prazo and primeiro <= _dia(prazo) <= ultimo:
            eventos.append({
                "dia": _dia(prazo),
                "hora": _hora(prazo),
                "tipo": "prazo",
                "id": id_,
                "titulo": titulo,
                "detalhe": "Prazo de entrega",
                "turma_id": turma,
                "turma_nome": turma_nome,
                "link": "atividades.html",
            })

    conexao.close()

    eventos.sort(key=lambda e: (e["dia"], e["hora"], e["titulo"]))

    # Dois prazos no mesmo dia é o aviso que o professor não tem hoje.
    prazos_por_dia = {}
    for evento in eventos:
        if evento["tipo"] == "prazo":
            prazos_por_dia[evento["dia"]] = prazos_por_dia.get(evento["dia"], 0) + 1

    return {
        "sucesso": True,
        "mes": "%04d-%02d" % (int(ano), int(mes)),
        "primeiro_dia": primeiro,
        "ultimo_dia": ultimo,
        "eventos": eventos,
        "resumo": {
            "materiais": len([e for e in eventos if e["tipo"].startswith("material")]),
            "atividades": len([e for e in eventos if e["tipo"].startswith("atividade")]),
            "prazos": len([e for e in eventos if e["tipo"] == "prazo"]),
            "dias_com_dois_prazos": sorted(d for d, n in prazos_por_dia.items() if n > 1),
        },
    }
