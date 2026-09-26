"""Regras de negócio de atividades: criação, entrega e correção.

Dois tipos, e a diferença está em **quem corrige**:

- `objetiva`     — questões de múltipla escolha. O sistema compara com o
                   gabarito e a nota sai na hora.
- `dissertativa` — o aluno escreve a resposta. A nota e a devolutiva vêm do
                   professor.

Três decisões que valem explicar, porque se forem desfeitas o módulo quebra de
formas silenciosas:

**O gabarito nunca sai do servidor para o aluno.** `_questoes_para_aluno()`
monta a lista sem o campo `correta`. Mandar o gabarito e esconder na interface
seria o mesmo que não ter gabarito: está tudo no DevTools.

**A entrega nasce no primeiro rascunho, não no envio.** Uma linha por aluno por
atividade, com `enviado_em NULL` enquanto for progresso salvo. É assim que o
aluno fecha a aba e retoma de onde parou.

**Entrega atrasada é aceita e marcada, não recusada.** Recusar joga fora o
trabalho que o aluno fez; marcar dá ao professor a informação para decidir. O
campo `atrasada` é calculado comparando `enviado_em` com `prazo`.
"""

import json
from datetime import datetime, timezone

from regras.turmas import buscar_usuario, conectar, turma_pertence_ao_professor

TIPOS_VALIDOS = ("objetiva", "dissertativa")


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _para_datahora(texto: str | None):
    """Lê uma data do banco tolerando a ausência de fuso."""
    if not texto:
        return None
    try:
        quando = datetime.fromisoformat(texto)
    except ValueError:
        return None
    if quando.tzinfo is None:
        quando = quando.replace(tzinfo=timezone.utc)
    return quando


def _calcular_status(rascunho: int, data_liberacao: str | None) -> str:
    """Mesma regra dos materiais: rascunho, agendado ou publicado."""
    if rascunho:
        return "rascunho"

    liberacao = _para_datahora(data_liberacao)
    if liberacao and liberacao > datetime.now(timezone.utc):
        return "agendado"

    return "publicado"


def _atrasada(enviado_em: str | None, prazo: str | None) -> bool:
    entrega = _para_datahora(enviado_em)
    limite = _para_datahora(prazo)
    return bool(entrega and limite and entrega > limite)


# =========================================================================
# Professor
# =========================================================================

def _validar_questoes(tipo: str, questoes) -> str | None:
    """Devolve a mensagem de erro, ou None se estiver tudo certo."""
    if tipo != "objetiva":
        return None

    if not questoes:
        return "Uma atividade objetiva precisa de pelo menos uma questão."

    for indice, questao in enumerate(questoes, start=1):
        enunciado = (questao.get("enunciado") or "").strip()
        alternativas = [a.strip() for a in (questao.get("alternativas") or []) if a.strip()]
        correta = questao.get("correta")

        if not enunciado:
            return f"A questão {indice} está sem enunciado."
        if len(alternativas) < 2:
            return f"A questão {indice} precisa de pelo menos duas alternativas."
        if not isinstance(correta, int) or not (0 <= correta < len(alternativas)):
            return f"A questão {indice} está sem alternativa correta marcada."

    return None


