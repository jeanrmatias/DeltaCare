"""Conversa entre professor e aluno.

É o canal que faltava. O assistente de IA responde o que o material cobre e
**recusa** o resto — e até agora o que ele recusava não tinha para onde ir.

Uma conversa é o par (turma, aluno). O outro lado é sempre o professor dono da
turma, então não existe "escolher destinatário": o aluno fala com quem dá a
aula, e o professor fala com quem está matriculado. Isso não é simplificação —
é o que impede aluno mandar mensagem para professor de outra turma e professor
mandar para aluno que não é dele.

Quem pode falar com quem sai da matrícula, e a checagem está em
`_conversa_valida`, num lugar só. Toda operação passa por ela.
"""

from datetime import datetime, timezone

from regras.turmas import buscar_usuario, conectar

LIMITE_CONTEUDO = 2000


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ordem_por_data(iso) -> float:
    """Número crescente com a data, e 0 quando a conversa nunca começou.

    Serve só para ordenar: comparar strings ISO diretamente funcionaria, mas
    não daria como colocar o `None` no fim sem um caso especial no `sort`.
    """
    if not iso:
        return 0.0
    try:
        return datetime.fromisoformat(str(iso)).timestamp()
    except ValueError:
        return 0.0


def _conversa_valida(conexao, usuario, turma_id: int, aluno_email: str | None):
    """Devolve (turma_id, aluno_id, professor_id) se a conversa pode existir.

    Para o aluno, `aluno_email` é ignorado: ele só conversa como ele mesmo.
    Deixar o aluno informar o próprio id seria abrir a porta para ele ler a
    conversa de outro trocando um parâmetro.
    """
    turma = conexao.execute(
        "SELECT id, professor_id FROM turmas WHERE id = ?", (int(turma_id),)
    ).fetchone()

    if not turma:
        return None

    if usuario[1] == "aluno":
        matriculado = conexao.execute(
            "SELECT 1 FROM matriculas WHERE turma_id = ? AND aluno_id = ?",
            (turma[0], usuario[0]),
        ).fetchone()
        return (turma[0], usuario[0], turma[1]) if matriculado else None

    if usuario[1] == "professor":
        if turma[1] != usuario[0]:
            return None

        aluno = buscar_usuario(conexao, aluno_email or "")
        if not aluno or aluno[1] != "aluno":
            return None

        matriculado = conexao.execute(
            "SELECT 1 FROM matriculas WHERE turma_id = ? AND aluno_id = ?",
            (turma[0], aluno[0]),
        ).fetchone()
        return (turma[0], aluno[0], usuario[0]) if matriculado else None

    return None


def listar_conversas(email: str) -> dict:
    """As conversas de quem está logado, com a última mensagem e não lidas.

    O aluno tem uma conversa por turma. O professor tem uma por aluno
    matriculado — inclusive as que ainda não começaram, porque ele precisa
    poder puxar assunto, e não só responder.
    """
    conexao = conectar()
    usuario = buscar_usuario(conexao, email)

    if not usuario:
        conexao.close()
        return {"sucesso": False, "mensagem": "Usuário não encontrado.", "conversas": []}

    conversas = []

    if usuario[1] == "aluno":
        linhas = conexao.execute(
            """
            SELECT t.id, t.nome, t.semestre, u.email, u.nome
              FROM matriculas m
              JOIN turmas t ON t.id = m.turma_id
              JOIN users u ON u.id = t.professor_id
             WHERE m.aluno_id = ?
             ORDER BY t.nome
            """,
            (usuario[0],),
        ).fetchall()

        for turma_id, turma_nome, semestre, prof_email, prof_nome in linhas:
            conversas.append(_montar_conversa(
                conexao, turma_id, usuario[0], usuario[0],
                titulo=prof_nome or prof_email,
                subtitulo=f"{turma_nome} · {semestre}",
                turma_nome=turma_nome,
                contraparte_email=prof_email,
            ))

    elif usuario[1] == "professor":
        linhas = conexao.execute(
            """
            SELECT t.id, t.nome, t.semestre, u.id, u.email, u.nome
              FROM turmas t
              JOIN matriculas m ON m.turma_id = t.id
              JOIN users u ON u.id = m.aluno_id
             WHERE t.professor_id = ?
             ORDER BY t.nome, COALESCE(u.nome, u.email)
            """,
            (usuario[0],),
        ).fetchall()

        for turma_id, turma_nome, semestre, aluno_id, aluno_email, aluno_nome in linhas:
            conversas.append(_montar_conversa(
                conexao, turma_id, aluno_id, usuario[0],
                titulo=aluno_nome or aluno_email,
                subtitulo=f"{turma_nome} · {semestre}",
                turma_nome=turma_nome,
                contraparte_email=aluno_email,
            ))

    conexao.close()

    # Quem abre a tela vem responder, não navegar por ordem alfabética: primeiro
    # o que tem mensagem nova, depois o que se mexeu mais recentemente, e por
    # último as conversas que nunca começaram.
    conversas.sort(key=lambda c: (
        0 if c["nao_lidas"] else 1,
        -_ordem_por_data(c["ultima_em"]),
        c["titulo"].lower(),
    ))

    return {
        "sucesso": True,
        "conversas": conversas,
        "nao_lidas": sum(c["nao_lidas"] for c in conversas),
    }


