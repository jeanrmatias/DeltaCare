"""Direitos do titular (LGPD): o aluno pede, e o pedido segue o tipo.

Decisões da instituição, todas aqui para mudar num lugar só:

- **Cópia dos dados** é automática: o aluno baixa na hora. É o direito de
  acesso e de portabilidade, e não há o que a administração avaliar — são os
  dados dele, para ele.
- **Correção** (nome, e-mail, matrícula) passa pela administração: é ela que
  confere com o registro acadêmico antes de trocar.
- **Exclusão da conta** passa pela administração e é **anonimização**, não
  apagamento. Aprovada, a conta é desativada na hora (não entra mais) e,
  45 dias depois, perde nome, e-mail e o que é pessoal. Notas, entregas e
  matrículas ficam, sem dono identificável: a faculdade é obrigada a guardar
  o registro acadêmico. Nos 45 dias a administração pode voltar atrás — é o
  caso do aluno que trancou e vai ser realocado.

A **administração é a encarregada pelo tratamento de dados (DPO)**, por
decisão da instituição: é ela que decide os pedidos e que pode, por conta
própria, excluir a conta de um aluno ou professor que deixou a faculdade
(`excluir_pela_administracao`) — com o mesmo prazo de 45 dias para voltar
atrás. O professor apaga o próprio conteúdo (material, atividade, aviso) nas
telas dele; a administração não despublica material de professor.

O que a anonimização apaga e o que guarda está em `_anonimizar`, com o
motivo de cada linha.
"""

import json
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

from infra.security import hash_senha
from regras.importacao import _parece_email
from regras.notificacoes import criar_notificacao, criar_notificacoes
from regras.turmas import buscar_usuario, conectar, conflito_ao_passar, passar_disciplina

PRAZO_ANONIMIZACAO_DIAS = 45

TIPOS = {
    "exportacao": "Cópia dos meus dados",
    "correcao": "Correção de dados",
    "exclusao": "Exclusão da conta",
}

# O que não passa pela administração. Para mudar a política, é esta linha.
AUTOMATICOS = {"exportacao"}

CAMPOS_CORRIGIVEIS = {"nome": "Nome", "email": "E-mail", "matricula": "Matrícula"}

LIMITE_TEXTO = 500


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _eh_admin(conexao, email: str) -> int | None:
    usuario = buscar_usuario(conexao, email)
    return usuario[0] if usuario and usuario[1] == "adm" else None


def _aluno(conexao, email: str):
    usuario = buscar_usuario(conexao, email)
    return usuario[0] if usuario and usuario[1] == "aluno" else None


# =========================================================================
# Lado do aluno
# =========================================================================

