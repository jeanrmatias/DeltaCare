"""Desempenho: o que as notas dizem sobre o estudo e sobre a aula.

Duas leituras dos mesmos dados, e elas respondem perguntas diferentes:

- **Aluno** — como eu estou indo, e em que assunto eu erro mais.
- **Professor** — como a turma está indo, e que tópico precisa voltar na aula.

A segunda é a que justifica o módulo. Uma média de turma diz que foi mal; o
índice de erro por tópico diz **onde** foi mal, que é a informação que muda a
aula seguinte.

Nada aqui é estimado. Tudo sai de `entregas`, `atividades` e `questoes`. Turma
sem atividade corrigida devolve lista vazia, não número inventado — a regra do
projeto é declarar o que não existe.
"""

import json
from datetime import datetime, timedelta, timezone

from regras.turmas import buscar_usuario, conectar, turma_pertence_ao_professor


def _agora():
    return datetime.now(timezone.utc)


def _percentual(nota, pontos):
    """Nota em porcentagem, para comparar atividades de escalas diferentes."""
    if nota is None or not pontos:
        return None
    return round(100 * nota / pontos, 1)


def _limite_do_periodo(dias):
    """Data de corte, ou None para 'desde sempre'."""
    if not dias:
        return None
    return (_agora() - timedelta(days=int(dias))).isoformat()


# =========================================================================
# Erros por tópico
# =========================================================================

def _erros_por_topico(conexao, entregas_objetivas):
    """Agrupa acerto e erro por tópico da atividade.

    `entregas_objetivas` são tuplas (atividade_id, topico, assunto, respostas).

    O tópico vem da atividade, não da questão: hoje a questão não tem
    classificação própria. Quando tiver, é só trocar a chave aqui — por isso o
    agrupamento está isolado nesta função.
    """
    gabaritos = {}
    contagem = {}

    for atividade_id, topico, assunto, respostas_json in entregas_objetivas:
        rotulo = (topico or assunto or "Sem tópico").strip() or "Sem tópico"

        if atividade_id not in gabaritos:
            gabaritos[atividade_id] = [
                linha[0]
                for linha in conexao.execute(
                    "SELECT correta FROM questoes WHERE atividade_id = ? ORDER BY ordem",
                    (atividade_id,),
                ).fetchall()
            ]

        gabarito = gabaritos[atividade_id]
        if not gabarito:
            continue

        try:
            escolhas = json.loads(respostas_json) if respostas_json else []
        except (TypeError, ValueError):
            continue

        if not isinstance(escolhas, list):
            continue

        dados = contagem.setdefault(rotulo, {"acertos": 0, "erros": 0})

        for ordem, correta in enumerate(gabarito):
            marcada = escolhas[ordem] if ordem < len(escolhas) else None
            if marcada == correta:
                dados["acertos"] += 1
            else:
                # Deixar em branco conta como erro: para saber o que revisar,
                # não respondida e respondida errado dizem a mesma coisa.
                dados["erros"] += 1

    topicos = []
    for rotulo, dados in contagem.items():
        total = dados["acertos"] + dados["erros"]
        if not total:
            continue
        topicos.append({
            "topico": rotulo,
            "acertos": dados["acertos"],
            "erros": dados["erros"],
            "total": total,
            "percentual_erro": round(100 * dados["erros"] / total, 1),
        })

    # Mais errado primeiro: é o que o professor e o aluno querem ver de cara.
    topicos.sort(key=lambda t: (-t["percentual_erro"], -t["total"]))
    return topicos


# =========================================================================
# Aluno
# =========================================================================

