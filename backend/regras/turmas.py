"""Regras de negócio de turmas. Sem depender do FastAPI (testável sozinho).

Quem cria, edita e exclui turmas é o administrador (US-07.xx do backlog —
governança da plataforma). O professor só enxerga as turmas que foram
atribuídas a ele; ele não cria nem edita turma, só publica/edita os
materiais dentro delas.
"""

import sqlite3
from datetime import datetime, timezone

from infra.database import CAMINHO_DB as DB_PATH
from infra.database import abrir_conexao


def conectar():
    return abrir_conexao()


def buscar_usuario(conexao, email: str):
    """Retorna (id, tipo) do usuário pelo e-mail, ou None."""
    cursor = conexao.cursor()
    cursor.execute("SELECT id, tipo FROM users WHERE email = ?", (email.strip().lower(),))
    return cursor.fetchone()


def buscar_professor(conexao, email: str):
    """Mantido por compatibilidade: busca um usuário do tipo 'professor'."""
    usuario = buscar_usuario(conexao, email)
    if usuario and usuario[1] == "professor":
        return usuario
    return None


def _eh_admin(conexao, email: str) -> bool:
    usuario = buscar_usuario(conexao, email)
    return bool(usuario and usuario[1] == "adm")


def criar_turma(
    admin_email: str,
    professor_email: str,
    nome: str,
    semestre: str,
    coorte_id: int | None = None,
) -> dict:
    """Cria uma disciplina (ver a nota de vocabulário em regras/coortes.py).

    `coorte_id` é opcional e vai continuar opcional: disciplina solta é caso
    legítimo — optativa, extensão, ou o admin que prefere matricular na mão.
    Passando a coorte, os alunos dela já entram matriculados, menos os que
    tiverem exceção registrada.
    """
    nome = nome.strip()
    semestre = semestre.strip()

    if not nome:
        return {"sucesso": False, "mensagem": "Informe o nome da turma."}
    if not semestre:
        return {"sucesso": False, "mensagem": "Informe o semestre (ex.: 2026/2)."}

    # Um formato só (ver regras/semestres.py): `2026.2` e `2026/2` eram
    # semestres diferentes para o sistema, e a disciplina sumiria da frente do
    # aluno por causa de um ponto.
    from regras.semestres import normalizar_semestre

    semestre_normalizado = normalizar_semestre(semestre)
    if not semestre_normalizado:
        return {"sucesso": False, "mensagem": "Semestre inválido. Use o formato 2026/2."}
    semestre = semestre_normalizado

    conexao = conectar()

    if not _eh_admin(conexao, admin_email):
        conexao.close()
        return {"sucesso": False, "mensagem": "Só um administrador pode criar turmas."}

    professor = buscar_usuario(conexao, professor_email)
    if not professor or professor[1] != "professor":
        conexao.close()
        return {"sucesso": False, "mensagem": "Professor não encontrado."}

    professor_id = professor[0]
    cursor = conexao.cursor()

    cursor.execute(
        "SELECT id FROM turmas WHERE professor_id = ? AND nome = ? AND semestre = ?",
        (professor_id, nome, semestre),
    )
    if cursor.fetchone():
        conexao.close()
        return {"sucesso": False, "mensagem": "Esse professor já tem uma turma com esse nome nesse semestre."}

    if coorte_id is not None:
        cursor.execute("SELECT id FROM coortes WHERE id = ?", (int(coorte_id),))
        if not cursor.fetchone():
            conexao.close()
            return {"sucesso": False, "mensagem": "Turma de alunos não encontrada."}

    agora = datetime.now(timezone.utc).isoformat()
    cursor.execute(
        "INSERT INTO turmas (nome, semestre, professor_id, criado_em, coorte_id) VALUES (?, ?, ?, ?, ?)",
        (nome, semestre, professor_id, agora, int(coorte_id) if coorte_id is not None else None),
    )
    conexao.commit()
    turma_id = cursor.lastrowid
    conexao.close()

    matriculados = 0
    if coorte_id is not None:
        # Import aqui dentro para evitar ciclo: coortes importa deste módulo.
        from regras.coortes import sincronizar_disciplina

        # A disciplina nasce com a turma dentro dela. Sem isto, ela nasceria
        # vazia e o admin teria que matricular todo mundo na mão — justamente
        # o trabalho que a coorte existe para tirar.
        matriculados = sincronizar_disciplina(turma_id)["matriculados"]

    mensagem = "Turma criada com sucesso!"
    if matriculados == 1:
        mensagem = "Disciplina criada com 1 aluno da turma."
    elif matriculados > 1:
        mensagem = f"Disciplina criada com {matriculados} alunos da turma."

    return {
        "sucesso": True,
        "mensagem": mensagem,
        "turma": {
            "id": turma_id,
            "nome": nome,
            "semestre": semestre,
            "professor_email": professor_email,
            "coorte_id": int(coorte_id) if coorte_id is not None else None,
        },
    }


