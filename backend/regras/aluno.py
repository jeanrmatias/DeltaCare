"""Visão do aluno: materiais liberados e resumo da tela inicial.

Separado de regras/materiais.py de propósito. Lá, toda consulta parte do
professor dono do material (`professor_id = ?`), e o professor enxerga também
rascunho e material agendado. O aluno tem outra regra, mais restritiva:

1. só vê turma em que está matriculado;
2. dentro dela, só vê material já publicado — nunca rascunho, nunca agendado
   para uma data futura.

Misturar as duas visões na mesma função convidaria a um erro de filtro que
vazaria material não liberado. Aqui a regra do aluno fica isolada e explícita.
"""

from datetime import datetime, timedelta, timezone

from regras.turmas import buscar_usuario, conectar


def _esta_publicado(rascunho: int, data_liberacao) -> bool:
    """Mesma regra de regras/materiais._calcular_status, na forma de sim/não.

    Reaplicada aqui para não criar import cruzado (logica_materiais já importa
    de logica_turmas). Se a regra mudar, os três pontos precisam mudar juntos —
    o outro é regras/chat_ia._status_material.
    """
    if rascunho:
        return False

    if data_liberacao:
        try:
            liberacao = datetime.fromisoformat(data_liberacao)
            if liberacao.tzinfo is None:
                liberacao = liberacao.replace(tzinfo=timezone.utc)
            if liberacao > datetime.now(timezone.utc):
                return False
        except ValueError:
            # Data inválida no banco: tratamos como publicado, que é o
            # comportamento já adotado em logica_materiais.
            pass

    return True


def _buscar_aluno(conexao, aluno_email: str):
    aluno = buscar_usuario(conexao, aluno_email)
    if not aluno or aluno[1] != "aluno":
        return None
    return aluno


def listar_materiais_do_aluno(aluno_email: str, turma_id: int | None = None) -> dict:
    """Materiais publicados das turmas em que o aluno está matriculado.

    Com `turma_id`, restringe a uma turma — e só devolve algo se o aluno
    estiver matriculado nela.
    """
    conexao = conectar()
    aluno = _buscar_aluno(conexao, aluno_email)

    if not aluno:
        conexao.close()
        return {"sucesso": False, "mensagem": "Aluno não encontrado.", "materiais": []}

    consulta = '''
        SELECT m.id, m.titulo, m.descricao, m.tipo, m.link_url, m.arquivo_nome,
               m.assunto, m.topico, m.aula, m.semestre, m.rascunho,
               m.data_liberacao, m.criado_em, m.turma_id, t.nome, u.email
        FROM materiais m
        JOIN turmas t ON t.id = m.turma_id
        JOIN matriculas mt ON mt.turma_id = m.turma_id
        LEFT JOIN users u ON u.id = m.professor_id
        WHERE mt.aluno_id = ?
    '''
    parametros = [aluno[0]]

    if turma_id is not None:
        consulta += " AND m.turma_id = ?"
        parametros.append(turma_id)

    consulta += " ORDER BY m.criado_em DESC"

    cursor = conexao.cursor()
    cursor.execute(consulta, parametros)
    linhas = cursor.fetchall()
    conexao.close()

    materiais = []
    for linha in linhas:
        (id_, titulo, descricao, tipo, link_url, arquivo_nome, assunto, topico,
         aula, semestre, rascunho, data_liberacao, criado_em, turma, turma_nome,
         professor_email) = linha

        # O filtro acontece aqui, e não no SQL, porque "publicado" depende da
        # hora atual (material agendado vira publicado sozinho).
        if not _esta_publicado(rascunho, data_liberacao):
            continue

        materiais.append({
            "id": id_,
            "titulo": titulo,
            "descricao": descricao,
            "tipo": tipo,
            "link_url": link_url,
            "arquivo_nome": arquivo_nome,
            "assunto": assunto,
            "topico": topico,
            "aula": aula,
            "semestre": semestre,
            "criado_em": criado_em,
            "turma_id": turma,
            "turma_nome": turma_nome,
            "professor_email": professor_email,
        })

    return {"sucesso": True, "materiais": materiais}


