"""Matrícula de alunos em turmas. Sem depender do FastAPI (testável sozinho).

Mesmo padrão de permissão de logica_turmas.py: só o admin matricula ou
remove um aluno de uma turma. O aluno só vê e conversa (via chat de IA)
sobre as turmas em que está matriculado.
"""

from datetime import datetime, timezone

from logica_turmas import _eh_admin, buscar_usuario, conectar


def matricular_aluno(admin_email: str, aluno_email: str, turma_id: int) -> dict:
    conexao = conectar()

    if not _eh_admin(conexao, admin_email):
        conexao.close()
        return {"sucesso": False, "mensagem": "Só um administrador pode matricular aluno."}

    aluno = buscar_usuario(conexao, aluno_email)
    if not aluno or aluno[1] != "aluno":
        conexao.close()
        return {"sucesso": False, "mensagem": "Aluno não encontrado."}

    cursor = conexao.cursor()
    cursor.execute("SELECT id FROM turmas WHERE id = ?", (turma_id,))
    if not cursor.fetchone():
        conexao.close()
        return {"sucesso": False, "mensagem": "Turma não encontrada."}

    cursor.execute(
        "SELECT id FROM matriculas WHERE aluno_id = ? AND turma_id = ?",
        (aluno[0], turma_id),
    )
    if cursor.fetchone():
        conexao.close()
        return {"sucesso": False, "mensagem": "Esse aluno já está matriculado nessa turma."}

    agora = datetime.now(timezone.utc).isoformat()
    cursor.execute(
        "INSERT INTO matriculas (aluno_id, turma_id, criado_em) VALUES (?, ?, ?)",
        (aluno[0], turma_id, agora),
    )
    conexao.commit()
    conexao.close()

    return {"sucesso": True, "mensagem": "Aluno matriculado com sucesso!"}


def desmatricular_aluno(admin_email: str, aluno_email: str, turma_id: int) -> dict:
    conexao = conectar()

    if not _eh_admin(conexao, admin_email):
        conexao.close()
        return {"sucesso": False, "mensagem": "Só um administrador pode desmatricular aluno."}

    aluno = buscar_usuario(conexao, aluno_email)
    if not aluno:
        conexao.close()
        return {"sucesso": False, "mensagem": "Aluno não encontrado."}

    cursor = conexao.cursor()
    cursor.execute(
        "DELETE FROM matriculas WHERE aluno_id = ? AND turma_id = ?",
        (aluno[0], turma_id),
    )
    conexao.commit()
    conexao.close()

    return {"sucesso": True, "mensagem": "Aluno desmatriculado."}


def listar_alunos_da_turma(admin_email: str, turma_id: int) -> dict:
    conexao = conectar()

    if not _eh_admin(conexao, admin_email):
        conexao.close()
        return {"sucesso": False, "mensagem": "Só um administrador pode ver isso.", "alunos": []}

    cursor = conexao.cursor()
    cursor.execute(
        '''
        SELECT u.email FROM matriculas m
        JOIN users u ON u.id = m.aluno_id
        WHERE m.turma_id = ?
        ORDER BY u.email
        ''',
        (turma_id,),
    )
    alunos = [linha[0] for linha in cursor.fetchall()]
    conexao.close()

    return {"sucesso": True, "alunos": alunos}


def listar_alunos(admin_email: str) -> dict:
    """Todos os alunos cadastrados na plataforma (pra popular o seletor de matrícula)."""
    conexao = conectar()

    if not _eh_admin(conexao, admin_email):
        conexao.close()
        return {"sucesso": False, "mensagem": "Só um administrador pode ver isso.", "alunos": []}

    cursor = conexao.cursor()
    cursor.execute("SELECT email FROM users WHERE tipo = 'aluno' ORDER BY email")
    alunos = [linha[0] for linha in cursor.fetchall()]
    conexao.close()

    return {"sucesso": True, "alunos": alunos}


def listar_turmas_do_aluno(aluno_email: str) -> dict:
    """Turmas em que o aluno está matriculado (visão dele, só leitura)."""
    conexao = conectar()
    aluno = buscar_usuario(conexao, aluno_email)

    if not aluno or aluno[1] != "aluno":
        conexao.close()
        return {"sucesso": False, "mensagem": "Aluno não encontrado.", "turmas": []}

    cursor = conexao.cursor()
    cursor.execute(
        '''
        SELECT t.id, t.nome, t.semestre
        FROM matriculas m
        JOIN turmas t ON t.id = m.turma_id
        WHERE m.aluno_id = ?
        ORDER BY t.nome
        ''',
        (aluno[0],),
    )
    turmas = [{"id": linha[0], "nome": linha[1], "semestre": linha[2]} for linha in cursor.fetchall()]
    conexao.close()

    return {"sucesso": True, "turmas": turmas}


def aluno_matriculado_na_turma(aluno_email: str, turma_id: int) -> bool:
    conexao = conectar()
    aluno = buscar_usuario(conexao, aluno_email)

    if not aluno:
        conexao.close()
        return False

    cursor = conexao.cursor()
    cursor.execute(
        "SELECT id FROM matriculas WHERE aluno_id = ? AND turma_id = ?",
        (aluno[0], turma_id),
    )
    resultado = cursor.fetchone()
    conexao.close()

    return resultado is not None