def excluir_turma(admin_email: str, turma_id: int) -> dict:
    conexao = conectar()

    if not _eh_admin(conexao, admin_email):
        conexao.close()
        return {"sucesso": False, "mensagem": "Só um administrador pode excluir turmas."}

    cursor = conexao.cursor()
    cursor.execute("SELECT id FROM turmas WHERE id = ?", (turma_id,))
    if not cursor.fetchone():
        conexao.close()
        return {"sucesso": False, "mensagem": "Turma não encontrada."}

    # Tudo que depende da disciplina sai junto, **filhos antes dos pais**. A
    # ordem não é estilo: o banco cobra chave estrangeira (infra/database.py),
    # e apagar a turma com uma atividade ainda apontando para ela falha.
    #
    # Antes da cobrança, esta função apagava só material, chat e matrícula, e
    # deixava atividades, entregas, mensagens e exceções órfãs em silêncio.
    # Ligada a cobrança, passou a falhar em qualquer disciplina que já tivesse
    # sido usada — os testes não viam porque excluíam disciplinas vazias.
    subconsulta_materiais = "SELECT id FROM materiais WHERE turma_id = ?"
    subconsulta_atividades = "SELECT id FROM atividades WHERE turma_id = ?"

    # Arquivos no disco: lidos antes de apagar as linhas que dizem onde estão.
    arquivos_de_material = [
        linha[0] for linha in cursor.execute(
            "SELECT arquivo_caminho FROM materiais WHERE turma_id = ? AND arquivo_caminho IS NOT NULL",
            (turma_id,),
        ).fetchall()
    ]
    arquivos_de_entrega = [
        linha[0] for linha in cursor.execute(
            f"SELECT arquivo_caminho FROM entregas WHERE atividade_id IN ({subconsulta_atividades})"
            " AND arquivo_caminho IS NOT NULL",
            (turma_id,),
        ).fetchall()
    ]

    for sql in (
        f"DELETE FROM acessos_material WHERE material_id IN ({subconsulta_materiais})",
        f"DELETE FROM material_chunks WHERE material_id IN ({subconsulta_materiais})",
        "DELETE FROM materiais WHERE turma_id = ?",
        f"DELETE FROM questoes WHERE atividade_id IN ({subconsulta_atividades})",
        f"DELETE FROM entregas WHERE atividade_id IN ({subconsulta_atividades})",
        "DELETE FROM atividades WHERE turma_id = ?",
        "DELETE FROM mensagens WHERE turma_id = ?",
        "DELETE FROM chat_mensagens WHERE turma_id = ?",
        "DELETE FROM excecoes_coorte WHERE turma_id = ?",
        "DELETE FROM matriculas WHERE turma_id = ?",
        "DELETE FROM turmas WHERE id = ?",
    ):
        cursor.execute(sql, (turma_id,))

    conexao.commit()

    # O arquivo de material pode estar compartilhado com o mesmo material
    # publicado em outra disciplina (ver criar_material_em_turmas): só sai do
    # disco se nenhum outro registro aponta para ele.
    em_uso = {
        linha[0] for linha in cursor.execute(
            "SELECT DISTINCT arquivo_caminho FROM materiais WHERE arquivo_caminho IS NOT NULL"
        ).fetchall()
    }
    conexao.close()

    from infra.arquivos import remover_arquivo

    for caminho in set(arquivos_de_material) - em_uso:
        remover_arquivo(caminho)
    for caminho in arquivos_de_entrega:
        remover_arquivo(caminho)

    return {"sucesso": True, "mensagem": "Turma excluída."}


def listar_turmas(professor_email: str) -> dict:
    """Turmas do próprio professor (visão dele, só leitura)."""
    conexao = conectar()
    professor = buscar_usuario(conexao, professor_email)

    if not professor or professor[1] != "professor":
        conexao.close()
        return {"sucesso": False, "mensagem": "Professor não encontrado.", "turmas": []}

    cursor = conexao.cursor()
    cursor.execute(
        '''
        SELECT t.id, t.nome, t.semestre, t.criado_em,
               (SELECT COUNT(*) FROM materiais m WHERE m.turma_id = t.id AND m.rascunho = 0),
               (SELECT COUNT(*) FROM matriculas mt WHERE mt.turma_id = t.id)
        FROM turmas t
        WHERE t.professor_id = ?
        ORDER BY t.criado_em DESC
        ''',
        (professor[0],),
    )
    linhas = cursor.fetchall()
    conexao.close()

    turmas = [
        {
            "id": linha[0],
            "nome": linha[1],
            "semestre": linha[2],
            "criado_em": linha[3],
            "materiais_publicados": linha[4],
            "total_alunos": linha[5],
        }
        for linha in linhas
    ]

    return {"sucesso": True, "turmas": turmas}


