"""Avisos: uma pessoa escrevendo para outras.

Diferente das notificações, que nascem sozinhas de eventos do sistema (material
publicado, nota lançada). Aqui é o professor avisando que a prova mudou de sala,
ou a coordenação avisando que não haverá aula na sexta.

- **Professor** escreve para uma, várias ou todas as disciplinas dele. Não
  escreve para disciplina alheia nem para a instituição.
- **Administração** escreve para a instituição inteira ou para disciplinas
  específicas (qualquer uma).
- **Aluno** só lê.

Quem recebe é avisado pelo sino; o aviso em si fica no mural (a tela inicial do
aluno, a tela de Avisos do professor). Urgente sobe para o topo — mas só por
DIAS_NO_TOPO: urgente para sempre deixa de ser urgente, e um aviso de três meses
atrás não pode continuar empurrando os de hoje para baixo.
"""

from datetime import datetime, timedelta, timezone

from regras.turmas import buscar_usuario, conectar

TAMANHO_TITULO = 120
TAMANHO_CONTEUDO = 4000
DIAS_NO_TOPO = 7
LIMITE_MURAL = 20

# Para onde o sino leva, conforme quem recebe.
LINK_POR_PERFIL = {"aluno": "inicio.html", "professor": "avisos.html", "adm": "avisos.html"}


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def publicar_aviso(
    autor_email: str,
    titulo: str,
    conteudo: str,
    turma_ids: list | None = None,
    geral: bool = False,
    urgente: bool = False,
) -> dict:
    titulo = (titulo or "").strip()
    conteudo = (conteudo or "").strip()
    turma_ids = sorted({int(t) for t in (turma_ids or [])})

    if not titulo or not conteudo:
        return {"sucesso": False, "mensagem": "Escreva o título e o texto do aviso."}
    if len(titulo) > TAMANHO_TITULO:
        return {"sucesso": False, "mensagem": f"Título com no máximo {TAMANHO_TITULO} caracteres."}
    if len(conteudo) > TAMANHO_CONTEUDO:
        return {"sucesso": False, "mensagem": f"Texto com no máximo {TAMANHO_CONTEUDO} caracteres."}

    conexao = conectar()
    autor = buscar_usuario(conexao, autor_email)

    if not autor or autor[1] not in ("professor", "adm"):
        conexao.close()
        return {"sucesso": False, "mensagem": "Só professor ou administração escrevem avisos."}

    autor_id, perfil = autor

    if geral and perfil != "adm":
        conexao.close()
        return {"sucesso": False, "mensagem": "Só a administração escreve para a instituição inteira."}

    if not geral and not turma_ids:
        conexao.close()
        return {"sucesso": False, "mensagem": "Escolha para quais disciplinas é o aviso."}

    # Tudo ou nada, como na publicação de material: se uma das disciplinas não
    # for do professor, nada é enviado. Envio parcial deixaria o professor sem
    # saber quem recebeu.
    if not geral:
        marcadores = ",".join("?" for _ in turma_ids)
        existentes = conexao.execute(
            f"SELECT id, professor_id FROM turmas WHERE id IN ({marcadores})", turma_ids
        ).fetchall()
        if len(existentes) != len(turma_ids):
            conexao.close()
            return {"sucesso": False, "mensagem": "Uma das disciplinas escolhidas não existe."}
        if perfil == "professor" and any(prof != autor_id for _, prof in existentes):
            conexao.close()
            return {"sucesso": False, "mensagem": "Uma das disciplinas escolhidas não é sua."}

    cursor = conexao.cursor()
    cursor.execute(
        "INSERT INTO avisos (autor_id, titulo, conteudo, urgente, geral, criado_em) VALUES (?, ?, ?, ?, ?, ?)",
        (autor_id, titulo, conteudo, 1 if urgente else 0, 1 if geral else 0, _agora()),
    )
    aviso_id = cursor.lastrowid
    cursor.executemany(
        "INSERT INTO avisos_turmas (aviso_id, turma_id) VALUES (?, ?)",
        [(aviso_id, turma_id) for turma_id in turma_ids],
    )

    destinatarios = _destinatarios(cursor, geral, turma_ids, autor_id)
    conexao.commit()
    conexao.close()

    from regras.notificacoes import criar_notificacoes

    criar_notificacoes(
        [(user_id, LINK_POR_PERFIL.get(tipo, "")) for user_id, tipo in destinatarios],
        "aviso",
        f"Urgente: {titulo}" if urgente else titulo,
        conteudo if len(conteudo) <= 140 else conteudo[:137] + "...",
    )

    quantos = len(destinatarios)
    return {
        "sucesso": True,
        "mensagem": "Aviso enviado para 1 pessoa." if quantos == 1 else f"Aviso enviado para {quantos} pessoas.",
        "aviso_id": aviso_id,
        "destinatarios": quantos,
    }


def _destinatarios(cursor, geral: bool, turma_ids: list, autor_id: int) -> list:
    """(user_id, perfil) de quem recebe, sem repetir e sem o próprio autor.

    Aviso para disciplina chega aos alunos matriculados **e ao professor dela**
    quando quem escreveu foi a administração: o professor precisa saber o que
    a coordenação disse à turma dele.
    """
    if geral:
        linhas = cursor.execute(
            "SELECT id, tipo FROM users WHERE id != ?", (autor_id,)
        ).fetchall()
        return sorted(set(linhas))

    marcadores = ",".join("?" for _ in turma_ids)
    linhas = cursor.execute(
        f"""
        SELECT u.id, u.tipo FROM matriculas m JOIN users u ON u.id = m.aluno_id
         WHERE m.turma_id IN ({marcadores})
        UNION
        SELECT u.id, u.tipo FROM turmas t JOIN users u ON u.id = t.professor_id
         WHERE t.id IN ({marcadores})
        """,
        turma_ids + turma_ids,
    ).fetchall()
    return sorted({(user_id, tipo) for user_id, tipo in linhas if user_id != autor_id})


