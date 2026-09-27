"""Denúncias de conteúdo: quem reporta e quem trata.

O módulo nasceu de uma lacuna do próprio backlog. Havia cards descrevendo a
**gestão** das denúncias — receber, acompanhar, agir — e nenhum descrevendo o
**ato de denunciar**. Uma caixa de entrada sem porta de entrada.

Por isso os dois lados vivem neste arquivo, e nenhum dos dois pode ser
implementado sozinho sem repetir a lacuna:

- `criar_denuncia`  — aluno ou professor reporta um material que enxerga.
- `listar_minhas`   — quem reportou acompanha o andamento.
- `listar_todas`    — a administração recebe.
- `tratar_denuncia` — a administração muda o status, registra a ação e **avisa
                      quem reportou**. Sem esse aviso, denunciar vira um buraco
                      onde a pessoa joga o problema e nunca sabe o que houve.
"""

from datetime import datetime, timezone

from regras.turmas import buscar_usuario, conectar

MOTIVOS = {
    "incorreto": "Conteúdo incorreto ou desatualizado",
    "ofensivo": "Conteúdo ofensivo ou inadequado",
    "fora_do_tema": "Material fora do tema da turma",
    "problema_tecnico": "Arquivo não abre ou está corrompido",
    "direitos_autorais": "Possível violação de direitos autorais",
    "outro": "Outro motivo",
}

STATUS = {
    "aberta": "Aberta",
    "em_analise": "Em análise",
    "concluida": "Concluída",
    "arquivada": "Arquivada",
}


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _linha_para_dict(linha) -> dict:
    (id_, motivo, descricao, status, acao, criado_em, atualizado_em,
     material_id, material_titulo, turma_id, autor_email, autor_nome, turma_nome) = linha

    return {
        "id": id_,
        "motivo": motivo,
        "motivo_rotulo": MOTIVOS.get(motivo, motivo),
        "descricao": descricao or "",
        "status": status,
        "status_rotulo": STATUS.get(status, status),
        "acao": acao or "",
        "criado_em": criado_em,
        "atualizado_em": atualizado_em,
        "material_id": material_id,
        "material_titulo": material_titulo or "(material removido)",
        "turma_id": turma_id,
        "turma_nome": turma_nome or "",
        "autor_email": autor_email,
        "autor_nome": autor_nome or autor_email,
    }


CONSULTA_BASE = """
    SELECT d.id, d.motivo, d.descricao, d.status, d.acao, d.criado_em, d.atualizado_em,
           d.material_id, d.material_titulo, d.turma_id,
           u.email, u.nome, t.nome
      FROM denuncias d
      JOIN users u ON u.id = d.autor_id
      LEFT JOIN turmas t ON t.id = d.turma_id
"""


# =========================================================================
# Quem reporta
# =========================================================================

def _material_visivel_para(conexao, usuario, material_id: int):
    """O material, se essa pessoa puder mesmo enxergá-lo.

    Sem esta checagem daria para descobrir o título de material de outra turma
    só denunciando ids no chute — e a denúncia devolve o título na resposta.
    """
    if usuario[1] == "professor":
        return conexao.execute(
            "SELECT m.id, m.titulo, m.turma_id FROM materiais m"
            "  JOIN turmas t ON t.id = m.turma_id"
            " WHERE m.id = ? AND t.professor_id = ?",
            (int(material_id), usuario[0]),
        ).fetchone()

    if usuario[1] == "aluno":
        # Só material publicado das turmas em que está matriculado — a mesma
        # regra da listagem dele.
        return conexao.execute(
            """
            SELECT m.id, m.titulo, m.turma_id
              FROM materiais m
              JOIN matriculas mt ON mt.turma_id = m.turma_id
             WHERE m.id = ? AND mt.aluno_id = ?
               AND m.rascunho = 0
               AND (m.data_liberacao IS NULL OR m.data_liberacao <= ?)
            """,
            (int(material_id), usuario[0], _agora()),
        ).fetchone()

    return None


def criar_denuncia(autor_email: str, material_id: int, motivo: str, descricao: str = "") -> dict:
    """Registra uma denúncia de material."""
    if motivo not in MOTIVOS:
        return {"sucesso": False, "mensagem": "Escolha um motivo válido."}

    descricao = (descricao or "").strip()

    if motivo == "outro" and not descricao:
        return {
            "sucesso": False,
            "mensagem": "Quando o motivo é \"outro\", descreva o problema.",
        }

    conexao = conectar()
    autor = buscar_usuario(conexao, autor_email)

    if not autor:
        conexao.close()
        return {"sucesso": False, "mensagem": "Usuário não encontrado."}

    if autor[1] == "adm":
        conexao.close()
        return {
            "sucesso": False,
            "mensagem": "A administração trata denúncias; quem reporta é aluno ou professor.",
        }

    material = _material_visivel_para(conexao, autor, material_id)

    if not material:
        conexao.close()
        return {"sucesso": False, "mensagem": "Material não encontrado."}

    # Uma denúncia aberta por pessoa e material. Reportar de novo não cria
    # fila duplicada para a administração tratar duas vezes o mesmo caso.
    repetida = conexao.execute(
        "SELECT id FROM denuncias"
        "  WHERE autor_id = ? AND material_id = ? AND status IN ('aberta', 'em_analise')",
        (autor[0], int(material_id)),
    ).fetchone()

    if repetida:
        conexao.close()
        return {
            "sucesso": False,
            "mensagem": "Você já reportou este material e a análise ainda está em andamento.",
        }

    agora = _agora()
    conexao.execute(
        """
        INSERT INTO denuncias (autor_id, material_id, material_titulo, turma_id,
                               motivo, descricao, status, criado_em, atualizado_em)
        VALUES (?, ?, ?, ?, ?, ?, 'aberta', ?, ?)
        """,
        (autor[0], material[0], material[1], material[2], motivo, descricao, agora, agora),
    )
    conexao.commit()
    conexao.close()

    from regras.notificacoes import criar_notificacao

    # A administração inteira é avisada: não há "dono" da fila de denúncias, e
    # depender de alguém abrir a tela por acaso é como não avisar.
    conexao = conectar()
    admins = conexao.execute("SELECT id FROM users WHERE tipo = 'adm'").fetchall()
    conexao.close()

    for (admin_id,) in admins:
        criar_notificacao(
            admin_id,
            "denuncia",
            "Novo conteúdo reportado",
            f'"{material[1]}" foi reportado: {MOTIVOS[motivo]}.',
            "denuncias.html",
        )

    return {"sucesso": True, "mensagem": "Denúncia registrada. Você será avisado do resultado."}


