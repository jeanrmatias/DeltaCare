"""Regras de negócio de turmas. Sem depender do FastAPI (testável sozinho).

Quem cria, edita e exclui turmas é o administrador (US-07.xx do backlog —
governança da plataforma). O professor só enxerga as turmas que foram
atribuídas a ele; ele não cria nem edita turma, só publica/edita os
materiais dentro delas.
"""

import sqlite3
from datetime import datetime, timezone

DB_PATH = "deltacare.db"


def conectar():
    return sqlite3.connect(DB_PATH)


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


def criar_turma(admin_email: str, professor_email: str, nome: str, semestre: str) -> dict:
    nome = nome.strip()
    semestre = semestre.strip()

    if not nome:
        return {"sucesso": False, "mensagem": "Informe o nome da turma."}
    if not semestre:
        return {"sucesso": False, "mensagem": "Informe o semestre (ex.: 2026/2)."}

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

    agora = datetime.now(timezone.utc).isoformat()
    cursor.execute(
        "INSERT INTO turmas (nome, semestre, professor_id, criado_em) VALUES (?, ?, ?, ?)",
        (nome, semestre, professor_id, agora),
    )
    conexao.commit()
    turma_id = cursor.lastrowid
    conexao.close()

    return {
        "sucesso": True,
        "mensagem": "Turma criada com sucesso!",
        "turma": {"id": turma_id, "nome": nome, "semestre": semestre, "professor_email": professor_email},
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

    # Os materiais dessa turma ficam órfãos sem a turma; para manter a
    # integridade, exclui os materiais junto (aviso já é dado no front).
    cursor.execute("DELETE FROM materiais WHERE turma_id = ?", (turma_id,))
    cursor.execute("DELETE FROM turmas WHERE id = ?", (turma_id,))
    conexao.commit()
    conexao.close()

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