def criar_atividade_em_turmas(professor_email: str, turma_ids: list, **campos) -> dict:
    """Cria a mesma atividade em várias turmas.

    Como nos materiais, a validação acontece **antes** de criar qualquer coisa:
    se uma das turmas não for do professor, nada é criado. Publicação parcial
    deixaria o professor sem saber em quais turmas a atividade entrou.
    """
    turma_ids = [int(t) for t in (turma_ids or [])]

    if not turma_ids:
        return {"sucesso": False, "mensagem": "Escolha pelo menos uma turma."}

    titulo = (campos.get("titulo") or "").strip()
    if not titulo:
        return {"sucesso": False, "mensagem": "Informe o título da atividade."}

    tipo = campos.get("tipo")
    if tipo not in TIPOS_VALIDOS:
        return {"sucesso": False, "mensagem": "Tipo de atividade inválido."}

    questoes = campos.get("questoes") or []
    erro = _validar_questoes(tipo, questoes)
    if erro:
        return {"sucesso": False, "mensagem": erro}

    for turma_id in turma_ids:
        if not turma_pertence_ao_professor(turma_id, professor_email):
            return {
                "sucesso": False,
                "mensagem": "Uma das turmas escolhidas não é sua.",
            }

    conexao = conectar()
    professor = buscar_usuario(conexao, professor_email)

    if not professor:
        conexao.close()
        return {"sucesso": False, "mensagem": "Professor não encontrado."}

    cursor = conexao.cursor()
    agora = _agora()
    rascunho = 1 if campos.get("rascunho", True) else 0
    data_liberacao = campos.get("data_liberacao") or None
    criadas = []

    for turma_id in turma_ids:
        cursor.execute(
            """
            INSERT INTO atividades (
                professor_id, turma_id, titulo, enunciado, tipo, assunto, topico,
                pontos, rascunho, data_liberacao, prazo, criado_em, atualizado_em
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                professor[0],
                turma_id,
                titulo,
                (campos.get("enunciado") or "").strip(),
                tipo,
                (campos.get("assunto") or "").strip(),
                (campos.get("topico") or "").strip(),
                int(campos.get("pontos") or 10),
                rascunho,
                data_liberacao,
                campos.get("prazo") or None,
                agora,
                agora,
            ),
        )
        atividade_id = cursor.lastrowid
        criadas.append(atividade_id)

        # As questões são copiadas para cada turma. Poderiam ser compartilhadas,
        # mas aí editar a questão de uma turma editaria a da outra — e o
        # professor edita turma a turma, como já faz com material.
        for ordem, questao in enumerate(questoes):
            alternativas = [a.strip() for a in questao["alternativas"] if a.strip()]
            cursor.execute(
                """
                INSERT INTO questoes (atividade_id, ordem, enunciado, alternativas, correta)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    atividade_id,
                    ordem,
                    questao["enunciado"].strip(),
                    json.dumps(alternativas, ensure_ascii=False),
                    int(questao["correta"]),
                ),
            )

    conexao.commit()

    nomes_por_turma = {
        turma_id: (
            cursor.execute("SELECT nome FROM turmas WHERE id = ?", (turma_id,)).fetchone()
            or ("sua turma",)
        )[0]
        for turma_id in turma_ids
    }
    conexao.close()

    # Mesma regra do material: rascunho não avisa, agendado avisa quando a data
    # chegar (regras/notificacoes), publicado avisa agora.
    if not rascunho and not data_liberacao:
        from regras.notificacoes import notificar_alunos_da_turma

        for turma_id in turma_ids:
            notificar_alunos_da_turma(
                turma_id,
                "atividade",
                "Nova atividade",
                f'"{titulo}" foi publicada em {nomes_por_turma[turma_id]}.',
                "atividades.html",
            )

    return {
        "sucesso": True,
        "mensagem": "Atividade criada.",
        "atividade_ids": criadas,
    }


def listar_atividades(professor_email: str, turma_id: int | None = None) -> dict:
    """Atividades do professor, com quantos alunos já entregaram."""
    conexao = conectar()
    professor = buscar_usuario(conexao, professor_email)

    if not professor or professor[1] != "professor":
        conexao.close()
        return {"sucesso": False, "mensagem": "Professor não encontrado.", "atividades": []}

    consulta = """
        SELECT a.id, a.titulo, a.enunciado, a.tipo, a.assunto, a.topico, a.pontos,
               a.rascunho, a.data_liberacao, a.prazo, a.criado_em, a.atualizado_em,
               a.turma_id, t.nome,
               (SELECT COUNT(*) FROM questoes q WHERE q.atividade_id = a.id),
               (SELECT COUNT(*) FROM entregas e
                 WHERE e.atividade_id = a.id AND e.enviado_em IS NOT NULL),
               (SELECT COUNT(*) FROM entregas e
                 WHERE e.atividade_id = a.id AND e.enviado_em IS NOT NULL
                   AND e.nota IS NULL),
               (SELECT COUNT(*) FROM matriculas m WHERE m.turma_id = a.turma_id)
          FROM atividades a
          JOIN turmas t ON t.id = a.turma_id
         WHERE a.professor_id = ?
    """
    parametros = [professor[0]]

    if turma_id:
        consulta += " AND a.turma_id = ?"
        parametros.append(int(turma_id))

    consulta += " ORDER BY a.criado_em DESC"

    linhas = conexao.execute(consulta, parametros).fetchall()
    conexao.close()

    atividades = []
    for linha in linhas:
        (id_, titulo, enunciado, tipo, assunto, topico, pontos, rascunho,
         data_liberacao, prazo, criado_em, atualizado_em, turma, turma_nome,
         total_questoes, entregues, a_corrigir, total_alunos) = linha

        atividades.append({
            "id": id_,
            "titulo": titulo,
            "enunciado": enunciado,
            "tipo": tipo,
            "assunto": assunto,
            "topico": topico,
            "pontos": pontos,
            "rascunho": bool(rascunho),
            "data_liberacao": data_liberacao,
            "prazo": prazo,
            "status": _calcular_status(rascunho, data_liberacao),
            "criado_em": criado_em,
            "atualizado_em": atualizado_em,
            "turma_id": turma,
            "turma_nome": turma_nome,
            "total_questoes": total_questoes,
            "entregues": entregues,
            "a_corrigir": a_corrigir,
            "total_alunos": total_alunos,
            "pendentes": max(total_alunos - entregues, 0),
        })

    return {"sucesso": True, "atividades": atividades}


