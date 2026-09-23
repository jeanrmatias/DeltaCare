"""Regras de negócio de materiais (Sprint 2 do backlog). Sem depender do FastAPI."""

import sqlite3
from datetime import datetime, timezone

from arquivos import remover_arquivo, salvar_arquivo_base64
from logica_turmas import turma_pertence_ao_professor, buscar_professor, conectar

TIPOS_VALIDOS = ("pdf", "documento", "video", "link")


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _calcular_status(rascunho: int, data_liberacao: str | None) -> str:
    if rascunho:
        return "rascunho"

    if data_liberacao:
        try:
            liberacao = datetime.fromisoformat(data_liberacao)
            if liberacao.tzinfo is None:
                liberacao = liberacao.replace(tzinfo=timezone.utc)
            if liberacao > datetime.now(timezone.utc):
                return "agendado"
        except ValueError:
            pass

    return "publicado"


def _linha_para_dict(linha) -> dict:
    (id_, titulo, descricao, tipo, link_url, arquivo_nome, assunto,
     topico, aula, semestre, rascunho, data_liberacao, criado_em,
     atualizado_em, turma_id, turma_nome) = linha

    return {
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
        "rascunho": bool(rascunho),
        "data_liberacao": data_liberacao,
        "status": _calcular_status(rascunho, data_liberacao),
        "criado_em": criado_em,
        "atualizado_em": atualizado_em,
        "turma_id": turma_id,
        "turma_nome": turma_nome,
    }