def obter_arquivo_material_do_aluno(aluno_email: str, material_id: int):
    """(caminho_no_disco, nome_original) se o aluno pode baixar o material.

    Devolve None quando o aluno não está matriculado na turma do material, o
    material não está publicado, ou não há arquivo — de fora, todos esses casos
    são iguais, para não revelar a existência de material que ele não pode ver.
    """
    conexao = conectar()
    aluno = _buscar_aluno(conexao, aluno_email)

    if not aluno:
        conexao.close()
        return None

    cursor = conexao.cursor()
    cursor.execute(
        '''
        SELECT m.arquivo_caminho, m.arquivo_nome, m.rascunho, m.data_liberacao
        FROM materiais m
        JOIN matriculas mt ON mt.turma_id = m.turma_id
        WHERE m.id = ? AND mt.aluno_id = ?
        ''',
        (material_id, aluno[0]),
    )
    linha = cursor.fetchone()
    conexao.close()

    if not linha:
        return None

    caminho, nome_original, rascunho, data_liberacao = linha

    if not caminho or not _esta_publicado(rascunho, data_liberacao):
        return None

    return caminho, nome_original


# Quanto vale cada ação no XP. Os pesos são pequenos e explicados na tela: um
# número de "pontos" que o aluno não sabe de onde vem não engaja, irrita.
XP_POR_PERGUNTA = 10
XP_POR_MATERIAL_ACESSADO = 15
XP_POR_DIA_ATIVO = 25

# Quantos XP cada nível exige. Progressão linear de propósito: o módulo de
# Atividades ainda não existe, e uma curva elaborada agora seria calibrada
# sobre metade dos dados que o sistema vai ter depois.
XP_POR_NIVEL = 150

DIAS_ACOMPANHAMENTO = 14


def registrar_acesso_material(aluno_email: str, material_id: int) -> None:
    """Anota que o aluno abriu um material.

    Silencioso de propósito: uma falha ao registrar estatística não pode
    impedir o download que o aluno pediu.
    """
    try:
        conexao = conectar()
        aluno = _buscar_aluno(conexao, aluno_email)

        if aluno:
            conexao.execute(
                "INSERT INTO acessos_material (aluno_id, material_id, criado_em) VALUES (?, ?, ?)",
                (aluno[0], material_id, datetime.now(timezone.utc).isoformat()),
            )
            conexao.commit()

        conexao.close()
    except Exception:
        pass


def _dias_com_atividade(cursor, aluno_id: int) -> set:
    """Dias (AAAA-MM-DD) em que o aluno perguntou ou abriu material."""
    consulta = (
        "SELECT DISTINCT substr(criado_em, 1, 10) FROM chat_mensagens "
        "WHERE aluno_id = ? AND papel = 'user' "
        "UNION "
        "SELECT DISTINCT substr(criado_em, 1, 10) FROM acessos_material "
        "WHERE aluno_id = ?"
    )
    return {linha[0] for linha in cursor.execute(consulta, (aluno_id, aluno_id)).fetchall()}