def _buscar_atividade_do_professor(conexao, atividade_id: int, professor_email: str):
    professor = buscar_usuario(conexao, professor_email)
    if not professor:
        return None

    return conexao.execute(
        "SELECT id, turma_id, titulo, tipo, pontos, prazo, rascunho, data_liberacao"
        "  FROM atividades WHERE id = ? AND professor_id = ?",
        (int(atividade_id), professor[0]),
    ).fetchone()


def obter_atividade(atividade_id: int, professor_email: str) -> dict:
    """Atividade completa **com gabarito** — só para o professor que a criou."""
    conexao = conectar()
    atividade = _buscar_atividade_do_professor(conexao, atividade_id, professor_email)

    if not atividade:
        conexao.close()
        return {"sucesso": False, "mensagem": "Atividade não encontrada."}

    questoes = conexao.execute(
        "SELECT id, ordem, enunciado, alternativas, correta FROM questoes"
        "  WHERE atividade_id = ? ORDER BY ordem",
        (int(atividade_id),),
    ).fetchall()
    conexao.close()

    return {
        "sucesso": True,
        "atividade": {
            "id": atividade[0],
            "turma_id": atividade[1],
            "titulo": atividade[2],
            "tipo": atividade[3],
            "pontos": atividade[4],
            "prazo": atividade[5],
        },
        "questoes": [
            {
                "id": q[0],
                "ordem": q[1],
                "enunciado": q[2],
                "alternativas": json.loads(q[3]),
                "correta": q[4],
            }
            for q in questoes
        ],
    }


def atualizar_atividade(atividade_id: int, professor_email: str, **campos) -> dict:
    conexao = conectar()
    atividade = _buscar_atividade_do_professor(conexao, atividade_id, professor_email)

    if not atividade:
        conexao.close()
        return {"sucesso": False, "mensagem": "Atividade não encontrada."}

    permitidos = ("titulo", "enunciado", "assunto", "topico", "pontos",
                  "rascunho", "data_liberacao", "prazo")
    mudancas = {c: v for c, v in campos.items() if c in permitidos and v is not None}

    if not mudancas:
        conexao.close()
        return {"sucesso": False, "mensagem": "Nada para atualizar."}

    if "rascunho" in mudancas:
        mudancas["rascunho"] = 1 if mudancas["rascunho"] else 0

    atribuicoes = ", ".join(f"{campo} = ?" for campo in mudancas)
    valores = list(mudancas.values()) + [_agora(), int(atividade_id)]

    conexao.execute(
        f"UPDATE atividades SET {atribuicoes}, atualizado_em = ? WHERE id = ?",
        valores,
    )
    conexao.commit()

    era_rascunho = bool(atividade[6])
    virou_publicada = era_rascunho and mudancas.get("rascunho") == 0
    turma_id = atividade[1]
    turma = conexao.execute(
        "SELECT nome FROM turmas WHERE id = ?", (turma_id,)
    ).fetchone()
    conexao.close()

    if virou_publicada and not mudancas.get("data_liberacao"):
        from regras.notificacoes import notificar_alunos_da_turma

        notificar_alunos_da_turma(
            turma_id,
            "atividade",
            "Nova atividade",
            f'"{mudancas.get("titulo") or atividade[2]}" foi publicada em '
            f'{turma[0] if turma else "sua turma"}.',
            "atividades.html",
        )

    return {"sucesso": True, "mensagem": "Atividade atualizada."}


