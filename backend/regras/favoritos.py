"""Favoritos: o material que o aluno quer reencontrar rápido.

Valem entre semestres. O material marcado no 3º período continua à mão no 6º,
quando a matéria volta na revisão para a residência — por isso a lista não
filtra pelo semestre vigente, só pela regra de sempre: o aluno continua podendo
ver o material (matriculado na disciplina, material publicado).
"""

from datetime import datetime, timezone

from regras.aluno import _buscar_aluno, _esta_publicado, material_visivel_para
from regras.turmas import conectar


def marcar_favorito(aluno_email: str, material_id: int) -> dict:
    conexao = conectar()
    aluno = _buscar_aluno(conexao, aluno_email)

    # "Não existe" e "você não vê" dão a mesma resposta.
    if not aluno or not material_visivel_para(conexao, aluno[0], material_id):
        conexao.close()
        return {"sucesso": False, "mensagem": "Material não encontrado."}

    # Idempotente: marcar duas vezes não é erro, é o mesmo estado.
    conexao.execute(
        "INSERT OR IGNORE INTO favoritos (aluno_id, material_id, criado_em) VALUES (?, ?, ?)",
        (aluno[0], int(material_id), datetime.now(timezone.utc).isoformat()),
    )
    conexao.commit()
    conexao.close()
    return {"sucesso": True, "favorito": True}


def desmarcar_favorito(aluno_email: str, material_id: int) -> dict:
    conexao = conectar()
    aluno = _buscar_aluno(conexao, aluno_email)

    if not aluno:
        conexao.close()
        return {"sucesso": False, "mensagem": "Aluno não encontrado."}

    conexao.execute(
        "DELETE FROM favoritos WHERE aluno_id = ? AND material_id = ?", (aluno[0], int(material_id))
    )
    conexao.commit()
    conexao.close()
    return {"sucesso": True, "favorito": False}


def listar_favoritos(aluno_email: str) -> dict:
    """Os favoritos que o aluno ainda consegue abrir, do mais recente para o mais antigo.

    Favorito de material que voltou a ser rascunho, ou de disciplina da qual o
    aluno saiu, não aparece — mas também não é apagado: se o material voltar,
    a estrela volta junto.
    """
    conexao = conectar()
    aluno = _buscar_aluno(conexao, aluno_email)

    if not aluno:
        conexao.close()
        return {"sucesso": False, "mensagem": "Aluno não encontrado.", "favoritos": []}

    linhas = conexao.execute(
        """
        SELECT m.id, m.titulo, m.tipo, m.link_url, m.arquivo_nome, m.descricao,
               m.rascunho, m.data_liberacao, t.id, t.nome, t.semestre
          FROM favoritos f
          JOIN materiais m ON m.id = f.material_id
          JOIN turmas t ON t.id = m.turma_id
          JOIN matriculas mt ON mt.turma_id = t.id AND mt.aluno_id = f.aluno_id
         WHERE f.aluno_id = ?
         ORDER BY f.criado_em DESC
        """,
        (aluno[0],),
    ).fetchall()
    conexao.close()

    favoritos = [
        {
            "id": id_,
            "titulo": titulo,
            "tipo": tipo,
            "link_url": link_url,
            "arquivo_nome": arquivo_nome,
            "descricao": descricao,
            "turma_id": turma_id,
            "turma_nome": turma_nome,
            "semestre": semestre,
            "favorito": True,
        }
        for (id_, titulo, tipo, link_url, arquivo_nome, descricao, rascunho,
             data_liberacao, turma_id, turma_nome, semestre) in linhas
        if _esta_publicado(rascunho, data_liberacao)
    ]
    return {"sucesso": True, "favoritos": favoritos}