def _formatar(linha, turmas_por_aviso: dict) -> dict:
    aviso_id, titulo, conteudo, urgente, geral, criado_em, autor_nome, autor_tipo = linha
    return {
        "id": aviso_id,
        "titulo": titulo,
        "conteudo": conteudo,
        "urgente": bool(urgente),
        "geral": bool(geral),
        "criado_em": criado_em,
        "autor": autor_nome,
        "autor_e_administracao": autor_tipo == "adm",
        "disciplinas": turmas_por_aviso.get(aviso_id, []),
    }


def _disciplinas_dos_avisos(cursor, ids: list) -> dict:
    if not ids:
        return {}
    marcadores = ",".join("?" for _ in ids)
    resultado = {}
    for aviso_id, nome in cursor.execute(
        f"""
        SELECT at.aviso_id, t.nome FROM avisos_turmas at JOIN turmas t ON t.id = at.turma_id
         WHERE at.aviso_id IN ({marcadores}) ORDER BY t.nome
        """,
        ids,
    ).fetchall():
        resultado.setdefault(aviso_id, []).append(nome)
    return resultado


_COLUNAS = """
    a.id, a.titulo, a.conteudo, a.urgente, a.geral, a.criado_em,
    COALESCE(NULLIF(u.nome, ''), u.email), u.tipo
"""


def listar_avisos_recebidos(email: str, limite: int = LIMITE_MURAL) -> dict:
    """O mural: avisos gerais e os das disciplinas da pessoa.

    Aluno recebe os das disciplinas em que está matriculado; professor, os das
    disciplinas que dá (escritos pela administração) e os gerais. O próprio
    aviso não aparece como recebido — ele está no histórico de enviados.
    """
    conexao = conectar()
    usuario = buscar_usuario(conexao, email)

    if not usuario:
        conexao.close()
        return {"sucesso": False, "mensagem": "Usuário não encontrado.", "avisos": []}

    user_id, perfil = usuario

    if perfil == "aluno":
        minhas = "SELECT turma_id FROM matriculas WHERE aluno_id = ?"
    elif perfil == "professor":
        minhas = "SELECT id FROM turmas WHERE professor_id = ?"
    else:
        minhas = "SELECT NULL WHERE ? IS NULL"  # admin: só os gerais

    corte = (datetime.now(timezone.utc) - timedelta(days=DIAS_NO_TOPO)).isoformat()
    cursor = conexao.cursor()
    linhas = cursor.execute(
        f"""
        SELECT {_COLUNAS}
          FROM avisos a JOIN users u ON u.id = a.autor_id
         WHERE a.autor_id != ?
           AND (a.geral = 1 OR a.id IN (
                SELECT aviso_id FROM avisos_turmas WHERE turma_id IN ({minhas})
           ))
         ORDER BY (a.urgente = 1 AND a.criado_em >= ?) DESC, a.criado_em DESC
         LIMIT ?
        """,
        (user_id, user_id, corte, int(limite)),
    ).fetchall()

    turmas = _disciplinas_dos_avisos(cursor, [linha[0] for linha in linhas])
    conexao.close()

    avisos = [_formatar(linha, turmas) for linha in linhas]
    for aviso in avisos:
        # A tela destaca só enquanto está no topo; depois disso é um aviso
        # comum, ainda marcado como tendo sido urgente.
        aviso["em_destaque"] = aviso["urgente"] and aviso["criado_em"] >= corte

    return {"sucesso": True, "avisos": avisos}


def listar_avisos_enviados(email: str) -> dict:
    """O histórico de quem escreve, com quantos receberam cada um."""
    conexao = conectar()
    usuario = buscar_usuario(conexao, email)

    if not usuario or usuario[1] not in ("professor", "adm"):
        conexao.close()
        return {"sucesso": False, "mensagem": "Só quem escreve avisos tem histórico.", "avisos": []}

    cursor = conexao.cursor()
    linhas = cursor.execute(
        f"""
        SELECT {_COLUNAS}
          FROM avisos a JOIN users u ON u.id = a.autor_id
         WHERE a.autor_id = ?
         ORDER BY a.criado_em DESC
        """,
        (usuario[0],),
    ).fetchall()
    turmas = _disciplinas_dos_avisos(cursor, [linha[0] for linha in linhas])
    conexao.close()

    return {"sucesso": True, "avisos": [_formatar(linha, turmas) for linha in linhas]}


def excluir_aviso(email: str, aviso_id: int) -> dict:
    """Quem escreveu pode apagar — aviso para a disciplina errada acontece.

    As notificações já entregues ficam: o sino avisou, e desfazer isso em
    silêncio não apaga o que a pessoa já leu. O que some é o aviso no mural.
    """
    conexao = conectar()
    usuario = buscar_usuario(conexao, email)
    linha = conexao.execute("SELECT autor_id FROM avisos WHERE id = ?", (int(aviso_id),)).fetchone()

    # Não existe e não é seu dão a mesma resposta.
    if not usuario or not linha or linha[0] != usuario[0]:
        conexao.close()
        return {"sucesso": False, "mensagem": "Aviso não encontrado."}

    conexao.execute("DELETE FROM avisos_turmas WHERE aviso_id = ?", (int(aviso_id),))
    conexao.execute("DELETE FROM avisos WHERE id = ?", (int(aviso_id),))
    conexao.commit()
    conexao.close()

    return {"sucesso": True, "mensagem": "Aviso apagado do mural."}