def solicitar(aluno_email: str, tipo: str, campo: str = "", valor_novo: str = "", motivo: str = "") -> dict:
    """Registra um pedido de correção ou de exclusão.

    A cópia dos dados não passa por aqui: é `exportar_dados`, na hora.
    """
    campo = (campo or "").strip()
    valor_novo = (valor_novo or "").strip()
    motivo = (motivo or "").strip()

    if tipo not in TIPOS or tipo in AUTOMATICOS:
        return {"sucesso": False, "mensagem": "Tipo de pedido inválido."}
    if len(motivo) > LIMITE_TEXTO or len(valor_novo) > LIMITE_TEXTO:
        return {"sucesso": False, "mensagem": f"O texto passa de {LIMITE_TEXTO} caracteres."}

    if tipo == "correcao":
        if campo not in CAMPOS_CORRIGIVEIS:
            return {"sucesso": False, "mensagem": "Escolha qual dado corrigir."}
        if not valor_novo:
            return {"sucesso": False, "mensagem": "Informe o valor correto."}
        if campo == "email":
            valor_novo = valor_novo.lower()
            if not _parece_email(valor_novo):
                return {"sucesso": False, "mensagem": "Esse e-mail não parece válido."}
    else:
        campo, valor_novo = "", ""

    conexao = conectar()
    aluno_id = _aluno(conexao, aluno_email)
    if not aluno_id:
        conexao.close()
        return {"sucesso": False, "mensagem": "Só a conta de aluno faz esse pedido por aqui."}

    # Um pedido em aberto por tipo: o segundo igual só duplicaria a fila da
    # administração. Correção de campo diferente é outro pedido.
    em_aberto = conexao.execute(
        "SELECT 1 FROM solicitacoes_privacidade"
        " WHERE aluno_id = ? AND tipo = ? AND status IN ('pendente', 'agendada')"
        "   AND COALESCE(campo, '') = ?",
        (aluno_id, tipo, campo),
    ).fetchone()
    if em_aberto:
        conexao.close()
        return {"sucesso": False, "mensagem": "Você já tem um pedido desse em andamento."}

    cursor = conexao.cursor()
    try:
        cursor.execute(
            "INSERT INTO solicitacoes_privacidade"
            " (aluno_id, tipo, status, campo, valor_novo, motivo, criado_em)"
            " VALUES (?, ?, 'pendente', ?, ?, ?, ?)",
            (aluno_id, tipo, campo or None, valor_novo or None, motivo or None, _agora().isoformat()),
        )
    except sqlite3.IntegrityError:
        # Outra requisição igual chegou primeiro (infra/database.UNICIDADES).
        conexao.close()
        return {"sucesso": False, "mensagem": "Você já tem um pedido desse em andamento."}
    solicitacao_id = cursor.lastrowid
    nome = conexao.execute(
        "SELECT COALESCE(NULLIF(nome, ''), email) FROM users WHERE id = ?", (aluno_id,)
    ).fetchone()[0]
    admins = conexao.execute("SELECT id FROM users WHERE tipo = 'adm'").fetchall()
    conexao.commit()
    conexao.close()

    criar_notificacoes(
        [(admin_id, "solicitacoes.html") for (admin_id,) in admins],
        "privacidade",
        "Novo pedido sobre dados pessoais",
        f"{nome}: {TIPOS[tipo].lower()}.",
    )
    return {"sucesso": True, "mensagem": "Pedido enviado à administração.", "id": solicitacao_id}


def cancelar(aluno_email: str, solicitacao_id: int) -> dict:
    conexao = conectar()
    aluno_id = _aluno(conexao, aluno_email)
    cursor = conexao.cursor()
    # O aluno_id no WHERE é o que impede cancelar o pedido de outra pessoa.
    cursor.execute(
        "UPDATE solicitacoes_privacidade SET status = 'cancelada', concluido_em = ?"
        " WHERE id = ? AND aluno_id = ? AND status = 'pendente'",
        (_agora().isoformat(), int(solicitacao_id), aluno_id or -1),
    )
    alterou = cursor.rowcount
    conexao.commit()
    conexao.close()

    if not alterou:
        return {"sucesso": False, "mensagem": "Pedido não encontrado ou já decidido."}
    return {"sucesso": True, "mensagem": "Pedido cancelado."}


def _linha_para_dict(linha) -> dict:
    (sid, tipo, status, campo, valor_novo, motivo, resposta,
     criado_em, decidido_em, anonimizar_em, concluido_em, origem) = linha
    return {
        "id": sid,
        "origem": origem,
        "tipo": tipo,
        "tipo_rotulo": TIPOS.get(tipo, tipo),
        "status": status,
        "campo": campo,
        "campo_rotulo": CAMPOS_CORRIGIVEIS.get(campo, campo) if campo else None,
        "valor_novo": valor_novo,
        "motivo": motivo,
        "resposta": resposta,
        "criado_em": criado_em,
        "decidido_em": decidido_em,
        "anonimizar_em": anonimizar_em,
        "concluido_em": concluido_em,
    }


_COLUNAS = (
    "s.id, s.tipo, s.status, s.campo, s.valor_novo, s.motivo, s.resposta,"
    " s.criado_em, s.decidido_em, s.anonimizar_em, s.concluido_em, s.origem"
)