def listar_turmas_admin(admin_email: str) -> dict:
    """Todas as turmas da plataforma, com o professor responsável (visão do admin)."""
    conexao = conectar()

    if not _eh_admin(conexao, admin_email):
        conexao.close()
        return {"sucesso": False, "mensagem": "Só um administrador pode ver isso.", "turmas": []}

    cursor = conexao.cursor()
    cursor.execute(
        '''
        SELECT t.id, t.nome, t.semestre, t.criado_em, u.email,
               (SELECT COUNT(*) FROM materiais m WHERE m.turma_id = t.id)
        FROM turmas t
        JOIN users u ON u.id = t.professor_id
        ORDER BY t.criado_em DESC
        '''
    )
    linhas = cursor.fetchall()
    conexao.close()

    turmas = [
        {
            "id": linha[0],
            "nome": linha[1],
            "semestre": linha[2],
            "criado_em": linha[3],
            "professor_email": linha[4],
            "total_materiais": linha[5],
        }
        for linha in linhas
    ]

    return {"sucesso": True, "turmas": turmas}


def listar_professores(admin_email: str) -> dict:
    conexao = conectar()

    if not _eh_admin(conexao, admin_email):
        conexao.close()
        return {"sucesso": False, "mensagem": "Só um administrador pode ver isso.", "professores": []}

    cursor = conexao.cursor()
    cursor.execute("SELECT email FROM users WHERE tipo = 'professor' ORDER BY email")
    professores = [linha[0] for linha in cursor.fetchall()]
    conexao.close()

    return {"sucesso": True, "professores": professores}


def listar_usuarios(admin_email: str) -> dict:
    """Todos os usuários do sistema, para a tela de gestão do admin.

    Traz junto o que cada conta tem vinculado (turmas para professor,
    matrículas para aluno), porque é isso que o admin precisa saber antes de
    mexer numa conta — e é o que impede exclusões às cegas.
    """
    conexao = conectar()

    if not _eh_admin(conexao, admin_email):
        conexao.close()
        return {"sucesso": False, "mensagem": "Só um administrador pode ver isso.", "usuarios": []}

    cursor = conexao.cursor()
    cursor.execute(
        '''
        SELECT u.id, u.email, u.tipo, u.nome, u.disciplinas, u.matricula,
               (SELECT COUNT(*) FROM turmas t WHERE t.professor_id = u.id),
               (SELECT COUNT(*) FROM matriculas m WHERE m.aluno_id = u.id)
        FROM users u
        ORDER BY
            CASE u.tipo WHEN 'adm' THEN 1 WHEN 'professor' THEN 2 ELSE 3 END,
            u.email
        '''
    )
    linhas = cursor.fetchall()
    conexao.close()

    usuarios = [
        {
            "id": linha[0],
            "email": linha[1],
            "tipo": linha[2],
            "nome": linha[3] or "",
            "disciplinas": linha[4] or "",
            "matricula": linha[5] or "",
            "total_turmas": linha[6],
            "total_matriculas": linha[7],
        }
        for linha in linhas
    ]

    return {"sucesso": True, "usuarios": usuarios}


def perfil_do_usuario(email: str) -> dict:
    """Dados da própria conta, para a tela de perfil.

    Só leitura. Editar o próprio cadastro (autosserviço) é item de escopo
    futuro — aqui apenas mostramos o que já está registrado, para o menu do
    rodapé não ser um texto morto.
    """
    conexao = conectar()
    cursor = conexao.cursor()

    linha = cursor.execute(
        """
        SELECT id, email, tipo, nome, disciplinas, matricula
        FROM users WHERE email = ?
        """,
        (email.strip().lower(),),
    ).fetchone()

    if not linha:
        conexao.close()
        return {"sucesso": False, "mensagem": "Usuário não encontrado."}

    user_id, email, tipo, nome, disciplinas, matricula = linha

    # As turmas vinculadas dependem do perfil: o professor leciona, o aluno cursa.
    if tipo == "professor":
        turmas = cursor.execute(
            "SELECT nome, semestre FROM turmas WHERE professor_id = ? ORDER BY nome",
            (user_id,),
        ).fetchall()
    elif tipo == "aluno":
        turmas = cursor.execute(
            """
            SELECT t.nome, t.semestre
            FROM matriculas m JOIN turmas t ON t.id = m.turma_id
            WHERE m.aluno_id = ? ORDER BY t.nome
            """,
            (user_id,),
        ).fetchall()
    else:
        turmas = []

    conexao.close()

    return {
        "sucesso": True,
        "email": email,
        "tipo": tipo,
        "nome": nome or "",
        "disciplinas": disciplinas or "",
        "matricula": matricula or "",
        "turmas": [{"nome": t[0], "semestre": t[1]} for t in turmas],
    }


def turma_pertence_ao_professor(turma_id: int, professor_email: str) -> bool:
    conexao = conectar()
    professor = buscar_usuario(conexao, professor_email)

    if not professor:
        conexao.close()
        return False

    cursor = conexao.cursor()
    cursor.execute(
        "SELECT id FROM turmas WHERE id = ? AND professor_id = ?",
        (turma_id, professor[0]),
    )
    resultado = cursor.fetchone()
    conexao.close()

    return resultado is not None