def desempenho_do_aluno(aluno_email: str, turma_id: int | None = None, dias: int | None = None) -> dict:
    """Notas, evolução e tópicos com mais erro do próprio aluno."""
    conexao = conectar()
    aluno = buscar_usuario(conexao, aluno_email)

    if not aluno or aluno[1] != "aluno":
        conexao.close()
        return {"sucesso": False, "mensagem": "Aluno não encontrado."}

    consulta = """
        SELECT a.id, a.titulo, a.tipo, a.pontos, a.topico, a.assunto,
               t.nome, e.nota, e.enviado_em, e.corrigido_em, e.respostas, a.prazo
          FROM entregas e
          JOIN atividades a ON a.id = e.atividade_id
          JOIN turmas t ON t.id = a.turma_id
         WHERE e.aluno_id = ? AND e.enviado_em IS NOT NULL
    """
    parametros = [aluno[0]]

    if turma_id:
        consulta += " AND a.turma_id = ?"
        parametros.append(int(turma_id))

    limite = _limite_do_periodo(dias)
    if limite:
        consulta += " AND e.enviado_em >= ?"
        parametros.append(limite)

    consulta += " ORDER BY e.enviado_em"

    linhas = conexao.execute(consulta, parametros).fetchall()

    notas = []
    evolucao = []
    objetivas = []
    soma_obtida = 0.0
    soma_possivel = 0.0

    for (id_, titulo, tipo, pontos, topico, assunto, turma_nome,
         nota, enviado_em, corrigido_em, respostas, prazo) in linhas:

        percentual = _percentual(nota, pontos)

        notas.append({
            "atividade_id": id_,
            "titulo": titulo,
            "tipo": tipo,
            "turma_nome": turma_nome,
            "topico": topico or assunto or "",
            "pontos": pontos,
            "nota": nota,
            "percentual": percentual,
            "enviado_em": enviado_em,
            "corrigido_em": corrigido_em,
            "atrasada": bool(enviado_em and prazo and enviado_em > prazo),
        })

        if nota is not None:
            soma_obtida += nota
            soma_possivel += pontos or 0
            evolucao.append({
                "data": (corrigido_em or enviado_em or "")[:10],
                "titulo": titulo,
                "percentual": percentual,
            })

        if tipo == "objetiva":
            objetivas.append((id_, topico, assunto, respostas))

    topicos = _erros_por_topico(conexao, objetivas)
    conexao.close()

    corrigidas = [n for n in notas if n["nota"] is not None]

    return {
        "sucesso": True,
        "resumo": {
            "entregues": len(notas),
            "corrigidas": len(corrigidas),
            "aguardando": len(notas) - len(corrigidas),
            "atrasadas": len([n for n in notas if n["atrasada"]]),
            "pontos_obtidos": round(soma_obtida, 1),
            "pontos_possiveis": round(soma_possivel, 1),
            # Aproveitamento é a média ponderada pelos pontos, não a média das
            # notas: uma atividade que vale 30 pesa mais que uma que vale 10.
            "aproveitamento": round(100 * soma_obtida / soma_possivel, 1) if soma_possivel else None,
        },
        "notas": notas,
        "evolucao": evolucao,
        "topicos": topicos,
    }


# =========================================================================
# Professor
# =========================================================================