def excluir_atividade(atividade_id: int, professor_email: str) -> dict:
    """Apaga a atividade e o que depende dela.

    Sem apagar questões e entregas sobrariam registros órfãos apontando para
    uma atividade que não existe mais — o mesmo problema que já apareceu ao
    excluir turma e material.
    """
    conexao = conectar()
    atividade = _buscar_atividade_do_professor(conexao, atividade_id, professor_email)

    if not atividade:
        conexao.close()
        return {"sucesso": False, "mensagem": "Atividade não encontrada."}

    conexao.execute("DELETE FROM questoes WHERE atividade_id = ?", (int(atividade_id),))
    conexao.execute("DELETE FROM entregas WHERE atividade_id = ?", (int(atividade_id),))
    conexao.execute("DELETE FROM atividades WHERE id = ?", (int(atividade_id),))
    conexao.commit()
    conexao.close()

    return {"sucesso": True, "mensagem": "Atividade excluída."}


def listar_entregas(atividade_id: int, professor_email: str) -> dict:
    """Quem entregou, quem está pendente e o que falta corrigir."""
    conexao = conectar()
    atividade = _buscar_atividade_do_professor(conexao, atividade_id, professor_email)

    if not atividade:
        conexao.close()
        return {"sucesso": False, "mensagem": "Atividade não encontrada.", "entregas": []}

    prazo = atividade[5]

    # O gabarito vai junto **aqui** de propósito: esta é rota de professor, e
    # sem ele a tela mostraria "marcou a alternativa 2" sem dizer se 2 estava
    # certa. Na rota do aluno, `correta` nem sai do banco.
    questoes = [
        {
            "ordem": linha[0],
            "enunciado": linha[1],
            "alternativas": json.loads(linha[2]),
            "correta": linha[3],
        }
        for linha in conexao.execute(
            "SELECT ordem, enunciado, alternativas, correta FROM questoes"
            "  WHERE atividade_id = ? ORDER BY ordem",
            (int(atividade_id),),
        ).fetchall()
    ]

    # Parte dos alunos matriculados, não das entregas: quem não entregou
    # também precisa aparecer, senão o professor não vê a pendência.
    linhas = conexao.execute(
        """
        SELECT u.id, u.email, u.nome,
               e.id, e.respostas, e.enviado_em, e.nota, e.devolutiva, e.corrigido_em
          FROM matriculas m
          JOIN users u ON u.id = m.aluno_id
          LEFT JOIN entregas e ON e.aluno_id = u.id AND e.atividade_id = ?
         WHERE m.turma_id = ?
         ORDER BY COALESCE(u.nome, u.email)
        """,
        (int(atividade_id), atividade[1]),
    ).fetchall()
    conexao.close()

    entregas = []
    for (aluno_id, email, nome, entrega_id, respostas, enviado_em,
         nota, devolutiva, corrigido_em) in linhas:
        entregas.append({
            "aluno_id": aluno_id,
            "aluno_email": email,
            "aluno_nome": nome or email,
            "entrega_id": entrega_id,
            "respostas": json.loads(respostas) if respostas else None,
            "enviado_em": enviado_em,
            "entregue": bool(enviado_em),
            "atrasada": _atrasada(enviado_em, prazo),
            "nota": nota,
            "devolutiva": devolutiva,
            "corrigido_em": corrigido_em,
        })

    return {
        "sucesso": True,
        "atividade": {
            "id": atividade[0],
            "titulo": atividade[2],
            "tipo": atividade[3],
            "pontos": atividade[4],
            "prazo": prazo,
        },
        "questoes": questoes,
        "entregas": entregas,
    }


