"""Notificações da plataforma.

Antes o sino do painel do professor exibia um "5" escrito à mão no HTML e não
abria nada ao ser clicado. Aqui as notificações passam a vir de eventos que
realmente aconteceram:

- a administração matricula um aluno  -> avisa o professor da turma;
- o professor publica um material     -> avisa os alunos matriculados.

Material agendado é caso à parte: ele "vira publicado" sozinho quando a data
chega, sem ninguém executar nada. Para não depender de uma tarefa periódica, a
notificação desse tipo é criada no momento em que alguém a consulta e a data já
passou (ver `_liberar_agendados_pendentes`).
"""

from datetime import datetime, timezone

from regras.turmas import buscar_usuario, conectar

# Quantas notificações a lista devolve por padrão. O sino não é um histórico;
# passa disso, o assunto já saiu de contexto.
LIMITE_PADRAO = 20


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def criar_notificacao(user_id: int, tipo: str, titulo: str, mensagem: str, link: str = "") -> None:
    """Grava uma notificação para um usuário. Não lança: um erro aqui não pode
    derrubar a ação que a originou (matricular, publicar)."""
    try:
        conexao = conectar()
        conexao.execute(
            '''
            INSERT INTO notificacoes (user_id, tipo, titulo, mensagem, link, lida, criado_em)
            VALUES (?, ?, ?, ?, ?, 0, ?)
            ''',
            (user_id, tipo, titulo, mensagem, link, _agora()),
        )
        conexao.commit()
        conexao.close()
    except Exception:
        pass


def notificar_professor_da_turma(turma_id: int, tipo: str, titulo: str, mensagem: str, link: str = "") -> None:
    conexao = conectar()
    linha = conexao.execute("SELECT professor_id FROM turmas WHERE id = ?", (turma_id,)).fetchone()
    conexao.close()

    if linha and linha[0]:
        criar_notificacao(linha[0], tipo, titulo, mensagem, link)


def notificar_alunos_da_turma(turma_id: int, tipo: str, titulo: str, mensagem: str, link: str = "") -> None:
    conexao = conectar()
    alunos = conexao.execute(
        "SELECT aluno_id FROM matriculas WHERE turma_id = ?", (turma_id,)
    ).fetchall()
    conexao.close()

    for (aluno_id,) in alunos:
        criar_notificacao(aluno_id, tipo, titulo, mensagem, link)


def _liberar_agendados_pendentes(user_id: int) -> None:
    """Cria a notificação dos materiais agendados cuja data já chegou.

    Um material agendado passa a ser visível sozinho, sem nenhum código rodar
    na hora marcada. Em vez de manter uma tarefa periódica só para isso, a
    verificação acontece quando o usuário abre as notificações: o custo é uma
    consulta, e o aviso chega no momento em que ele olharia de qualquer forma.

    A coluna `notificado` no material impede avisar duas vezes.
    """
    conexao = conectar()
    cursor = conexao.cursor()

    usuario = cursor.execute("SELECT tipo FROM users WHERE id = ?", (user_id,)).fetchone()
    if not usuario or usuario[0] != "aluno":
        conexao.close()
        return

    agora = _agora()
    pendentes = cursor.execute(
        '''
        SELECT m.id, m.titulo, t.nome
        FROM materiais m
        JOIN turmas t ON t.id = m.turma_id
        JOIN matriculas mt ON mt.turma_id = m.turma_id
        WHERE mt.aluno_id = ?
          AND m.rascunho = 0
          AND m.data_liberacao IS NOT NULL
          AND m.data_liberacao <= ?
          AND COALESCE(m.notificado, 0) = 0
        ''',
        (user_id, agora),
    ).fetchall()
    conexao.close()

    for material_id, titulo, turma_nome in pendentes:
        criar_notificacao(
            user_id,
            "material",
            "Novo material liberado",
            f'"{titulo}" já está disponível em {turma_nome}.',
            "materiais.html",
        )

        conexao = conectar()
        conexao.execute("UPDATE materiais SET notificado = 1 WHERE id = ?", (material_id,))
        conexao.commit()
        conexao.close()


def listar_notificacoes(email: str, limite: int = LIMITE_PADRAO) -> dict:
    conexao = conectar()
    usuario = buscar_usuario(conexao, email)
    conexao.close()

    if not usuario:
        return {"sucesso": False, "mensagem": "Usuário não encontrado.", "notificacoes": [], "nao_lidas": 0}

    user_id = usuario[0]
    _liberar_agendados_pendentes(user_id)

    conexao = conectar()
    cursor = conexao.cursor()
    linhas = cursor.execute(
        '''
        SELECT id, tipo, titulo, mensagem, link, lida, criado_em
        FROM notificacoes
        WHERE user_id = ?
        ORDER BY lida ASC, criado_em DESC
        LIMIT ?
        ''',
        (user_id, limite),
    ).fetchall()

    nao_lidas = cursor.execute(
        "SELECT COUNT(*) FROM notificacoes WHERE user_id = ? AND lida = 0", (user_id,)
    ).fetchone()[0]
    conexao.close()

    notificacoes = [
        {
            "id": linha[0],
            "tipo": linha[1],
            "titulo": linha[2],
            "mensagem": linha[3],
            "link": linha[4] or "",
            "lida": bool(linha[5]),
            "criado_em": linha[6],
        }
        for linha in linhas
    ]

    return {"sucesso": True, "notificacoes": notificacoes, "nao_lidas": nao_lidas}


def marcar_como_lida(email: str, notificacao_id: int) -> dict:
    conexao = conectar()
    usuario = buscar_usuario(conexao, email)

    if not usuario:
        conexao.close()
        return {"sucesso": False, "mensagem": "Usuário não encontrado."}

    # O user_id no WHERE não é redundante: sem ele, qualquer pessoa marcaria
    # como lida a notificação de outra pessoa sabendo o id.
    cursor = conexao.cursor()
    cursor.execute(
        "UPDATE notificacoes SET lida = 1 WHERE id = ? AND user_id = ?",
        (notificacao_id, usuario[0]),
    )
    conexao.commit()
    alteradas = cursor.rowcount
    conexao.close()

    if alteradas == 0:
        return {"sucesso": False, "mensagem": "Notificação não encontrada."}

    return {"sucesso": True, "mensagem": "Notificação marcada como lida."}


def marcar_todas_como_lidas(email: str) -> dict:
    conexao = conectar()
    usuario = buscar_usuario(conexao, email)

    if not usuario:
        conexao.close()
        return {"sucesso": False, "mensagem": "Usuário não encontrado."}

    cursor = conexao.cursor()
    cursor.execute("UPDATE notificacoes SET lida = 1 WHERE user_id = ? AND lida = 0", (usuario[0],))
    conexao.commit()
    total = cursor.rowcount
    conexao.close()

    return {"sucesso": True, "mensagem": f"{total} notificação(ões) marcada(s) como lida(s).", "total": total}
