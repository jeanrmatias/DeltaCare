"""A turma de alunos (coorte) e o espalhamento dela para as disciplinas.

**Vocabulário, porque as duas coisas se chamam "turma" em lugares diferentes:**
uma linha de `turmas` é na prática uma *disciplina* — um professor, um corpo de
material, e o chat de IA busca só dentro dela. A coorte é a turma no sentido que
a instituição usa: MED 3A, o grupo que cursa o semestre junto. Na interface,
`coortes` aparece como "Turma" e `turmas` como "Disciplina".

O que este módulo resolve: matricular um aluno na MED 3A devia matriculá-lo em
Anatomia, Fisiologia, Semiologia e no resto da grade, sem o admin repetir a
operação disciplina por disciplina. E devia permitir a exceção — o aluno que traz
Anatomia aproveitada de outra instituição, ou que reprovou só em Fisiologia e
está cursando o resto do semestre seguinte.

## Por que espalhar em vez de calcular na hora

A alternativa era deixar `matriculas` só para matrícula direta e *derivar* quem
está na disciplina na hora da consulta (coorte menos exceções). Mais elegante, e
descartada por medição: existem 24 consultas diretas a `matriculas` em 9 módulos
— materiais, atividades, desempenho, mensagens, denúncias, notificações. Derivar
exigiria acertar todas as 24, e **cada uma esquecida seria um furo de permissão
silencioso**: aluno lendo material de disciplina que não cursa, ou faltando na
lista de correção do professor.

Então `matriculas` continua sendo a única verdade sobre quem cursa o quê, e a
coorte é a ferramenta que escreve essas linhas. Os 9 módulos seguem intocados.

O preço é sincronismo: espalhar é um evento, não uma consulta. Por isso todo
caminho que muda a composição chama `sincronizar_coorte`, e criar disciplina
dentro de uma coorte também chama. Se um caminho novo esquecer, o sintoma é
aluno de fora da disciplina — visível, ao contrário do inverso.
"""

from datetime import datetime, timezone

from regras.turmas import _eh_admin, buscar_usuario, conectar


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


# =========================================================================
# A coorte em si
# =========================================================================

def criar_coorte(admin_email: str, nome: str, semestre: str) -> dict:
    nome = (nome or "").strip()
    semestre = (semestre or "").strip()

    if not nome:
        return {"sucesso": False, "mensagem": "Informe o nome da turma (ex.: MED 3A)."}
    if not semestre:
        return {"sucesso": False, "mensagem": "Informe o semestre (ex.: 2026/2)."}

    conexao = conectar()

    if not _eh_admin(conexao, admin_email):
        conexao.close()
        return {"sucesso": False, "mensagem": "Só um administrador pode criar turmas."}

    cursor = conexao.cursor()
    cursor.execute("SELECT id FROM coortes WHERE nome = ? AND semestre = ?", (nome, semestre))
    if cursor.fetchone():
        conexao.close()
        return {"sucesso": False, "mensagem": "Já existe uma turma com esse nome nesse semestre."}

    cursor.execute(
        "INSERT INTO coortes (nome, semestre, criado_em) VALUES (?, ?, ?)",
        (nome, semestre, _agora()),
    )
    conexao.commit()
    coorte_id = cursor.lastrowid
    conexao.close()

    return {
        "sucesso": True,
        "mensagem": "Turma criada com sucesso!",
        "coorte": {"id": coorte_id, "nome": nome, "semestre": semestre},
    }