def corrigir_entrega(entrega_id: int, professor_email: str, nota, devolutiva: str = "") -> dict:
    """Registra nota e devolutiva. Só o professor dono da atividade."""
    conexao = conectar()
    professor = buscar_usuario(conexao, professor_email)

    if not professor:
        conexao.close()
        return {"sucesso": False, "mensagem": "Professor não encontrado."}

    # O JOIN com atividades é o que impede corrigir entrega de turma alheia:
    # sem ele, bastaria conhecer o id da entrega.
    linha = conexao.execute(
        """
        SELECT e.id, a.pontos, e.aluno_id, a.titulo
          FROM entregas e
          JOIN atividades a ON a.id = e.atividade_id
         WHERE e.id = ? AND a.professor_id = ?
        """,
        (int(entrega_id), professor[0]),
    ).fetchone()

    if not linha:
        conexao.close()
        return {"sucesso": False, "mensagem": "Entrega não encontrada."}

    try:
        nota = float(nota)
    except (TypeError, ValueError):
        conexao.close()
        return {"sucesso": False, "mensagem": "Nota inválida."}

    if nota < 0 or nota > linha[1]:
        conexao.close()
        return {
            "sucesso": False,
            "mensagem": f"A nota precisa estar entre 0 e {linha[1]}.",
        }

    conexao.execute(
        "UPDATE entregas SET nota = ?, devolutiva = ?, corrigido_em = ? WHERE id = ?",
        (nota, (devolutiva or "").strip(), _agora(), int(entrega_id)),
    )
    conexao.commit()
    conexao.close()

    from regras.notificacoes import criar_notificacao

    criar_notificacao(
        linha[2],
        "correcao",
        "Atividade corrigida",
        f'"{linha[3]}" foi corrigida: nota {nota:g} de {linha[1]}.',
        "atividades.html",
    )

    return {"sucesso": True, "mensagem": "Correção registrada."}


# =========================================================================
# Aluno
# =========================================================================

def _turmas_do_aluno(conexao, aluno_id: int) -> list:
    return [
        linha[0]
        for linha in conexao.execute(
            "SELECT turma_id FROM matriculas WHERE aluno_id = ?", (aluno_id,)
        ).fetchall()
    ]


def _questoes_para_aluno(conexao, atividade_id: int) -> list:
    """Questões **sem o gabarito**.

    O campo `correta` é lido da mesma tabela em `obter_atividade()`, que é do
    professor. Aqui ele nem chega a sair do banco.
    """
    linhas = conexao.execute(
        "SELECT id, ordem, enunciado, alternativas FROM questoes"
        "  WHERE atividade_id = ? ORDER BY ordem",
        (int(atividade_id),),
    ).fetchall()

    return [
        {
            "id": linha[0],
            "ordem": linha[1],
            "enunciado": linha[2],
            "alternativas": json.loads(linha[3]),
        }
        for linha in linhas
    ]


def listar_atividades_do_aluno(aluno_email: str, turma_id: int | None = None) -> dict:
    """Só o que já está liberado, com o estado da entrega do próprio aluno.

    Arquivo e consulta separados da visão do professor pelo mesmo motivo dos
    materiais: aqui rascunho e agendado **nunca** aparecem, e unificar as duas
    consultas num parâmetro convidaria a um erro de filtro que vazaria
    atividade não liberada.
    """
    conexao = conectar()
    aluno = buscar_usuario(conexao, aluno_email)

    if not aluno or aluno[1] != "aluno":
        conexao.close()
        return {"sucesso": False, "mensagem": "Aluno não encontrado.", "atividades": []}

    turmas = _turmas_do_aluno(conexao, aluno[0])

    if not turmas:
        conexao.close()
        return {"sucesso": True, "atividades": []}

    marcadores = ",".join("?" for _ in turmas)
    consulta = f"""
        SELECT a.id, a.titulo, a.enunciado, a.tipo, a.assunto, a.topico, a.pontos,
               a.prazo, a.criado_em, a.turma_id, t.nome,
               (SELECT COUNT(*) FROM questoes q WHERE q.atividade_id = a.id),
               e.id, e.enviado_em, e.nota, e.devolutiva
          FROM atividades a
          JOIN turmas t ON t.id = a.turma_id
          LEFT JOIN entregas e ON e.atividade_id = a.id AND e.aluno_id = ?
         WHERE a.turma_id IN ({marcadores})
           AND a.rascunho = 0
           AND (a.data_liberacao IS NULL OR a.data_liberacao <= ?)
    """
    parametros = [aluno[0]] + turmas + [_agora()]

    if turma_id:
        consulta += " AND a.turma_id = ?"
        parametros.append(int(turma_id))

    consulta += " ORDER BY COALESCE(a.prazo, a.criado_em)"

    linhas = conexao.execute(consulta, parametros).fetchall()
    conexao.close()

    atividades = []
    for linha in linhas:
        (id_, titulo, enunciado, tipo, assunto, topico, pontos, prazo, criado_em,
         turma, turma_nome, total_questoes, entrega_id, enviado_em, nota,
         devolutiva) = linha

        if enviado_em:
            situacao = "corrigida" if nota is not None else "entregue"
        elif entrega_id:
            situacao = "em andamento"
        else:
            situacao = "pendente"

        atividades.append({
            "id": id_,
            "titulo": titulo,
            "enunciado": enunciado,
            "tipo": tipo,
            "assunto": assunto,
            "topico": topico,
            "pontos": pontos,
            "prazo": prazo,
            "criado_em": criado_em,
            "turma_id": turma,
            "turma_nome": turma_nome,
            "total_questoes": total_questoes,
            "situacao": situacao,
            "enviado_em": enviado_em,
            "atrasada": _atrasada(enviado_em, prazo),
            "nota": nota,
            "devolutiva": devolutiva,
        })

    return {"sucesso": True, "atividades": atividades}