def _montar_conversa(conexao, turma_id, aluno_id, eu_id, titulo, subtitulo,
                     turma_nome, contraparte_email) -> dict:
    ultima = conexao.execute(
        "SELECT conteudo, criado_em, autor_id FROM mensagens"
        "  WHERE turma_id = ? AND aluno_id = ?"
        "  ORDER BY criado_em DESC LIMIT 1",
        (turma_id, aluno_id),
    ).fetchone()

    nao_lidas = conexao.execute(
        "SELECT COUNT(*) FROM mensagens"
        "  WHERE turma_id = ? AND aluno_id = ? AND autor_id != ? AND lida = 0",
        (turma_id, aluno_id, eu_id),
    ).fetchone()[0]

    return {
        "turma_id": turma_id,
        "turma_nome": turma_nome,
        "titulo": titulo,
        "subtitulo": subtitulo,
        "contraparte_email": contraparte_email,
        "ultima_mensagem": (ultima[0][:120] if ultima else ""),
        "ultima_em": ultima[1] if ultima else None,
        "ultima_minha": bool(ultima and ultima[2] == eu_id),
        "nao_lidas": nao_lidas,
    }


def abrir_conversa(email: str, turma_id: int, aluno_email: str | None = None) -> dict:
    """As mensagens da conversa, e marca como lidas as que chegaram."""
    conexao = conectar()
    usuario = buscar_usuario(conexao, email)

    if not usuario:
        conexao.close()
        return {"sucesso": False, "mensagem": "Usuário não encontrado.", "mensagens": []}

    conversa = _conversa_valida(conexao, usuario, turma_id, aluno_email)

    if not conversa:
        conexao.close()
        return {"sucesso": False, "mensagem": "Conversa não encontrada.", "mensagens": []}

    turma, aluno_id, professor_id = conversa

    # Marcar como lida na abertura, e só o que veio do outro lado: marcar as
    # próprias zeraria o contador do interlocutor.
    conexao.execute(
        "UPDATE mensagens SET lida = 1"
        "  WHERE turma_id = ? AND aluno_id = ? AND autor_id != ? AND lida = 0",
        (turma, aluno_id, usuario[0]),
    )
    conexao.commit()

    linhas = conexao.execute(
        """
        SELECT m.id, m.conteudo, m.criado_em, m.autor_id, u.nome, u.email, u.tipo
          FROM mensagens m
          JOIN users u ON u.id = m.autor_id
         WHERE m.turma_id = ? AND m.aluno_id = ?
         ORDER BY m.criado_em
        """,
        (turma, aluno_id),
    ).fetchall()

    dados_turma = conexao.execute(
        "SELECT nome, semestre FROM turmas WHERE id = ?", (turma,)
    ).fetchone()
    conexao.close()

    return {
        "sucesso": True,
        "turma": {"id": turma, "nome": dados_turma[0], "semestre": dados_turma[1]},
        "mensagens": [
            {
                "id": id_,
                "conteudo": conteudo,
                "criado_em": criado_em,
                "minha": autor_id == usuario[0],
                "autor_nome": nome or autor_email,
                "autor_tipo": tipo,
            }
            for id_, conteudo, criado_em, autor_id, nome, autor_email, tipo in linhas
        ],
    }


def enviar_mensagem(email: str, turma_id: int, conteudo: str,
                    aluno_email: str | None = None) -> dict:
    """Escreve na conversa e avisa o outro lado."""
    conteudo = (conteudo or "").strip()

    if not conteudo:
        return {"sucesso": False, "mensagem": "Escreva a mensagem antes de enviar."}

    if len(conteudo) > LIMITE_CONTEUDO:
        return {
            "sucesso": False,
            "mensagem": f"A mensagem passa de {LIMITE_CONTEUDO} caracteres.",
        }

    conexao = conectar()
    usuario = buscar_usuario(conexao, email)

    if not usuario:
        conexao.close()
        return {"sucesso": False, "mensagem": "Usuário não encontrado."}

    conversa = _conversa_valida(conexao, usuario, turma_id, aluno_email)

    if not conversa:
        conexao.close()
        return {"sucesso": False, "mensagem": "Conversa não encontrada."}

    turma, aluno_id, professor_id = conversa

    conexao.execute(
        "INSERT INTO mensagens (turma_id, aluno_id, autor_id, conteudo, criado_em)"
        " VALUES (?, ?, ?, ?, ?)",
        (turma, aluno_id, usuario[0], conteudo, _agora()),
    )
    conexao.commit()

    turma_nome = conexao.execute(
        "SELECT nome FROM turmas WHERE id = ?", (turma,)
    ).fetchone()[0]
    conexao.close()

    from regras.notificacoes import criar_notificacao

    # Quem recebe é sempre o outro lado da conversa.
    destino = professor_id if usuario[0] == aluno_id else aluno_id

    criar_notificacao(
        destino,
        "mensagem",
        "Nova mensagem",
        f"Você recebeu uma mensagem em {turma_nome}.",
        "mensagens.html",
    )

    return {"sucesso": True, "mensagem": "Mensagem enviada."}