def listar_minhas(aluno_email: str) -> dict:
    conexao = conectar()
    aluno_id = _aluno(conexao, aluno_email)
    linhas = conexao.execute(
        f"SELECT {_COLUNAS} FROM solicitacoes_privacidade s"
        " WHERE s.aluno_id = ? ORDER BY s.criado_em DESC, s.id DESC",
        (aluno_id or -1,),
    ).fetchall()
    conexao.close()
    return {
        "sucesso": True,
        "prazo_anonimizacao_dias": PRAZO_ANONIMIZACAO_DIAS,
        "solicitacoes": [_linha_para_dict(linha) for linha in linhas],
    }


def exportar_dados(aluno_email: str) -> dict:
    """Tudo o que a plataforma guarda sobre o aluno, legível por gente.

    Fica de fora só o que não é dado *dele*: o hash da senha (não serve a
    ninguém e ajudaria um ataque se o arquivo vazasse) e os tokens de sessão.
    """
    conexao = conectar()
    aluno_id = _aluno(conexao, aluno_email)
    if not aluno_id:
        conexao.close()
        return {"sucesso": False, "mensagem": "Só a conta de aluno exporta por aqui."}

    def todas(sql, parametros=(aluno_id,)):
        cursor = conexao.execute(sql, parametros)
        nomes = [coluna[0] for coluna in cursor.description]
        return [dict(zip(nomes, linha)) for linha in cursor.fetchall()]

    agora = _agora().isoformat()
    titular = todas(
        "SELECT nome, email, matricula, tipo, ranking_oculto FROM users WHERE id = ?"
    )[0]
    titular["aparece_no_ranking"] = not titular.pop("ranking_oculto")

    dados = {
        "gerado_em": agora,
        "plataforma": "Delta Care",
        "titular": titular,
        "turmas_de_alunos": todas(
            "SELECT c.nome, c.semestre, mc.criado_em AS desde"
            "  FROM matriculas_coorte mc JOIN coortes c ON c.id = mc.coorte_id"
            " WHERE mc.aluno_id = ? ORDER BY c.semestre"
        ),
        "disciplinas": todas(
            "SELECT t.nome, t.semestre, COALESCE(p.nome, p.email) AS professor, m.criado_em AS desde"
            "  FROM matriculas m JOIN turmas t ON t.id = m.turma_id"
            "  LEFT JOIN users p ON p.id = t.professor_id"
            " WHERE m.aluno_id = ? ORDER BY t.semestre, t.nome"
        ),
        "entregas": todas(
            "SELECT a.titulo AS atividade, t.nome AS disciplina, a.tipo, e.respostas,"
            "       e.enviado_em, e.nota, e.devolutiva, e.corrigido_em, e.arquivo_nome"
            "  FROM entregas e JOIN atividades a ON a.id = e.atividade_id"
            "  JOIN turmas t ON t.id = a.turma_id"
            " WHERE e.aluno_id = ? ORDER BY e.enviado_em"
        ),
        "materiais_abertos": todas(
            "SELECT m.titulo AS material, t.nome AS disciplina, x.criado_em AS quando"
            "  FROM acessos_material x JOIN materiais m ON m.id = x.material_id"
            "  JOIN turmas t ON t.id = m.turma_id"
            " WHERE x.aluno_id = ? ORDER BY x.criado_em"
        ),
        "favoritos": todas(
            "SELECT m.titulo AS material, f.criado_em AS desde"
            "  FROM favoritos f JOIN materiais m ON m.id = f.material_id"
            " WHERE f.aluno_id = ? ORDER BY f.criado_em"
        ),
        "anotacoes": todas(
            "SELECT material_titulo AS material, trecho, texto, criado_em, atualizado_em"
            "  FROM anotacoes WHERE aluno_id = ? ORDER BY criado_em"
        ),
        "conversas_com_o_assistente": todas(
            # LEFT JOIN: pergunta do modo automático que nenhum material
            # respondeu não tem disciplina, e continua sendo dado do aluno.
            "SELECT coalesce(t.nome, 'Automático (sem disciplina)') AS disciplina,"
            "       CASE c.papel WHEN 'user' THEN 'você' ELSE 'assistente' END AS autor,"
            "       c.conteudo, c.criado_em"
            "  FROM chat_mensagens c LEFT JOIN turmas t ON t.id = c.turma_id"
            # Apagada pelo aluno não tem mais texto: não há o que entregar.
            " WHERE c.aluno_id = ? AND c.apagada_em IS NULL ORDER BY c.criado_em"
        ),
        "mensagens_com_professores": todas(
            "SELECT t.nome AS disciplina,"
            "       CASE WHEN m.autor_id = m.aluno_id THEN 'você' ELSE 'professor' END AS autor,"
            "       m.conteudo, m.criado_em"
            "  FROM mensagens m JOIN turmas t ON t.id = m.turma_id"
            " WHERE m.aluno_id = ? ORDER BY m.criado_em"
        ),
        "denuncias_feitas": todas(
            "SELECT material_titulo AS material, motivo, descricao, status, criado_em"
            "  FROM denuncias WHERE autor_id = ? ORDER BY criado_em"
        ),
        "notificacoes": todas(
            "SELECT titulo, mensagem, lida, criado_em FROM notificacoes"
            " WHERE user_id = ? ORDER BY criado_em"
        ),
        "pedidos_sobre_dados_pessoais": todas(
            "SELECT tipo, status, campo, valor_novo, motivo, resposta, criado_em, decidido_em"
            "  FROM solicitacoes_privacidade WHERE aluno_id = ? ORDER BY criado_em"
        ),
    }

    for entrega in dados["entregas"]:
        # Objetiva guarda JSON (as alternativas marcadas); dissertativa, texto.
        try:
            entrega["respostas"] = json.loads(entrega["respostas"])
        except (TypeError, ValueError):
            pass

    # Registro de que a cópia foi entregue: quem atende pedido de titular
    # precisa conseguir mostrar que atendeu, e quando.
    conexao.execute(
        "INSERT INTO solicitacoes_privacidade"
        " (aluno_id, tipo, status, criado_em, concluido_em)"
        " VALUES (?, 'exportacao', 'concluida', ?, ?)",
        (aluno_id, agora, agora),
    )
    conexao.commit()
    conexao.close()

    return {"sucesso": True, "dados": dados}