def _atividade_liberada_para(conexao, aluno_id: int, atividade_id: int):
    """A atividade, se o aluno puder mesmo vê-la. Senão, None."""
    turmas = _turmas_do_aluno(conexao, aluno_id)
    if not turmas:
        return None

    marcadores = ",".join("?" for _ in turmas)
    return conexao.execute(
        f"""
        SELECT id, titulo, enunciado, tipo, pontos, prazo, turma_id
          FROM atividades
         WHERE id = ?
           AND turma_id IN ({marcadores})
           AND rascunho = 0
           AND (data_liberacao IS NULL OR data_liberacao <= ?)
        """,
        [int(atividade_id)] + turmas + [_agora()],
    ).fetchone()


def obter_atividade_do_aluno(aluno_email: str, atividade_id: int) -> dict:
    """Enunciado, questões sem gabarito e o rascunho salvo do aluno."""
    conexao = conectar()
    aluno = buscar_usuario(conexao, aluno_email)

    if not aluno or aluno[1] != "aluno":
        conexao.close()
        return {"sucesso": False, "mensagem": "Aluno não encontrado."}

    atividade = _atividade_liberada_para(conexao, aluno[0], atividade_id)

    if not atividade:
        conexao.close()
        return {"sucesso": False, "mensagem": "Atividade não encontrada."}

    entrega = conexao.execute(
        "SELECT respostas, enviado_em, nota, devolutiva FROM entregas"
        "  WHERE atividade_id = ? AND aluno_id = ?",
        (int(atividade_id), aluno[0]),
    ).fetchone()

    questoes = _questoes_para_aluno(conexao, atividade_id)
    conexao.close()

    return {
        "sucesso": True,
        "atividade": {
            "id": atividade[0],
            "titulo": atividade[1],
            "enunciado": atividade[2],
            "tipo": atividade[3],
            "pontos": atividade[4],
            "prazo": atividade[5],
            "turma_id": atividade[6],
        },
        "questoes": questoes,
        "entrega": {
            "respostas": json.loads(entrega[0]) if entrega and entrega[0] else None,
            "enviado_em": entrega[1] if entrega else None,
            "nota": entrega[2] if entrega else None,
            "devolutiva": entrega[3] if entrega else None,
            "atrasada": _atrasada(entrega[1] if entrega else None, atividade[5]),
        },
    }


