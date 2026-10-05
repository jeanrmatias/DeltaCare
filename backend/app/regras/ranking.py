"""Ranking da turma, pelo XP do semestre.

O cuidado central veio do próprio backlog: **ranking obrigatório expõe quem
está indo mal.** Então:

- A lista que os colegas veem mostra só o topo (TAMANHO_DO_TOPO). Ninguém
  enxerga o fundo. A posição de cada um, inclusive a de quem está atrás, só o
  próprio aluno vê.
- Quem não quer aparecer, não aparece: continua ocupando a posição dele, como
  "colega que preferiu não aparecer". A numeração segue honesta — um buraco
  entre o 2º e o 4º seria pior — e a identidade some.
- Nenhum e-mail nem id de colega sai daqui. Posição, nome, XP e faixa.

O grupo é a turma de alunos (coorte) do semestre vigente, e a medida é o XP
**do semestre**, calculado pelas mesmas funções da tela inicial. Somando a vida
inteira, o veterano ganharia sempre por tempo de casa.

"Quem mais evoluiu" é o XP dos últimos DIAS_DA_EVOLUCAO dias. As regras que
impedem farmar XP rodam antes do recorte por data (ver aluno.xp_no_periodo):
reabrir material antigo ou repetir pergunta velha não viram "evolução".
"""

from datetime import datetime, timedelta, timezone

from regras.aluno import XP_POR_NIVEL, faixa_do_nivel, xp_no_periodo
from regras.semestres import semestre_vigente
from regras.turmas import buscar_usuario, conectar

TAMANHO_DO_TOPO = 10
DIAS_DA_EVOLUCAO = 7
DESTAQUES_DA_EVOLUCAO = 3


def _disciplinas_do_semestre(cursor, aluno_id: int, vigente: str) -> set:
    """As disciplinas do aluno neste semestre — o recorte do XP do semestre."""
    return {
        linha[0]
        for linha in cursor.execute(
            """
            SELECT t.id FROM matriculas m JOIN turmas t ON t.id = m.turma_id
             WHERE m.aluno_id = ? AND t.semestre = ?
            """,
            (aluno_id, vigente),
        ).fetchall()
    }


def _faixa(xp: int) -> dict:
    faixa = faixa_do_nivel(1 + xp // XP_POR_NIVEL)
    return {"chave": faixa["chave"], "nome": faixa["nome"]}


def ranking_da_turma(aluno_email: str, coorte_id: int | None = None) -> dict:
    conexao = conectar()
    aluno = buscar_usuario(conexao, aluno_email)

    if not aluno or aluno[1] != "aluno":
        conexao.close()
        return {"sucesso": False, "mensagem": "Aluno não encontrado."}

    vigente = semestre_vigente()
    cursor = conexao.cursor()

    coortes = cursor.execute(
        """
        SELECT c.id, c.nome, c.semestre
          FROM matriculas_coorte mc JOIN coortes c ON c.id = mc.coorte_id
         WHERE mc.aluno_id = ? AND c.semestre = ?
         ORDER BY c.nome
        """,
        (aluno[0], vigente),
    ).fetchall()

    if not coortes:
        conexao.close()
        return {
            "sucesso": True,
            "semestre": vigente,
            "coorte": None,
            "coortes": [],
            "mensagem": "Você não está numa turma neste semestre, e o ranking é por turma.",
        }

    # A turma pedida só vale se for uma das dele: senão, trocando o número na
    # URL, dava para ver o ranking de uma turma alheia.
    escolhida = next((c for c in coortes if coorte_id is not None and c[0] == int(coorte_id)), coortes[0])

    colegas = cursor.execute(
        """
        SELECT u.id, COALESCE(NULLIF(u.nome, ''), u.email), u.ranking_oculto
          FROM matriculas_coorte mc JOIN users u ON u.id = mc.aluno_id
         WHERE mc.coorte_id = ? AND u.desativado_em IS NULL
        """,
        (escolhida[0],),
    ).fetchall()

    hoje = datetime.now(timezone.utc).date()
    desde = (hoje - timedelta(days=DIAS_DA_EVOLUCAO - 1)).isoformat()

    placar = []
    for colega_id, nome, oculto in colegas:
        disciplinas = _disciplinas_do_semestre(cursor, colega_id, vigente)
        placar.append({
            "id": colega_id,
            "nome": nome,
            "oculto": bool(oculto),
            "xp": xp_no_periodo(cursor, colega_id, disciplinas),
            "xp_semana": xp_no_periodo(cursor, colega_id, disciplinas, desde),
        })
    conexao.close()

    # Empate divide a posição (1º, 2º, 2º, 4º): quem fez o mesmo XP não fica
    # atrás por ordem alfabética. A ordem por nome é só para a lista ser
    # estável entre uma carga e outra.
    placar.sort(key=lambda p: (-p["xp"], p["nome"].casefold()))
    for linha in placar:
        linha["posicao"] = 1 + sum(1 for outro in placar if outro["xp"] > linha["xp"])

    eu = next(p for p in placar if p["id"] == aluno[0])

    def publico(linha: dict) -> dict:
        proprio = linha["id"] == aluno[0]
        return {
            "posicao": linha["posicao"],
            # O próprio aluno se vê pelo nome mesmo oculto: "preferiu não
            # aparecer" é para os outros.
            "nome": linha["nome"] if (proprio or not linha["oculto"]) else None,
            "oculto": linha["oculto"],
            "xp": linha["xp"],
            "faixa": _faixa(linha["xp"]),
            "eu": proprio,
        }

    # Zero XP não entra no topo: numa turma que ainda não começou, o "top 10"
    # seria uma lista de empatados em zero — exposição sem informação nenhuma.
    topo = [publico(p) for p in placar if p["xp"] > 0][:TAMANHO_DO_TOPO]

    evoluiu = [
        {"nome": p["nome"], "xp_semana": p["xp_semana"], "eu": p["id"] == aluno[0]}
        for p in sorted(placar, key=lambda p: (-p["xp_semana"], p["nome"].casefold()))
        if p["xp_semana"] > 0 and not p["oculto"]
    ][:DESTAQUES_DA_EVOLUCAO]

    return {
        "sucesso": True,
        "semestre": vigente,
        "coorte": {"id": escolhida[0], "nome": escolhida[1], "semestre": escolhida[2]},
        "coortes": [{"id": c[0], "nome": c[1]} for c in coortes],
        "total": len(placar),
        "eu": {
            "posicao": eu["posicao"],
            "xp": eu["xp"],
            "xp_semana": eu["xp_semana"],
            "faixa": _faixa(eu["xp"]),
            "aparece": not eu["oculto"],
        },
        "topo": topo,
        "evoluiu": evoluiu,
        "dias_da_evolucao": DIAS_DA_EVOLUCAO,
    }


def definir_visibilidade(aluno_email: str, aparecer: bool) -> dict:
    """O aluno escolhe se aparece no ranking dos colegas."""
    conexao = conectar()
    aluno = buscar_usuario(conexao, aluno_email)

    if not aluno or aluno[1] != "aluno":
        conexao.close()
        return {"sucesso": False, "mensagem": "Aluno não encontrado."}

    conexao.execute(
        "UPDATE users SET ranking_oculto = ? WHERE id = ?", (0 if aparecer else 1, aluno[0])
    )
    conexao.commit()
    conexao.close()

    return {
        "sucesso": True,
        "aparece": bool(aparecer),
        "mensagem": (
            "Você aparece no ranking da turma."
            if aparecer
            else "Você não aparece mais para os colegas. Sua posição continua visível só para você."
        ),
    }