# =========================================================================
# Lado da administração
# =========================================================================

def listar_solicitacoes(admin_email: str, status: str = "") -> dict:
    conexao = conectar()
    if not _eh_admin(conexao, admin_email):
        conexao.close()
        return {"sucesso": False, "mensagem": "Acesso restrito à administração.", "solicitacoes": []}
    conexao.close()

    # Quem abre a fila vê o estado de hoje: as exclusões vencidas são
    # anonimizadas antes da lista ser montada, e não só na rotina diária.
    anonimizar_vencidas()

    conexao = conectar()
    filtro, parametros = "", []
    if status:
        filtro, parametros = " WHERE s.status = ?", [status]

    linhas = conexao.execute(
        f"SELECT {_COLUNAS}, s.aluno_id, u.nome, u.email, u.matricula, u.anonimizado_em, u.tipo"
        "  FROM solicitacoes_privacidade s JOIN users u ON u.id = s.aluno_id"
        f"{filtro}"
        # A exportação é automática: na fila só polui. Fica no histórico do aluno.
        f" {'AND' if filtro else 'WHERE'} s.tipo != 'exportacao'"
        " ORDER BY CASE s.status WHEN 'pendente' THEN 0 WHEN 'agendada' THEN 1 ELSE 2 END,"
        "          s.criado_em DESC",
        parametros,
    ).fetchall()
    contagem = dict(conexao.execute(
        "SELECT status, COUNT(*) FROM solicitacoes_privacidade"
        " WHERE tipo != 'exportacao' GROUP BY status"
    ).fetchall())
    conexao.close()

    solicitacoes = []
    for linha in linhas:
        item = _linha_para_dict(linha[:12])
        aluno_id, nome, email, matricula, anonimizado_em, tipo_conta = linha[12:]
        item["aluno"] = {
            "id": aluno_id,
            "tipo": tipo_conta,
            "nome": nome,
            "email": email,
            "matricula": matricula,
            "anonimizado": bool(anonimizado_em),
        }
        # Para a correção, o valor de hoje ao lado do pedido: decidir sem ver
        # o que vai ser trocado é aprovar no escuro.
        if item["tipo"] == "correcao" and item["campo"] in CAMPOS_CORRIGIVEIS:
            item["valor_atual"] = {"nome": nome, "email": email, "matricula": matricula}[item["campo"]]
        solicitacoes.append(item)

    return {
        "sucesso": True,
        "prazo_anonimizacao_dias": PRAZO_ANONIMIZACAO_DIAS,
        "contagem": contagem,
        "solicitacoes": solicitacoes,
    }