def listar_minhas(autor_email: str) -> dict:
    """O que a própria pessoa reportou, com o andamento."""
    conexao = conectar()
    autor = buscar_usuario(conexao, autor_email)

    if not autor:
        conexao.close()
        return {"sucesso": False, "mensagem": "Usuário não encontrado.", "denuncias": []}

    linhas = conexao.execute(
        CONSULTA_BASE + " WHERE d.autor_id = ? ORDER BY d.criado_em DESC",
        (autor[0],),
    ).fetchall()
    conexao.close()

    return {
        "sucesso": True,
        "denuncias": [_linha_para_dict(l) for l in linhas],
        # A lista de motivos vai junto para o formulário não ter uma cópia dela
        # no JavaScript. Duas listas iguais em lugares diferentes viram duas
        # listas diferentes no dia em que alguém acrescenta um motivo.
        "motivos": [{"valor": v, "rotulo": r} for v, r in MOTIVOS.items()],
    }


# =========================================================================
# Quem trata
# =========================================================================

def listar_todas(admin_email: str, status: str | None = None) -> dict:
    """A fila da administração."""
    conexao = conectar()
    admin = buscar_usuario(conexao, admin_email)

    if not admin or admin[1] != "adm":
        conexao.close()
        return {"sucesso": False, "mensagem": "Só a administração vê as denúncias.", "denuncias": []}

    consulta = CONSULTA_BASE
    parametros = []

    if status and status in STATUS:
        consulta += " WHERE d.status = ?"
        parametros.append(status)

    # Abertas primeiro: a fila existe para ser trabalhada, não para ser lida
    # em ordem cronológica.
    consulta += """
        ORDER BY CASE d.status
                   WHEN 'aberta' THEN 0
                   WHEN 'em_analise' THEN 1
                   ELSE 2
                 END,
                 d.criado_em DESC
    """

    linhas = conexao.execute(consulta, parametros).fetchall()

    contagem = dict(conexao.execute(
        "SELECT status, COUNT(*) FROM denuncias GROUP BY status"
    ).fetchall())
    conexao.close()

    return {
        "sucesso": True,
        "denuncias": [_linha_para_dict(l) for l in linhas],
        "resumo": {
            "abertas": contagem.get("aberta", 0),
            "em_analise": contagem.get("em_analise", 0),
            "concluidas": contagem.get("concluida", 0),
            "arquivadas": contagem.get("arquivada", 0),
        },
    }


def tratar_denuncia(admin_email: str, denuncia_id: int, status: str, acao: str = "") -> dict:
    """Muda o status, registra o que foi feito e avisa quem reportou."""
    if status not in STATUS:
        return {"sucesso": False, "mensagem": "Status inválido."}

    acao = (acao or "").strip()

    # Fechar sem dizer o que foi feito transforma a denúncia num buraco: quem
    # reportou recebe "concluída" e não sabe se algo mudou.
    if status in ("concluida", "arquivada") and not acao:
        return {
            "sucesso": False,
            "mensagem": "Descreva a ação tomada antes de encerrar a denúncia.",
        }

    conexao = conectar()
    admin = buscar_usuario(conexao, admin_email)

    if not admin or admin[1] != "adm":
        conexao.close()
        return {"sucesso": False, "mensagem": "Só a administração trata denúncias."}

    denuncia = conexao.execute(
        "SELECT id, autor_id, material_titulo, status FROM denuncias WHERE id = ?",
        (int(denuncia_id),),
    ).fetchone()

    if not denuncia:
        conexao.close()
        return {"sucesso": False, "mensagem": "Denúncia não encontrada."}

    conexao.execute(
        "UPDATE denuncias SET status = ?, acao = ?, atualizado_em = ? WHERE id = ?",
        (status, acao or None, _agora(), int(denuncia_id)),
    )
    conexao.commit()
    conexao.close()

    if status != denuncia[3]:
        from regras.notificacoes import criar_notificacao

        criar_notificacao(
            denuncia[1],
            "denuncia",
            "Sua denúncia foi atualizada",
            f'"{denuncia[2]}": {STATUS[status].lower()}.',
            "denuncias.html",
        )

    return {"sucesso": True, "mensagem": "Denúncia atualizada."}