def _gravar_entrega(conexao, atividade_id: int, aluno_id: int, respostas, enviar: bool):
    """Cria ou atualiza a entrega. `enviar=False` é só progresso salvo."""
    agora = _agora()
    existente = conexao.execute(
        "SELECT id, enviado_em FROM entregas WHERE atividade_id = ? AND aluno_id = ?",
        (int(atividade_id), aluno_id),
    ).fetchone()

    corpo = json.dumps(respostas, ensure_ascii=False)

    if existente:
        conexao.execute(
            "UPDATE entregas SET respostas = ?, atualizado_em = ?"
            + (", enviado_em = ?" if enviar else "")
            + " WHERE id = ?",
            ([corpo, agora] + ([agora] if enviar else []) + [existente[0]]),
        )
        return existente[0], bool(existente[1])

    conexao.execute(
        "INSERT INTO entregas (atividade_id, aluno_id, respostas, enviado_em, atualizado_em)"
        " VALUES (?, ?, ?, ?, ?)",
        (int(atividade_id), aluno_id, corpo, agora if enviar else None, agora),
    )
    return conexao.execute("SELECT last_insert_rowid()").fetchone()[0], False


def salvar_progresso(aluno_email: str, atividade_id: int, respostas) -> dict:
    """Guarda o que o aluno respondeu até agora, sem entregar."""
    conexao = conectar()
    aluno = buscar_usuario(conexao, aluno_email)

    if not aluno or aluno[1] != "aluno":
        conexao.close()
        return {"sucesso": False, "mensagem": "Aluno não encontrado."}

    atividade = _atividade_liberada_para(conexao, aluno[0], atividade_id)

    if not atividade:
        conexao.close()
        return {"sucesso": False, "mensagem": "Atividade não encontrada."}

    ja_enviada = conexao.execute(
        "SELECT enviado_em FROM entregas WHERE atividade_id = ? AND aluno_id = ?",
        (int(atividade_id), aluno[0]),
    ).fetchone()

    if ja_enviada and ja_enviada[0]:
        conexao.close()
        return {"sucesso": False, "mensagem": "Esta atividade já foi entregue."}

    _gravar_entrega(conexao, atividade_id, aluno[0], respostas, enviar=False)
    conexao.commit()
    conexao.close()

    return {"sucesso": True, "mensagem": "Progresso salvo."}


def enviar_entrega(aluno_email: str, atividade_id: int, respostas) -> dict:
    """Entrega a atividade. Objetiva é corrigida na hora."""
    conexao = conectar()
    aluno = buscar_usuario(conexao, aluno_email)

    if not aluno or aluno[1] != "aluno":
        conexao.close()
        return {"sucesso": False, "mensagem": "Aluno não encontrado."}

    atividade = _atividade_liberada_para(conexao, aluno[0], atividade_id)

    if not atividade:
        conexao.close()
        return {"sucesso": False, "mensagem": "Atividade não encontrada."}

    ja_enviada = conexao.execute(
        "SELECT enviado_em FROM entregas WHERE atividade_id = ? AND aluno_id = ?",
        (int(atividade_id), aluno[0]),
    ).fetchone()

    if ja_enviada and ja_enviada[0]:
        conexao.close()
        return {"sucesso": False, "mensagem": "Você já entregou esta atividade."}

    tipo = atividade[3]

    if tipo == "dissertativa":
        texto = (respostas or "").strip() if isinstance(respostas, str) else ""
        if not texto:
            conexao.close()
            return {"sucesso": False, "mensagem": "Escreva a resposta antes de enviar."}
        respostas = texto

    entrega_id, _ = _gravar_entrega(conexao, atividade_id, aluno[0], respostas, enviar=True)

    resultado = {"sucesso": True, "mensagem": "Atividade entregue."}

    if tipo == "objetiva":
        gabarito = conexao.execute(
            "SELECT ordem, correta FROM questoes WHERE atividade_id = ? ORDER BY ordem",
            (int(atividade_id),),
        ).fetchall()

        escolhas = respostas if isinstance(respostas, list) else []
        acertos = sum(
            1
            for ordem, correta in gabarito
            if ordem < len(escolhas) and escolhas[ordem] == correta
        )
        total = len(gabarito)
        nota = round(atividade[4] * acertos / total, 1) if total else 0.0

        conexao.execute(
            "UPDATE entregas SET nota = ?, corrigido_em = ? WHERE id = ?",
            (nota, _agora(), entrega_id),
        )

        resultado.update({
            "mensagem": f"Atividade entregue. Você acertou {acertos} de {total}.",
            "nota": nota,
            "acertos": acertos,
            "total": total,
        })

    conexao.commit()

    prazo = atividade[5]
    conexao.close()

    resultado["atrasada"] = _atrasada(_agora(), prazo)
    return resultado