def listar_coortes(admin_email: str) -> dict:
    """As coortes com as contagens que o admin precisa para decidir algo."""
    conexao = conectar()

    if not _eh_admin(conexao, admin_email):
        conexao.close()
        return {"sucesso": False, "mensagem": "Só um administrador pode ver isso.", "coortes": []}

    cursor = conexao.cursor()
    cursor.execute(
        '''
        SELECT c.id, c.nome, c.semestre,
               (SELECT COUNT(*) FROM matriculas_coorte mc WHERE mc.coorte_id = c.id),
               (SELECT COUNT(*) FROM turmas t WHERE t.coorte_id = c.id)
        FROM coortes c
        ORDER BY c.semestre DESC, c.nome
        '''
    )
    coortes = [
        {
            "id": linha[0],
            "nome": linha[1],
            "semestre": linha[2],
            "total_alunos": linha[3],
            "total_disciplinas": linha[4],
        }
        for linha in cursor.fetchall()
    ]
    conexao.close()

    return {"sucesso": True, "coortes": coortes}


def excluir_coorte(admin_email: str, coorte_id: int) -> dict:
    """Desfaz a coorte sem desfazer o semestre do aluno.

    As disciplinas **ficam**, e as matrículas nelas também: o aluno cursou
    Anatomia, tem nota e material lido, e nada disso deixa de ter acontecido
    porque o agrupamento foi desfeito. As disciplinas só perdem o vínculo e
    voltam a ser soltas, como as de antes desta feature.
    """
    conexao = conectar()

    if not _eh_admin(conexao, admin_email):
        conexao.close()
        return {"sucesso": False, "mensagem": "Só um administrador pode excluir turmas."}

    cursor = conexao.cursor()
    cursor.execute("SELECT id FROM coortes WHERE id = ?", (coorte_id,))
    if not cursor.fetchone():
        conexao.close()
        return {"sucesso": False, "mensagem": "Turma não encontrada."}

    # As exceções vão embora: elas só existem em relação a uma coorte, e
    # deixá-las guardaria uma regra que ninguém mais aplica.
    cursor.execute(
        "DELETE FROM excecoes_coorte WHERE turma_id IN (SELECT id FROM turmas WHERE coorte_id = ?)",
        (coorte_id,),
    )
    cursor.execute("DELETE FROM matriculas_coorte WHERE coorte_id = ?", (coorte_id,))
    cursor.execute("UPDATE turmas SET coorte_id = NULL WHERE coorte_id = ?", (coorte_id,))
    cursor.execute("DELETE FROM coortes WHERE id = ?", (coorte_id,))
    conexao.commit()
    conexao.close()

    return {"sucesso": True, "mensagem": "Turma desfeita. As disciplinas e as notas continuam."}


# =========================================================================
# Espalhamento
# =========================================================================

def _disciplinas_da_coorte(cursor, coorte_id: int) -> list:
    cursor.execute("SELECT id FROM turmas WHERE coorte_id = ?", (int(coorte_id),))
    return [linha[0] for linha in cursor.fetchall()]


def _alunos_da_coorte(cursor, coorte_id: int) -> list:
    cursor.execute("SELECT aluno_id FROM matriculas_coorte WHERE coorte_id = ?", (int(coorte_id),))
    return [linha[0] for linha in cursor.fetchall()]


def _sincronizar(cursor, coorte_id: int) -> dict:
    """Faz `matriculas` refletir (alunos da coorte × disciplinas) − exceções.

    Idempotente de propósito: é chamada de cinco caminhos diferentes, e uma
    delas ser executada duas vezes não pode mudar o resultado.

    Só mexe nas disciplinas **desta** coorte. Matrícula direta feita à mão em
    disciplina solta não é da conta daqui, e apagar o que o admin fez na mão
    seria o tipo de efeito que ninguém liga à causa.
    """
    disciplinas = _disciplinas_da_coorte(cursor, coorte_id)
    if not disciplinas:
        return {"matriculados": 0, "removidos": 0}

    alunos = set(_alunos_da_coorte(cursor, coorte_id))
    marcadores = ",".join("?" for _ in disciplinas)

    cursor.execute(
        f"SELECT aluno_id, turma_id FROM excecoes_coorte WHERE turma_id IN ({marcadores})",
        disciplinas,
    )
    excecoes = set(cursor.fetchall())

    cursor.execute(
        f"SELECT aluno_id, turma_id FROM matriculas WHERE turma_id IN ({marcadores})",
        disciplinas,
    )
    existentes = set(cursor.fetchall())

    desejadas = {
        (aluno_id, turma_id)
        for aluno_id in alunos
        for turma_id in disciplinas
        if (aluno_id, turma_id) not in excecoes
    }

    agora = _agora()
    faltando = desejadas - existentes
    for aluno_id, turma_id in faltando:
        cursor.execute(
            "INSERT INTO matriculas (aluno_id, turma_id, criado_em) VALUES (?, ?, ?)",
            (aluno_id, turma_id, agora),
        )

    # Sobrando = aluno que saiu da coorte, ou que virou exceção. Some da
    # disciplina na hora: continuar vendo o material seria o furo que esta
    # feature existe para fechar.
    sobrando = existentes - desejadas
    for aluno_id, turma_id in sobrando:
        cursor.execute(
            "DELETE FROM matriculas WHERE aluno_id = ? AND turma_id = ?",
            (aluno_id, turma_id),
        )

    return {"matriculados": len(faltando), "removidos": len(sobrando)}