def decidir(admin_email: str, solicitacao_id: int, aprovar: bool, resposta: str = "") -> dict:
    resposta = (resposta or "").strip()
    if len(resposta) > LIMITE_TEXTO:
        return {"sucesso": False, "mensagem": f"A resposta passa de {LIMITE_TEXTO} caracteres."}

    conexao = conectar()
    admin_id = _eh_admin(conexao, admin_email)
    if not admin_id:
        conexao.close()
        return {"sucesso": False, "mensagem": "Acesso restrito à administração."}

    linha = conexao.execute(
        "SELECT s.aluno_id, s.tipo, s.campo, s.valor_novo, u.email"
        "  FROM solicitacoes_privacidade s JOIN users u ON u.id = s.aluno_id"
        " WHERE s.id = ? AND s.status = 'pendente'",
        (int(solicitacao_id),),
    ).fetchone()
    if not linha:
        conexao.close()
        return {"sucesso": False, "mensagem": "Pedido não encontrado ou já decidido."}

    aluno_id, tipo, campo, valor_novo, email_do_aluno = linha
    agora = _agora()

    if not aprovar:
        if not resposta:
            conexao.close()
            return {"sucesso": False, "mensagem": "Diga ao aluno por que o pedido foi recusado."}
        conexao.execute(
            "UPDATE solicitacoes_privacidade SET status = 'recusada', resposta = ?,"
            " decidido_em = ?, decidido_por = ?, concluido_em = ? WHERE id = ?",
            (resposta, agora.isoformat(), admin_id, agora.isoformat(), int(solicitacao_id)),
        )
        conexao.commit()
        conexao.close()
        criar_notificacao(aluno_id, "privacidade", f"{TIPOS[tipo]}: pedido recusado", resposta,
                          "meus-dados.html")
        return {"sucesso": True, "mensagem": "Pedido recusado. O aluno foi avisado."}

    if tipo == "correcao":
        if campo == "email" and conexao.execute(
            "SELECT 1 FROM users WHERE email = ? AND id != ?", (valor_novo, aluno_id)
        ).fetchone():
            conexao.close()
            return {"sucesso": False, "mensagem": "Esse e-mail já é de outra conta."}

        # `campo` veio da lista fechada CAMPOS_CORRIGIVEIS na hora do pedido:
        # por isso pode entrar no SQL. Valor sempre por parâmetro.
        conexao.execute(f"UPDATE users SET {campo} = ? WHERE id = ?", (valor_novo, aluno_id))
        conexao.execute(
            "UPDATE solicitacoes_privacidade SET status = 'concluida', resposta = ?,"
            " decidido_em = ?, decidido_por = ?, concluido_em = ? WHERE id = ?",
            (resposta or None, agora.isoformat(), admin_id, agora.isoformat(), int(solicitacao_id)),
        )
        conexao.commit()
        conexao.close()
        criar_notificacao(
            aluno_id, "privacidade", "Dado corrigido",
            f"{CAMPOS_CORRIGIVEIS[campo]} atualizado." + (" Use o novo e-mail para entrar." if campo == "email" else ""),
            "meus-dados.html",
        )
        return {"sucesso": True, "mensagem": "Dado corrigido."}

    # Exclusão: desativa agora, anonimiza no fim do prazo.
    anonimizar_em = agora + timedelta(days=PRAZO_ANONIMIZACAO_DIAS)
    conexao.execute("UPDATE users SET desativado_em = ? WHERE id = ?", (agora.isoformat(), aluno_id))
    # Sessões abertas morrem junto: desativar e deixar o aluno logado até o
    # token expirar seria desativar só no papel.
    conexao.execute("DELETE FROM sessoes WHERE user_id = ?", (aluno_id,))
    conexao.execute(
        "UPDATE solicitacoes_privacidade SET status = 'agendada', resposta = ?,"
        " decidido_em = ?, decidido_por = ?, anonimizar_em = ? WHERE id = ?",
        (resposta or None, agora.isoformat(), admin_id, anonimizar_em.isoformat(), int(solicitacao_id)),
    )
    # Os outros pedidos em aberto perdem o sentido com a conta desativada.
    conexao.execute(
        "UPDATE solicitacoes_privacidade SET status = 'cancelada', concluido_em = ?,"
        " resposta = 'Cancelado com a exclusão da conta.'"
        " WHERE aluno_id = ? AND status = 'pendente'",
        (agora.isoformat(), aluno_id),
    )
    conexao.commit()
    conexao.close()

    # Por e-mail, porque o aluno já não entra para ver notificação.
    from infra.email import enviar_em_segundo_plano

    data = anonimizar_em.strftime("%d/%m/%Y")
    enviar_em_segundo_plano(
        email_do_aluno,
        "Delta Care — exclusão da sua conta",
        "Seu pedido de exclusão da conta no Delta Care foi aprovado.\n\n"
        "A conta já está desativada. Em " + data + " seus dados pessoais serão "
        "anonimizados: nome, e-mail, anotações, favoritos e conversas deixam de existir. "
        "Notas e entregas continuam no registro acadêmico da instituição, sem identificação.\n\n"
        "Até essa data, se mudar de ideia, fale com a secretaria acadêmica.\n",
    )
    return {
        "sucesso": True,
        "mensagem": f"Conta desativada. Os dados pessoais serão anonimizados em {data}.",
        "anonimizar_em": anonimizar_em.isoformat(),
    }


