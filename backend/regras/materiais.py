"""Regras de negócio de materiais (Sprint 2 do backlog). Sem depender do FastAPI."""

import sqlite3
from datetime import datetime, timezone

from infra.arquivos import remover_arquivo, salvar_arquivo_base64
from regras.turmas import turma_pertence_ao_professor, buscar_professor, conectar

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
    _caminho_pronto: str | None = None,
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
    elif _caminho_pronto:
        # Publicação em várias turmas: o arquivo já foi gravado na primeira.
        caminho_arquivo = _caminho_pronto
        link_url = None
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
    turma = cursor.execute("SELECT nome FROM turmas WHERE id = ?", (turma_id,)).fetchone()
    conexao.close()

    # Avisa os alunos só quando o material já está visível para eles. Rascunho
    # não avisa nunca; agendado avisa quando a data chega (ver
    # regras/notificacoes._liberar_agendados_pendentes).
    if not rascunho and not data_liberacao:
        from regras.notificacoes import notificar_alunos_da_turma

        notificar_alunos_da_turma(
            turma_id,
            "material",
            "Novo material disponível",
            f'"{titulo}" foi publicado em {turma[0] if turma else "sua turma"}.',
            "materiais.html",
        )

    return {
        "sucesso": True,
        "mensagem": "Material salvo como rascunho." if rascunho else "Material publicado com sucesso!",
        "material_id": material_id,
    }


def criar_material_em_turmas(professor_email: str, turma_ids: list, **campos) -> dict:
    """Publica o mesmo material em várias turmas de uma vez.

    O schema guarda `turma_id` na própria linha do material, então cada turma
    recebe um registro próprio. Mudar para uma relação muitos-para-muitos
    quebraria a listagem por turma do professor e a busca por turma do chat,
    sem ganho para o caso real — o professor edita e despublica turma a turma.

    O arquivo, porém, é gravado **uma única vez** e o caminho é compartilhado
    entre os registros; um PDF de 15 MB em cinco turmas ocuparia 75 MB à toa.
    Por isso `excluir_material` só apaga o arquivo do disco quando nenhum outro
    registro aponta para ele.
    """
    if not turma_ids:
        return {"sucesso": False, "mensagem": "Escolha pelo menos uma turma."}

    # Valida todas antes de criar qualquer uma: publicação parcial deixaria o
    # professor sem saber em quais turmas o material entrou.
    for turma_id in turma_ids:
        if not turma_pertence_ao_professor(turma_id, professor_email):
            return {"sucesso": False, "mensagem": "Uma das turmas não pertence a este professor."}

    criados = []
    caminho_compartilhado = None
    campos_arquivo = {
        "arquivo_base64": campos.pop("arquivo_base64", None),
        "arquivo_nome": campos.pop("arquivo_nome", None),
    }

    for indice, turma_id in enumerate(turma_ids):
        # Só a primeira chamada recebe o base64; as demais reaproveitam o
        # arquivo já gravado.
        if indice == 0:
            resultado = criar_material(
                professor_email=professor_email,
                turma_id=turma_id,
                **campos,
                **campos_arquivo,
            )
            if resultado.get("sucesso"):
                caminho_compartilhado = _caminho_do_material(resultado["material_id"])
        else:
            resultado = criar_material(
                professor_email=professor_email,
                turma_id=turma_id,
                **campos,
                arquivo_nome=campos_arquivo["arquivo_nome"],
                _caminho_pronto=caminho_compartilhado,
            )

        if not resultado.get("sucesso"):
            return {
                "sucesso": False,
                "mensagem": resultado.get("mensagem"),
                "criados": criados,
            }

        criados.append(resultado["material_id"])

    total = len(criados)
    return {
        "sucesso": True,
        "mensagem": f"Material publicado em {total} turma{'s' if total > 1 else ''}!",
        "material_ids": criados,
        "material_id": criados[0],
    }


def _caminho_do_material(material_id: int):
    conexao = conectar()
    linha = conexao.execute(
        "SELECT arquivo_caminho FROM materiais WHERE id = ?", (material_id,)
    ).fetchone()
    conexao.close()
    return linha[0] if linha else None


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
    # O arquivo pode estar compartilhado com o mesmo material publicado em
    # outra turma (ver criar_material_em_turmas). Só sai do disco quando o
    # último registro que aponta para ele é excluído.
    caminho = material[2]
    ainda_em_uso = 0
    if caminho:
        ainda_em_uso = cursor.execute(
            "SELECT COUNT(*) FROM materiais WHERE arquivo_caminho = ?", (caminho,)
        ).fetchone()[0]

    conexao.commit()
    conexao.close()

    if caminho and ainda_em_uso == 0:
        remover_arquivo(caminho)

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