def sincronizar_coorte(coorte_id: int) -> dict:
    """Ponto de entrada para quem já fechou a própria transação."""
    conexao = conectar()
    cursor = conexao.cursor()
    resultado = _sincronizar(cursor, coorte_id)
    conexao.commit()
    conexao.close()
    return resultado


def sincronizar_disciplina(turma_id: int) -> dict:
    """Chamada quando uma disciplina é criada ou movida para uma coorte.

    Sem isto, a disciplina criada depois do aluno entrar na coorte nasceria
    vazia, e o admin teria que matricular a turma inteira na mão — exatamente o
    trabalho que a coorte existe para tirar.
    """
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("SELECT coorte_id FROM turmas WHERE id = ?", (int(turma_id),))
    linha = cursor.fetchone()

    if not linha or not linha[0]:
        conexao.close()
        return {"matriculados": 0, "removidos": 0}

    resultado = _sincronizar(cursor, linha[0])
    conexao.commit()
    conexao.close()
    return resultado


# =========================================================================
# Alunos na coorte
# =========================================================================

def matricular_na_coorte(admin_email: str, aluno_email: str, coorte_id: int) -> dict:
    conexao = conectar()

    if not _eh_admin(conexao, admin_email):
        conexao.close()
        return {"sucesso": False, "mensagem": "Só um administrador pode matricular aluno."}

    aluno = buscar_usuario(conexao, aluno_email)
    if not aluno or aluno[1] != "aluno":
        conexao.close()
        return {"sucesso": False, "mensagem": "Aluno não encontrado."}

    cursor = conexao.cursor()
    cursor.execute("SELECT id FROM coortes WHERE id = ?", (coorte_id,))
    if not cursor.fetchone():
        conexao.close()
        return {"sucesso": False, "mensagem": "Turma não encontrada."}

    cursor.execute(
        "SELECT id FROM matriculas_coorte WHERE aluno_id = ? AND coorte_id = ?",
        (aluno[0], coorte_id),
    )
    if cursor.fetchone():
        conexao.close()
        return {"sucesso": False, "mensagem": "Esse aluno já está nessa turma."}

    cursor.execute(
        "INSERT INTO matriculas_coorte (aluno_id, coorte_id, criado_em) VALUES (?, ?, ?)",
        (aluno[0], coorte_id, _agora()),
    )
    resultado = _sincronizar(cursor, coorte_id)
    conexao.commit()
    conexao.close()

    quantas = resultado["matriculados"]
    if quantas == 0:
        detalhe = "Essa turma ainda não tem disciplinas."
    elif quantas == 1:
        detalhe = "Matriculado em 1 disciplina."
    else:
        detalhe = f"Matriculado em {quantas} disciplinas."

    return {"sucesso": True, "mensagem": f"Aluno adicionado à turma. {detalhe}", **resultado}