def excluir_pela_administracao(admin_email: str, email: str, motivo: str, novo_professor_email: str = "") -> dict:
    """A administração exclui a conta de um aluno ou professor que saiu.

    Mesmo caminho do pedido do aluno, já aprovado: desativa agora, anonimiza
    em PRAZO_ANONIMIZACAO_DIAS, e até lá dá para voltar atrás na tela
    Privacidade. O motivo é obrigatório — é o registro de por que a
    instituição tratou o dado de alguém sem ele pedir.

    Professor com disciplina precisa de quem as assuma (`novo_professor_email`):
    o material, as atividades e as notas são do curso e continuam com os
    alunos. A passagem não volta se a exclusão for desfeita — a essa altura o
    outro professor já pode ter publicado e corrigido.
    """
    motivo = (motivo or "").strip()
    if not motivo:
        return {"sucesso": False, "mensagem": "Diga o motivo da exclusão. Ele fica registrado."}
    if len(motivo) > LIMITE_TEXTO:
        return {"sucesso": False, "mensagem": f"O motivo passa de {LIMITE_TEXTO} caracteres."}

    conexao = conectar()
    try:
        admin_id = _eh_admin(conexao, admin_email)
        if not admin_id:
            return {"sucesso": False, "mensagem": "Acesso restrito à administração."}
        alvo = conexao.execute(
            "SELECT id, tipo, nome, email, desativado_em FROM users WHERE email = ?", ((email or "").strip().lower(),)
        ).fetchone()
        if not alvo:
            return {"sucesso": False, "mensagem": "Conta não encontrada."}
        alvo_id, tipo_conta, nome, email_alvo, desativado_em = alvo
        if tipo_conta not in ("aluno", "professor"):
            return {"sucesso": False, "mensagem": "Por aqui só se exclui conta de aluno ou de professor."}
        if desativado_em:
            return {"sucesso": False, "mensagem": "Essa conta já está desativada."}

        disciplinas = [linha[0] for linha in conexao.execute("SELECT id FROM turmas WHERE professor_id = ?", (alvo_id,))]
        novo_id = None
        if disciplinas:
            novo = conexao.execute(
                "SELECT id FROM users WHERE email = ? AND tipo = 'professor' AND desativado_em IS NULL AND id != ?",
                ((novo_professor_email or "").strip().lower(), alvo_id),
            ).fetchone()
            if not novo:
                quais = "a disciplina" if len(disciplinas) == 1 else f"as {len(disciplinas)} disciplinas"
                return {"sucesso": False, "mensagem": f"Escolha quem assume {quais} deste professor."}
            novo_id = novo[0]

        conflito = conflito_ao_passar(conexao, disciplinas, novo_id)
        if conflito:
            return {"sucesso": False, "mensagem": conflito}

        agora = _agora()
        anonimizar_em = agora + timedelta(days=PRAZO_ANONIMIZACAO_DIAS)
        if novo_id is not None:
            for turma_id in disciplinas:
                passar_disciplina(conexao, turma_id, novo_id)
        conexao.execute("UPDATE users SET desativado_em = ? WHERE id = ?", (agora.isoformat(), alvo_id))
        conexao.execute("DELETE FROM sessoes WHERE user_id = ?", (alvo_id,))
        conexao.execute(
            "UPDATE solicitacoes_privacidade SET status = 'cancelada', concluido_em = ?,"
            " resposta = 'Cancelado com a exclusão da conta.'"
            " WHERE aluno_id = ? AND status = 'pendente'",
            (agora.isoformat(), alvo_id),
        )
        conexao.execute(
            "INSERT INTO solicitacoes_privacidade (aluno_id, tipo, status, motivo, criado_em, decidido_em,"
            " decidido_por, anonimizar_em, origem) VALUES (?, 'exclusao', 'agendada', ?, ?, ?, ?, ?, 'administracao')",
            (alvo_id, motivo, agora.isoformat(), agora.isoformat(), admin_id, anonimizar_em.isoformat()),
        )
        conexao.commit()
    finally:
        conexao.close()

    if novo_id:
        criar_notificacao(novo_id, "disciplina", "Novas disciplinas",
                          f"Você assumiu {len(disciplinas)} disciplina(s) de outro professor, com o material e as atividades.",
                          "turmas.html")

    from infra.email import enviar_em_segundo_plano

    data = anonimizar_em.strftime("%d/%m/%Y")
    enviar_em_segundo_plano(
        email_alvo,
        "Delta Care — sua conta foi desativada",
        "A administração da instituição desativou a sua conta no Delta Care.\n\n"
        "Em " + data + " os seus dados pessoais serão anonimizados. "
        "O registro acadêmico (notas, entregas e o material publicado) continua com a instituição, sem identificação.\n\n"
        "Se isso foi um engano, fale com a secretaria acadêmica até essa data.\n",
    )
    rotulo = nome or email_alvo
    return {
        "sucesso": True,
        "mensagem": f"Conta de {rotulo} desativada. Os dados pessoais serão anonimizados em {data}."
                    + (f" {len(disciplinas)} disciplina(s) passaram para o novo professor." if disciplinas else ""),
        "anonimizar_em": anonimizar_em.isoformat(),
    }


