"""Anotações do aluno sobre o material.

**Privadas.** Não existe rota pela qual professor ou administração leiam uma
anotação, e um aluno não vê a do colega nem no mesmo material. Anotação de
estudo é do aluno: ele escreve o que não entendeu, o que achou fraco na aula,
o que vai perguntar — e só escreve isso com franqueza se ninguém mais lê.

A anotação sobrevive ao material. Se o professor apagar ou reorganizar, ela
perde o vínculo mas fica, com o título que o material tinha (ver
infra/database.py). Apagar o caderno do aluno porque a disciplina mudou seria
destruir trabalho dele.

`trecho` é a passagem citada, colada pelo aluno. Marcar o texto dentro do PDF
exigiria um leitor de PDF próprio; a citação resolve o que importa — saber a
que parte do material a nota se refere.
"""

from datetime import datetime, timezone

from regras.aluno import _buscar_aluno, material_visivel_para
from regras.turmas import conectar

TAMANHO_TEXTO = 5000
TAMANHO_TRECHO = 1000


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validar(texto: str, trecho: str) -> str:
    if not texto:
        return "Escreva a anotação."
    if len(texto) > TAMANHO_TEXTO:
        return f"Anotação com no máximo {TAMANHO_TEXTO} caracteres."
    if len(trecho) > TAMANHO_TRECHO:
        return f"Trecho citado com no máximo {TAMANHO_TRECHO} caracteres."
    return ""


def _formatar(linha) -> dict:
    id_, material_id, material_titulo, trecho, texto, criado_em, atualizado_em = linha
    return {
        "id": id_,
        "material_id": material_id,
        "material_titulo": material_titulo,
        # Sem vínculo: o material foi apagado. A tela diz isso em vez de
        # oferecer um "abrir material" que daria erro.
        "material_disponivel": material_id is not None,
        "trecho": trecho or "",
        "texto": texto,
        "criado_em": criado_em,
        "atualizado_em": atualizado_em,
    }


_COLUNAS = "id, material_id, material_titulo, trecho, texto, criado_em, atualizado_em"


def criar_anotacao(aluno_email: str, material_id: int, texto: str, trecho: str = "") -> dict:
    texto = (texto or "").strip()
    trecho = (trecho or "").strip()

    erro = _validar(texto, trecho)
    if erro:
        return {"sucesso": False, "mensagem": erro}

    conexao = conectar()
    aluno = _buscar_aluno(conexao, aluno_email)
    visivel = material_visivel_para(conexao, aluno[0], material_id) if aluno else None

    if not aluno or not visivel:
        conexao.close()
        return {"sucesso": False, "mensagem": "Material não encontrado."}

    agora = _agora()
    cursor = conexao.cursor()
    cursor.execute(
        "INSERT INTO anotacoes (aluno_id, material_id, material_titulo, trecho, texto, criado_em, atualizado_em)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (aluno[0], int(material_id), visivel[0], trecho or None, texto, agora, agora),
    )
    anotacao_id = cursor.lastrowid
    conexao.commit()
    linha = conexao.execute(f"SELECT {_COLUNAS} FROM anotacoes WHERE id = ?", (anotacao_id,)).fetchone()
    conexao.close()

    return {"sucesso": True, "mensagem": "Anotação salva.", "anotacao": _formatar(linha)}


def listar_anotacoes(aluno_email: str, material_id: int | None = None) -> dict:
    """As anotações do próprio aluno — todas, ou as de um material.

    O filtro `aluno_id` está em toda consulta, e é ele que faz a privacidade:
    não há parâmetro que troque de dono.
    """
    conexao = conectar()
    aluno = _buscar_aluno(conexao, aluno_email)

    if not aluno:
        conexao.close()
        return {"sucesso": False, "mensagem": "Aluno não encontrado.", "anotacoes": []}

    consulta = f"SELECT {_COLUNAS} FROM anotacoes WHERE aluno_id = ?"
    parametros = [aluno[0]]
    if material_id is not None:
        consulta += " AND material_id = ?"
        parametros.append(int(material_id))
    consulta += " ORDER BY atualizado_em DESC"

    linhas = conexao.execute(consulta, parametros).fetchall()
    conexao.close()
    return {"sucesso": True, "anotacoes": [_formatar(linha) for linha in linhas]}


def _minha(conexao, aluno_id: int, anotacao_id: int) -> bool:
    return conexao.execute(
        "SELECT 1 FROM anotacoes WHERE id = ? AND aluno_id = ?", (int(anotacao_id), aluno_id)
    ).fetchone() is not None


def editar_anotacao(aluno_email: str, anotacao_id: int, texto: str, trecho: str = "") -> dict:
    texto = (texto or "").strip()
    trecho = (trecho or "").strip()

    erro = _validar(texto, trecho)
    if erro:
        return {"sucesso": False, "mensagem": erro}

    conexao = conectar()
    aluno = _buscar_aluno(conexao, aluno_email)

    # A anotação de outro aluno recebe a mesma resposta que a inexistente.
    if not aluno or not _minha(conexao, aluno[0], anotacao_id):
        conexao.close()
        return {"sucesso": False, "mensagem": "Anotação não encontrada."}

    conexao.execute(
        "UPDATE anotacoes SET texto = ?, trecho = ?, atualizado_em = ? WHERE id = ?",
        (texto, trecho or None, _agora(), int(anotacao_id)),
    )
    conexao.commit()
    linha = conexao.execute(f"SELECT {_COLUNAS} FROM anotacoes WHERE id = ?", (int(anotacao_id),)).fetchone()
    conexao.close()

    return {"sucesso": True, "mensagem": "Anotação atualizada.", "anotacao": _formatar(linha)}


def excluir_anotacao(aluno_email: str, anotacao_id: int) -> dict:
    conexao = conectar()
    aluno = _buscar_aluno(conexao, aluno_email)

    if not aluno or not _minha(conexao, aluno[0], anotacao_id):
        conexao.close()
        return {"sucesso": False, "mensagem": "Anotação não encontrada."}

    conexao.execute("DELETE FROM anotacoes WHERE id = ?", (int(anotacao_id),))
    conexao.commit()
    conexao.close()
    return {"sucesso": True, "mensagem": "Anotação apagada."}