def remover_da_coorte(admin_email: str, aluno_email: str, coorte_id: int) -> dict:
    """Tira o aluno da coorte e das disciplinas dela.

    As exceções dele nessas disciplinas vão embora junto: elas descrevem "está
    na coorte, mas fora desta disciplina", e fora da coorte a frase não quer
    dizer nada. Guardá-las faria uma rematrícula futura herdar em silêncio uma
    decisão de outro semestre.
    """
    conexao = conectar()

    if not _eh_admin(conexao, admin_email):
        conexao.close()
        return {"sucesso": False, "mensagem": "Só um administrador pode remover aluno."}

    aluno = buscar_usuario(conexao, aluno_email)
    if not aluno:
        conexao.close()
        return {"sucesso": False, "mensagem": "Aluno não encontrado."}

    cursor = conexao.cursor()
    cursor.execute(
        "DELETE FROM matriculas_coorte WHERE aluno_id = ? AND coorte_id = ?",
        (aluno[0], coorte_id),
    )
    cursor.execute(
        '''
        DELETE FROM excecoes_coorte
        WHERE aluno_id = ?
          AND turma_id IN (SELECT id FROM turmas WHERE coorte_id = ?)
        ''',
        (aluno[0], coorte_id),
    )
    resultado = _sincronizar(cursor, coorte_id)
    conexao.commit()
    conexao.close()

    return {"sucesso": True, "mensagem": "Aluno removido da turma e das disciplinas dela.", **resultado}


def listar_alunos_da_coorte(admin_email: str, coorte_id: int) -> dict:
    """Os alunos da coorte, cada um com as disciplinas de que está fora.

    Devolve a exceção junto porque é onde o admin decide: a tela precisa marcar
    quem está fora de quê sem uma chamada por aluno.
    """
    conexao = conectar()

    if not _eh_admin(conexao, admin_email):
        conexao.close()
        return {"sucesso": False, "mensagem": "Só um administrador pode ver isso.", "alunos": []}

    cursor = conexao.cursor()
    cursor.execute(
        '''
        SELECT u.id, u.email, u.nome
        FROM matriculas_coorte mc
        JOIN users u ON u.id = mc.aluno_id
        WHERE mc.coorte_id = ?
        ORDER BY COALESCE(u.nome, u.email)
        ''',
        (int(coorte_id),),
    )
    linhas = cursor.fetchall()

    cursor.execute(
        '''
        SELECT e.aluno_id, e.turma_id, t.nome
        FROM excecoes_coorte e
        JOIN turmas t ON t.id = e.turma_id
        WHERE t.coorte_id = ?
        ''',
        (int(coorte_id),),
    )
    fora = {}
    for aluno_id, turma_id, nome_disciplina in cursor.fetchall():
        fora.setdefault(aluno_id, []).append({"turma_id": turma_id, "nome": nome_disciplina})

    conexao.close()

    alunos = [
        {
            "email": linha[1],
            "nome": linha[2] or linha[1],
            "fora_de": fora.get(linha[0], []),
        }
        for linha in linhas
    ]

    return {"sucesso": True, "alunos": alunos}


def listar_disciplinas_da_coorte(admin_email: str, coorte_id: int) -> dict:
    conexao = conectar()

    if not _eh_admin(conexao, admin_email):
        conexao.close()
        return {"sucesso": False, "mensagem": "Só um administrador pode ver isso.", "disciplinas": []}

    cursor = conexao.cursor()
    cursor.execute(
        '''
        SELECT t.id, t.nome, t.semestre, u.nome, u.email,
               (SELECT COUNT(*) FROM matriculas m WHERE m.turma_id = t.id)
        FROM turmas t
        JOIN users u ON u.id = t.professor_id
        WHERE t.coorte_id = ?
        ORDER BY t.nome
        ''',
        (int(coorte_id),),
    )
    disciplinas = [
        {
            "id": linha[0],
            "nome": linha[1],
            "semestre": linha[2],
            "professor_nome": linha[3] or linha[4],
            "total_alunos": linha[5],
        }
        for linha in cursor.fetchall()
    ]
    conexao.close()

    return {"sucesso": True, "disciplinas": disciplinas}