def _calcular_progresso(aluno_id: int) -> dict:
    """XP e frequência de estudo, a partir do que o sistema registrou de fato.

    Nada aqui é estimado: perguntas vêm de `chat_mensagens` e materiais
    consultados de `acessos_material`. Quando o módulo de Atividades existir,
    entrega e nota entram nesta mesma conta.
    """
    conexao = conectar()
    cursor = conexao.cursor()

    perguntas = cursor.execute(
        "SELECT COUNT(*) FROM chat_mensagens WHERE aluno_id = ? AND papel = 'user'",
        (aluno_id,),
    ).fetchone()[0]

    # DISTINCT: reabrir o mesmo PDF cinco vezes não são cinco materiais
    # estudados.
    materiais_acessados = cursor.execute(
        "SELECT COUNT(DISTINCT material_id) FROM acessos_material WHERE aluno_id = ?",
        (aluno_id,),
    ).fetchone()[0]

    dias_ativos = _dias_com_atividade(cursor, aluno_id)
    conexao.close()

    xp = (
        perguntas * XP_POR_PERGUNTA
        + materiais_acessados * XP_POR_MATERIAL_ACESSADO
        + len(dias_ativos) * XP_POR_DIA_ATIVO
    )

    hoje = datetime.now(timezone.utc).date()

    # Últimos dias para o gráfico, do mais antigo para o mais recente.
    acompanhamento = []
    for recuo in range(DIAS_ACOMPANHAMENTO - 1, -1, -1):
        dia = hoje - timedelta(days=recuo)
        acompanhamento.append({"dia": dia.isoformat(), "ativo": dia.isoformat() in dias_ativos})

    # Sequência de dias consecutivos. Começa de ontem quando hoje ainda não
    # teve atividade, senão a sequência zeraria toda manhã.
    sequencia = 0
    referencia = hoje if hoje.isoformat() in dias_ativos else hoje - timedelta(days=1)

    while referencia.isoformat() in dias_ativos:
        sequencia += 1
        referencia -= timedelta(days=1)

    return {
        "xp": xp,
        "nivel": 1 + xp // XP_POR_NIVEL,
        "xp_no_nivel": xp % XP_POR_NIVEL,
        "xp_para_proximo_nivel": XP_POR_NIVEL,
        "perguntas": perguntas,
        "materiais_acessados": materiais_acessados,
        "dias_ativos": len(dias_ativos),
        "sequencia": sequencia,
        "acompanhamento": acompanhamento,
        # A composição vai para a tela: o aluno consegue ver de onde veio cada
        # ponto, em vez de receber um total sem explicação.
        "composicao": [
            {
                "rotulo": "Perguntas ao assistente",
                "quantidade": perguntas,
                "xp": perguntas * XP_POR_PERGUNTA,
            },
            {
                "rotulo": "Materiais consultados",
                "quantidade": materiais_acessados,
                "xp": materiais_acessados * XP_POR_MATERIAL_ACESSADO,
            },
            {
                "rotulo": "Dias de estudo",
                "quantidade": len(dias_ativos),
                "xp": len(dias_ativos) * XP_POR_DIA_ATIVO,
            },
        ],
    }


def resumo_do_aluno(aluno_email: str) -> dict:
    """Números e destaques da tela inicial do aluno.

    Tudo vem do banco: nada nesta tela é exemplo fixo.
    """
    from regras.matriculas import listar_turmas_do_aluno

    conexao = conectar()
    aluno = _buscar_aluno(conexao, aluno_email)

    if not aluno:
        conexao.close()
        return {"sucesso": False, "mensagem": "Aluno não encontrado."}

    aluno_id = aluno[0]

    cursor = conexao.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM chat_mensagens WHERE aluno_id = ? AND papel = 'user'",
        (aluno_id,),
    )
    perguntas_feitas = cursor.fetchone()[0]
    conexao.close()

    turmas = listar_turmas_do_aluno(aluno_email).get("turmas", [])
    materiais = listar_materiais_do_aluno(aluno_email).get("materiais", [])

    # Quantos materiais por turma, para os cartões da tela inicial.
    por_turma = {}
    for material in materiais:
        por_turma[material["turma_id"]] = por_turma.get(material["turma_id"], 0) + 1

    for turma in turmas:
        turma["total_materiais"] = por_turma.get(turma["id"], 0)

    return {
        "sucesso": True,
        "total_turmas": len(turmas),
        "total_materiais": len(materiais),
        "perguntas_feitas": perguntas_feitas,
        "turmas": turmas,
        "materiais_recentes": materiais[:5],
        "progresso": _calcular_progresso(aluno_id),
    }
