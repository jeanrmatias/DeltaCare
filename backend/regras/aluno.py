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

from datetime import datetime, timezone

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
    }