def desempenho_da_turma(professor_email: str, turma_id: int, dias: int | None = None) -> dict:
    """Como a turma está indo, por atividade, por tópico e por aluno."""
    if not turma_pertence_ao_professor(int(turma_id), professor_email):
        return {"sucesso": False, "mensagem": "Essa turma não é sua."}

    conexao = conectar()

    turma = conexao.execute(
        "SELECT id, nome, semestre FROM turmas WHERE id = ?", (int(turma_id),)
    ).fetchone()

    if not turma:
        conexao.close()
        return {"sucesso": False, "mensagem": "Turma não encontrada."}

    limite = _limite_do_periodo(dias)

    # ---- atividades publicadas e o que cada uma produziu ----
    consulta_atividades = """
        SELECT id, titulo, tipo, pontos, criado_em, topico, assunto
          FROM atividades
         WHERE turma_id = ? AND rascunho = 0
           AND (data_liberacao IS NULL OR data_liberacao <= ?)
    """
    parametros = [int(turma_id), _agora().isoformat()]

    if limite:
        consulta_atividades += " AND criado_em >= ?"
        parametros.append(limite)

    consulta_atividades += " ORDER BY criado_em"

    total_alunos = conexao.execute(
        "SELECT COUNT(*) FROM matriculas WHERE turma_id = ?", (int(turma_id),)
    ).fetchone()[0]

    atividades = []
    objetivas = []
    soma_percentuais = []

    for id_, titulo, tipo, pontos, criado_em, topico, assunto in conexao.execute(
        consulta_atividades, parametros
    ).fetchall():
        entregas = conexao.execute(
            "SELECT nota, respostas FROM entregas"
            "  WHERE atividade_id = ? AND enviado_em IS NOT NULL",
            (id_,),
        ).fetchall()

        notas = [n for n, _ in entregas if n is not None]
        percentuais = [_percentual(n, pontos) for n in notas]
        percentuais = [p for p in percentuais if p is not None]

        atividades.append({
            "id": id_,
            "titulo": titulo,
            "tipo": tipo,
            "pontos": pontos,
            "criado_em": criado_em,
            "entregues": len(entregas),
            "pendentes": max(total_alunos - len(entregas), 0),
            "corrigidas": len(notas),
            "media": round(sum(notas) / len(notas), 1) if notas else None,
            "media_percentual": round(sum(percentuais) / len(percentuais), 1) if percentuais else None,
            "menor": min(notas) if notas else None,
            "maior": max(notas) if notas else None,
        })

        soma_percentuais.extend(percentuais)

        if tipo == "objetiva":
            for _, respostas in entregas:
                objetivas.append((id_, topico, assunto, respostas))

    topicos = _erros_por_topico(conexao, objetivas)

    # ---- um resumo por aluno ----
    alunos = []
    for aluno_id, email, nome in conexao.execute(
        "SELECT u.id, u.email, u.nome FROM matriculas m"
        "  JOIN users u ON u.id = m.aluno_id"
        " WHERE m.turma_id = ? ORDER BY COALESCE(u.nome, u.email)",
        (int(turma_id),),
    ).fetchall():
        linhas = conexao.execute(
            """
            SELECT e.nota, a.pontos, e.enviado_em, a.prazo
              FROM entregas e
              JOIN atividades a ON a.id = e.atividade_id
             WHERE e.aluno_id = ? AND a.turma_id = ? AND e.enviado_em IS NOT NULL
            """,
            (aluno_id, int(turma_id)),
        ).fetchall()

        obtidos = sum(n for n, _, _, _ in linhas if n is not None)
        possiveis = sum(p for n, p, _, _ in linhas if n is not None and p)
        atrasadas = len([1 for _, _, enviado, prazo in linhas if enviado and prazo and enviado > prazo])
        ultima = max((e for _, _, e, _ in linhas if e), default=None)

        alunos.append({
            "aluno_email": email,
            "aluno_nome": nome or email,
            "entregues": len(linhas),
            "atrasadas": atrasadas,
            "aproveitamento": round(100 * obtidos / possiveis, 1) if possiveis else None,
            "ultima_entrega": ultima,
        })

    conexao.close()

    total_esperado = total_alunos * len(atividades)
    total_entregue = sum(a["entregues"] for a in atividades)

    return {
        "sucesso": True,
        "turma": {"id": turma[0], "nome": turma[1], "semestre": turma[2]},
        "resumo": {
            "total_alunos": total_alunos,
            "atividades": len(atividades),
            "media_percentual": round(sum(soma_percentuais) / len(soma_percentuais), 1)
                                if soma_percentuais else None,
            "taxa_entrega": round(100 * total_entregue / total_esperado, 1) if total_esperado else None,
            "a_corrigir": sum(a["entregues"] - a["corrigidas"] for a in atividades),
        },
        "atividades": atividades,
        "topicos": topicos,
        "alunos": alunos,
    }