# =========================================================================
# Exceções
# =========================================================================

def criar_excecao(admin_email: str, aluno_email: str, turma_id: int) -> dict:
    """Tira da disciplina um aluno que continua na coorte."""
    conexao = conectar()

    if not _eh_admin(conexao, admin_email):
        conexao.close()
        return {"sucesso": False, "mensagem": "Só um administrador pode fazer isso."}

    aluno = buscar_usuario(conexao, aluno_email)
    if not aluno or aluno[1] != "aluno":
        conexao.close()
        return {"sucesso": False, "mensagem": "Aluno não encontrado."}

    cursor = conexao.cursor()
    cursor.execute("SELECT coorte_id, nome FROM turmas WHERE id = ?", (int(turma_id),))
    disciplina = cursor.fetchone()

    if not disciplina:
        conexao.close()
        return {"sucesso": False, "mensagem": "Disciplina não encontrada."}

    # Exceção só faz sentido contra um espalhamento. Numa disciplina solta, o
    # admin desmatricula e pronto — inventar uma exceção ali criaria duas
    # formas de dizer a mesma coisa, e nenhuma delas confiável.
    if not disciplina[0]:
        conexao.close()
        return {
            "sucesso": False,
            "mensagem": "Essa disciplina não pertence a nenhuma turma. Desmatricule o aluno direto nela.",
        }

    cursor.execute(
        "SELECT id FROM matriculas_coorte WHERE aluno_id = ? AND coorte_id = ?",
        (aluno[0], disciplina[0]),
    )
    if not cursor.fetchone():
        conexao.close()
        return {"sucesso": False, "mensagem": "Esse aluno não está na turma dessa disciplina."}

    cursor.execute(
        "SELECT id FROM excecoes_coorte WHERE aluno_id = ? AND turma_id = ?",
        (aluno[0], turma_id),
    )
    if cursor.fetchone():
        conexao.close()
        return {"sucesso": False, "mensagem": "Esse aluno já está fora dessa disciplina."}

    cursor.execute(
        "INSERT INTO excecoes_coorte (aluno_id, turma_id, criado_em) VALUES (?, ?, ?)",
        (aluno[0], turma_id, _agora()),
    )
    resultado = _sincronizar(cursor, disciplina[0])
    conexao.commit()
    conexao.close()

    return {
        "sucesso": True,
        "mensagem": f"Aluno está fora de {disciplina[1]}, e continua na turma.",
        **resultado,
    }


def remover_excecao(admin_email: str, aluno_email: str, turma_id: int) -> dict:
    """Desfaz a exceção: o aluno volta a cursar a disciplina."""
    conexao = conectar()

    if not _eh_admin(conexao, admin_email):
        conexao.close()
        return {"sucesso": False, "mensagem": "Só um administrador pode fazer isso."}

    aluno = buscar_usuario(conexao, aluno_email)
    if not aluno:
        conexao.close()
        return {"sucesso": False, "mensagem": "Aluno não encontrado."}

    cursor = conexao.cursor()
    cursor.execute("SELECT coorte_id, nome FROM turmas WHERE id = ?", (int(turma_id),))
    disciplina = cursor.fetchone()

    if not disciplina:
        conexao.close()
        return {"sucesso": False, "mensagem": "Disciplina não encontrada."}

    cursor.execute(
        "DELETE FROM excecoes_coorte WHERE aluno_id = ? AND turma_id = ?",
        (aluno[0], turma_id),
    )
    if cursor.rowcount == 0:
        conexao.close()
        return {"sucesso": False, "mensagem": "Esse aluno não estava fora dessa disciplina."}

    resultado = {"matriculados": 0, "removidos": 0}
    if disciplina[0]:
        resultado = _sincronizar(cursor, disciplina[0])

    conexao.commit()
    conexao.close()

    return {"sucesso": True, "mensagem": f"Aluno voltou a cursar {disciplina[1]}.", **resultado}