def criar_material(
    professor_email: str,
    turma_id: int,
    titulo: str,
    tipo: str,
    descricao: str = "",
    assunto: str = "",
    topico: str = "",
    aula: str = "",
    semestre: str = "",
    rascunho: bool = True,
    data_liberacao: str | None = None,
    link_url: str | None = None,
    arquivo_base64: str | None = None,
    arquivo_nome: str | None = None,
) -> dict:
    titulo = titulo.strip()
    tipo = tipo.strip().lower()

    if not titulo:
        return {"sucesso": False, "mensagem": "Informe o título do material."}

    if tipo not in TIPOS_VALIDOS:
        return {"sucesso": False, "mensagem": f"Tipo inválido. Use um destes: {', '.join(TIPOS_VALIDOS)}."}

    if not turma_pertence_ao_professor(turma_id, professor_email):
        return {"sucesso": False, "mensagem": "Turma não encontrada para este professor."}

    caminho_arquivo = None

    if tipo == "link":
        link_url = (link_url or "").strip()
        if not link_url:
            return {"sucesso": False, "mensagem": "Informe o link do material."}
        if not (link_url.startswith("http://") or link_url.startswith("https://")):
            return {"sucesso": False, "mensagem": "O link precisa começar com http:// ou https://."}
    else:
        if not arquivo_base64 or not arquivo_nome:
            return {"sucesso": False, "mensagem": "Envie um arquivo para este tipo de material."}

        resultado = salvar_arquivo_base64(arquivo_base64, arquivo_nome, tipo)
        if not resultado["sucesso"]:
            return {"sucesso": False, "mensagem": resultado["mensagem"]}
        caminho_arquivo = resultado["caminho"]
        link_url = None

    conexao = conectar()
    professor = buscar_professor(conexao, professor_email)
    agora = _agora()

    cursor = conexao.cursor()
    cursor.execute(
        '''
        INSERT INTO materiais (
            professor_id, turma_id, titulo, descricao, tipo, link_url,
            arquivo_nome, arquivo_caminho, assunto, topico, aula, semestre,
            rascunho, data_liberacao, criado_em, atualizado_em
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            professor[0], turma_id, titulo, descricao, tipo, link_url,
            arquivo_nome if tipo != "link" else None, caminho_arquivo,
            assunto, topico, aula, semestre,
            1 if rascunho else 0, data_liberacao, agora, agora,
        ),
    )
    conexao.commit()
    material_id = cursor.lastrowid
    conexao.close()

    return {
        "sucesso": True,
        "mensagem": "Material salvo como rascunho." if rascunho else "Material publicado com sucesso!",
        "material_id": material_id,
    }


def listar_materiais(professor_email: str, turma_id: int | None = None) -> dict:
    conexao = conectar()
    professor = buscar_professor(conexao, professor_email)

    if not professor or professor[1] != "professor":
        conexao.close()
        return {"sucesso": False, "mensagem": "Professor não encontrado.", "materiais": []}

    consulta = '''
        SELECT m.id, m.titulo, m.descricao, m.tipo, m.link_url, m.arquivo_nome,
               m.assunto, m.topico, m.aula, m.semestre, m.rascunho,
               m.data_liberacao, m.criado_em, m.atualizado_em,
               m.turma_id, t.nome
        FROM materiais m
        JOIN turmas t ON t.id = m.turma_id
        WHERE m.professor_id = ?
    '''
    parametros = [professor[0]]

    if turma_id is not None:
        consulta += " AND m.turma_id = ?"
        parametros.append(turma_id)

    consulta += " ORDER BY m.criado_em DESC"

    cursor = conexao.cursor()
    cursor.execute(consulta, parametros)
    linhas = cursor.fetchall()
    conexao.close()

    return {"sucesso": True, "materiais": [_linha_para_dict(linha) for linha in linhas]}


def _buscar_material_do_professor(conexao, material_id: int, professor_email: str):
    professor = buscar_professor(conexao, professor_email)
    if not professor:
        return None, None

    cursor = conexao.cursor()
    cursor.execute(
        "SELECT id, professor_id, arquivo_caminho FROM materiais WHERE id = ?",
        (material_id,),
    )
    material = cursor.fetchone()

    if not material or material[1] != professor[0]:
        return None, professor

    return material, professor


def atualizar_material(material_id: int, professor_email: str, **campos) -> dict:
    conexao = conectar()
    material, _ = _buscar_material_do_professor(conexao, material_id, professor_email)

    if not material:
        conexao.close()
        return {"sucesso": False, "mensagem": "Material não encontrado."}

    campos_permitidos = {
        "titulo", "descricao", "assunto", "topico", "aula", "semestre",
        "rascunho", "data_liberacao", "link_url",
    }
    atualizacoes = {chave: valor for chave, valor in campos.items() if chave in campos_permitidos and valor is not None}

    if "rascunho" in campos:
        atualizacoes["rascunho"] = 1 if campos["rascunho"] else 0

    if not atualizacoes:
        conexao.close()
        return {"sucesso": False, "mensagem": "Nada para atualizar."}

    atualizacoes["atualizado_em"] = _agora()

    colunas = ", ".join(f"{chave} = ?" for chave in atualizacoes)
    valores = list(atualizacoes.values()) + [material_id]

    cursor = conexao.cursor()
    cursor.execute(f"UPDATE materiais SET {colunas} WHERE id = ?", valores)
    conexao.commit()
    conexao.close()

    return {"sucesso": True, "mensagem": "Material atualizado."}


def excluir_material(material_id: int, professor_email: str) -> dict:
    conexao = conectar()
    material, _ = _buscar_material_do_professor(conexao, material_id, professor_email)

    if not material:
        conexao.close()
        return {"sucesso": False, "mensagem": "Material não encontrado."}

    cursor = conexao.cursor()
    # Os trechos indexados para o chat de IA precisam sair junto: sem isso eles
    # ficam órfãos no banco, acumulando a cada material excluído.
    cursor.execute("DELETE FROM material_chunks WHERE material_id = ?", (material_id,))
    cursor.execute("DELETE FROM materiais WHERE id = ?", (material_id,))
    conexao.commit()
    conexao.close()

    remover_arquivo(material[2])

    return {"sucesso": True, "mensagem": "Material excluído."}


def obter_arquivo_material(material_id: int, professor_email: str):
    """Retorna (caminho_no_disco, nome_original) se o professor for dono do
    material e ele tiver um arquivo anexado. Senão, retorna None."""

    conexao = conectar()
    professor = buscar_professor(conexao, professor_email)

    if not professor:
        conexao.close()
        return None

    cursor = conexao.cursor()
    cursor.execute(
        "SELECT professor_id, arquivo_caminho, arquivo_nome FROM materiais WHERE id = ?",
        (material_id,),
    )
    material = cursor.fetchone()
    conexao.close()

    if not material or material[0] != professor[0] or not material[1]:
        return None

    return material[1], material[2]
