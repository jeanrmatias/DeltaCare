"""Matrícula de alunos em turmas. Sem depender do FastAPI (testável sozinho).

Mesmo padrão de permissão de regras/turmas.py: só o admin matricula ou
remove um aluno de uma turma. O aluno só vê e conversa (via chat de IA)
sobre as turmas em que está matriculado.
"""

import sqlite3
from datetime import datetime, timezone

from regras.turmas import _eh_admin, buscar_usuario, conectar


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
    try:
        cursor.execute(
            "INSERT INTO matriculas (aluno_id, turma_id, criado_em) VALUES (?, ?, ?)",
            (aluno[0], turma_id, agora),
        )
    except sqlite3.IntegrityError:
        # Outra requisição igual chegou entre a conferência acima e este
        # INSERT: o banco recusa pela restrição única, e a resposta é a mesma.
        conexao.rollback()
        conexao.close()
        return {"sucesso": False, "mensagem": "Esse aluno já está matriculado nessa turma."}
    conexao.commit()

    turma = cursor.execute("SELECT nome FROM turmas WHERE id = ?", (turma_id,)).fetchone()
    linha_nome = cursor.execute("SELECT nome FROM users WHERE id = ?", (aluno[0],)).fetchone()
    conexao.close()

    # Import aqui dentro para evitar ciclo: notificacoes importa de turmas, que
    # é de onde este módulo também importa.
    from regras.notificacoes import notificar_professor_da_turma

    nome_aluno = (linha_nome[0] if linha_nome and linha_nome[0] else aluno_email)
    notificar_professor_da_turma(
        turma_id,
        "matricula",
        "Novo aluno na turma",
        f"{nome_aluno} foi matriculado em {turma[0] if turma else 'uma turma sua'}.",
        "turmas.html",
    )

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
    # O nome do professor vem junto para a tela poder oferecer "leve ao Prof.
    # Fulano" quando o assistente recusa uma pergunta. Sem ele, a oferta seria
    # genérica — e genérica ninguém clica.
    cursor.execute(
        '''
        SELECT t.id, t.nome, t.semestre, u.nome, u.email
        FROM matriculas m
        JOIN turmas t ON t.id = m.turma_id
        JOIN users u ON u.id = t.professor_id
        WHERE m.aluno_id = ?
        ORDER BY t.nome
        ''',
        (aluno[0],),
    )
    from regras.semestres import chave_de_ordem, semestre_vigente

    vigente = semestre_vigente()
    turmas = [
        {
            "id": linha[0],
            "nome": linha[1],
            "semestre": linha[2],
            "professor_nome": linha[3] or linha[4],
            # As de semestres passados continuam aqui — o chat sobre material
            # antigo é justamente o que serve para revisar para a residência.
            # A marca é para a tela pôr as de agora na frente.
            "vigente": linha[2] == vigente,
        }
        for linha in cursor.fetchall()
    ]
    conexao.close()

    # Vigentes primeiro; depois as antigas, da mais recente para a mais velha.
    # Senão o seletor do chat abriria, por ordem alfabética, numa disciplina
    # de três semestres atrás.
    turmas.sort(key=lambda t: (not t["vigente"], tuple(-n for n in chave_de_ordem(t["semestre"])), t["nome"]))

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