def reverter_exclusao(admin_email: str, solicitacao_id: int) -> dict:
    """Dentro do prazo, a conta volta como estava. Depois, não há o que voltar."""
    conexao = conectar()
    admin_id = _eh_admin(conexao, admin_email)
    if not admin_id:
        conexao.close()
        return {"sucesso": False, "mensagem": "Acesso restrito à administração."}

    # Anonimizada, a exclusão já não está 'agendada' (anonimizar_vencidas a
    # conclui): é o status que fecha a volta.
    linha = conexao.execute(
        "SELECT aluno_id FROM solicitacoes_privacidade"
        " WHERE id = ? AND tipo = 'exclusao' AND status = 'agendada'",
        (int(solicitacao_id),),
    ).fetchone()
    if not linha:
        conexao.close()
        return {"sucesso": False, "mensagem": "Não há exclusão em andamento para reverter."}

    agora = _agora().isoformat()
    conexao.execute("UPDATE users SET desativado_em = NULL WHERE id = ?", (linha[0],))
    conexao.execute(
        "UPDATE solicitacoes_privacidade SET status = 'revertida', concluido_em = ? WHERE id = ?",
        (agora, int(solicitacao_id)),
    )
    conexao.commit()
    conexao.close()

    criar_notificacao(linha[0], "privacidade", "Conta reativada",
                      "A exclusão da sua conta foi revertida pela administração.", "meus-dados.html")
    return {"sucesso": True, "mensagem": "Exclusão revertida. A conta voltou a entrar."}


# =========================================================================
# Anonimização
# =========================================================================

def _anonimizar(conexao, aluno_id: int, agora: str) -> None:
    from regras.auditoria import anonimizar_na_trilha

    email_antigo, tipo_conta, nome_antigo = conexao.execute(
        "SELECT email, tipo, nome FROM users WHERE id = ?", (aluno_id,)).fetchone()
    removido = "Professor removido" if tipo_conta == "professor" else "Aluno removido"
    anonimizar_na_trilha(conexao, aluno_id, email_antigo, f"removido-{aluno_id}@anonimo.invalid", nome_antigo or "", removido)

    # Some: é pessoal e não é registro acadêmico.
    for sql in (
        "DELETE FROM sessoes WHERE user_id = ?",
        "DELETE FROM desafios_login WHERE user_id = ?",
        "DELETE FROM notificacoes WHERE user_id = ?",
        "DELETE FROM favoritos WHERE aluno_id = ?",
        # Anotação é caderno particular; nem a administração lê (regras/anotacoes.py).
        "DELETE FROM anotacoes WHERE aluno_id = ?",
        "DELETE FROM chat_mensagens WHERE aluno_id = ?",
        # Conversa com o professor é correspondência pessoal. O que tinha de
        # acadêmico virou entrega, que fica.
        "DELETE FROM mensagens WHERE aluno_id = ?",
    ):
        conexao.execute(sql, (aluno_id,))
    conexao.execute("DELETE FROM tentativas_login WHERE email = ?", (email_antigo,))

    # Os pedidos ficam (provam que a exclusão foi atendida), mas sem o que é
    # pessoal: um pedido de correção de e-mail guardaria o e-mail.
    conexao.execute(
        "UPDATE solicitacoes_privacidade SET valor_novo = NULL, motivo = NULL WHERE aluno_id = ?",
        (aluno_id,),
    )

    # A linha do usuário fica — é ela que segura notas, entregas, matrículas e
    # acessos, que a faculdade precisa guardar. Sem nada que identifique.
    # A senha vira o hash de um segredo descartado: ninguém entra mais.
    conexao.execute(
        "UPDATE users SET nome = ?, email = ?, matricula = NULL,"
        " senha = ?, reset_token = NULL, reset_expira = NULL, disciplinas = NULL,"
        " ranking_oculto = 1, anonimizado_em = ? WHERE id = ?",
        (removido, f"removido-{aluno_id}@anonimo.invalid", hash_senha(secrets.token_hex(32)), agora, aluno_id),
    )


def anonimizar_vencidas(agora: datetime | None = None) -> int:
    """Anonimiza as contas cuja exclusão venceu o prazo. Devolve quantas.

    Roda ao subir o servidor, quando a administração abre a fila de pedidos e
    pelo script `anonimizar_vencidas.py` (agendado no servidor, uma vez por
    dia). Pode rodar quantas vezes for: a que já foi não volta à lista.
    """
    agora = agora or _agora()
    conexao = conectar()
    vencidas = conexao.execute(
        "SELECT id, aluno_id FROM solicitacoes_privacidade"
        " WHERE tipo = 'exclusao' AND status = 'agendada' AND anonimizar_em <= ?",
        (agora.isoformat(),),
    ).fetchall()

    for solicitacao_id, aluno_id in vencidas:
        _anonimizar(conexao, aluno_id, agora.isoformat())
        conexao.execute(
            "UPDATE solicitacoes_privacidade SET status = 'concluida', concluido_em = ? WHERE id = ?",
            (agora.isoformat(), solicitacao_id),
        )
    conexao.commit()
    conexao.close()
    return len(vencidas)
