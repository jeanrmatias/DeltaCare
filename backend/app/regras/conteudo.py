"""Supervisão de conteúdo: a coordenação vendo o que as turmas recebem.

**O que a administração vê é o que os alunos veem ou vão ver — e nada que seja
trabalho pessoal de alguém.**

- Material e atividade **publicados ou agendados**. Agendado entra porque
  revisar antes de chegar ao aluno é justamente o sentido de supervisionar.
- **Rascunho, não.** É trabalho em andamento do professor, como um e-mail que
  ainda não foi enviado.
- Gabarito das objetivas, sim: "a questão 3 está com a resposta errada" é o
  caso típico de conformidade, e quem trata é a coordenação.
- **Entregas, anotações, conversas com o assistente e mensagens: nunca.** Não
  há função aqui que as leia, e não há rota que as entregue à administração
  (os testes conferem a lista de rotas).

Só leitura. Tirar material do ar é decisão de política — a coordenação pode
despublicar o material de um professor? — e fica fora até ser decidida. O
caminho que existe é o das denúncias, e esta tela mostra quantas estão abertas
para cada material.
"""

import json

from regras.atividades import _calcular_status as _status_da_atividade
from regras.materiais import _calcular_status as _status_do_material
from regras.semestres import chave_de_ordem, semestre_vigente
from regras.turmas import _eh_admin, conectar

VISIVEIS = ("publicado", "agendado")


def visao_do_conteudo(admin_email: str, semestre: str | None = None) -> dict:
    """Todas as disciplinas de um semestre, com o material e as atividades.

    Sem `semestre`, o vigente. `semestres` vem junto para a tela oferecer os
    outros — inclusive os antigos, que a coordenação pode precisar revisar
    depois de uma reclamação.
    """
    conexao = conectar()

    if not _eh_admin(conexao, admin_email):
        conexao.close()
        return {"sucesso": False, "mensagem": "Só a administração supervisiona conteúdo."}

    from regras.semestres import normalizar_semestre

    semestre = normalizar_semestre(semestre) if semestre else semestre_vigente()
    if not semestre:
        conexao.close()
        return {"sucesso": False, "mensagem": "Semestre inválido. Use o formato 2026/2."}

    cursor = conexao.cursor()
    semestres = sorted(
        {linha[0] for linha in cursor.execute("SELECT DISTINCT semestre FROM turmas").fetchall()} | {semestre},
        key=chave_de_ordem,
        reverse=True,
    )

    disciplinas = {
        linha[0]: {
            "id": linha[0],
            "nome": linha[1],
            "professor_nome": linha[2],
            "professor_email": linha[3],
            "total_alunos": linha[4],
            "materiais": [],
            "atividades": [],
        }
        for linha in cursor.execute(
            """
            SELECT t.id, t.nome, COALESCE(NULLIF(u.nome, ''), u.email), u.email,
                   (SELECT COUNT(*) FROM matriculas m WHERE m.turma_id = t.id)
              FROM turmas t JOIN users u ON u.id = t.professor_id
             WHERE t.semestre = ?
             ORDER BY t.nome
            """,
            (semestre,),
        ).fetchall()
    }

    if disciplinas:
        marcadores = ",".join("?" for _ in disciplinas)
        ids = list(disciplinas)

        for (id_, turma_id, titulo, tipo, descricao, assunto, topico, link_url, arquivo_nome,
             rascunho, data_liberacao, criado_em, denuncias) in cursor.execute(
            f"""
            SELECT m.id, m.turma_id, m.titulo, m.tipo, m.descricao, m.assunto, m.topico,
                   m.link_url, m.arquivo_nome, m.rascunho, m.data_liberacao, m.criado_em,
                   (SELECT COUNT(*) FROM denuncias d
                     WHERE d.material_id = m.id AND d.status IN ('aberta', 'em_analise'))
              FROM materiais m
             WHERE m.turma_id IN ({marcadores}) AND m.rascunho = 0
             ORDER BY m.criado_em DESC
            """,
            ids,
        ).fetchall():
            # O `rascunho = 0` do SQL só evita ler rascunho à toa. A regra é
            # esta linha: ela também separa agendado de publicado, que depende
            # da hora — não dá para tirá-la achando que o SQL já resolve.
            status = _status_do_material(rascunho, data_liberacao)
            if status not in VISIVEIS:
                continue
            disciplinas[turma_id]["materiais"].append({
                "id": id_,
                "titulo": titulo,
                "tipo": tipo,
                "descricao": descricao,
                "classificacao": " · ".join(p for p in (assunto, topico) if p),
                "link_url": link_url,
                "arquivo_nome": arquivo_nome,
                "status": status,
                "data_liberacao": data_liberacao,
                "criado_em": criado_em,
                "denuncias_abertas": denuncias,
            })

        for (id_, turma_id, titulo, tipo, pontos, prazo, rascunho, data_liberacao,
             total_questoes, entregues) in cursor.execute(
            f"""
            SELECT a.id, a.turma_id, a.titulo, a.tipo, a.pontos, a.prazo, a.rascunho,
                   a.data_liberacao,
                   (SELECT COUNT(*) FROM questoes q WHERE q.atividade_id = a.id),
                   (SELECT COUNT(*) FROM entregas e
                     WHERE e.atividade_id = a.id AND e.enviado_em IS NOT NULL)
              FROM atividades a
             WHERE a.turma_id IN ({marcadores}) AND a.rascunho = 0
             ORDER BY a.criado_em DESC
            """,
            ids,
        ).fetchall():
            status = _status_da_atividade(rascunho, data_liberacao)
            if status not in VISIVEIS:
                continue
            disciplinas[turma_id]["atividades"].append({
                "id": id_,
                "titulo": titulo,
                "tipo": tipo,
                "pontos": pontos,
                "prazo": prazo,
                "status": status,
                "data_liberacao": data_liberacao,
                "total_questoes": total_questoes,
                # Quantas entregas houve, e não o que foi entregue: é número
                # de acompanhamento da coordenação, não trabalho de aluno.
                "entregues": entregues,
            })

    conexao.close()

    return {
        "sucesso": True,
        "semestre": semestre,
        "semestres": semestres,
        "disciplinas": list(disciplinas.values()),
    }


def atividade_para_supervisao(admin_email: str, atividade_id: int) -> dict:
    """Enunciado e questões, com o gabarito. Rascunho não abre."""
    conexao = conectar()

    if not _eh_admin(conexao, admin_email):
        conexao.close()
        return {"sucesso": False, "mensagem": "Só a administração supervisiona conteúdo."}

    atividade = conexao.execute(
        """
        SELECT a.id, a.titulo, a.enunciado, a.tipo, a.pontos, a.prazo, a.rascunho,
               a.data_liberacao, t.nome
          FROM atividades a JOIN turmas t ON t.id = a.turma_id
         WHERE a.id = ?
        """,
        (int(atividade_id),),
    ).fetchone()

    # Rascunho responde como inexistente: nem a existência dele é da conta
    # da supervisão.
    if not atividade or _status_da_atividade(atividade[6], atividade[7]) not in VISIVEIS:
        conexao.close()
        return {"sucesso": False, "mensagem": "Atividade não encontrada."}

    questoes = [
        {
            "ordem": ordem,
            "enunciado": enunciado,
            "alternativas": json.loads(alternativas),
            "correta": correta,
        }
        for ordem, enunciado, alternativas, correta in conexao.execute(
            "SELECT ordem, enunciado, alternativas, correta FROM questoes"
            " WHERE atividade_id = ? ORDER BY ordem",
            (int(atividade_id),),
        ).fetchall()
    ]
    conexao.close()

    return {
        "sucesso": True,
        "atividade": {
            "id": atividade[0],
            "titulo": atividade[1],
            "enunciado": atividade[2],
            "tipo": atividade[3],
            "pontos": atividade[4],
            "prazo": atividade[5],
            "status": _status_da_atividade(atividade[6], atividade[7]),
            "turma_nome": atividade[8],
        },
        "questoes": questoes,
    }


def arquivo_para_supervisao(admin_email: str, material_id: int):
    """(caminho, nome) do arquivo de um material publicado ou agendado."""
    conexao = conectar()

    if not _eh_admin(conexao, admin_email):
        conexao.close()
        return None

    linha = conexao.execute(
        "SELECT arquivo_caminho, arquivo_nome, rascunho, data_liberacao FROM materiais WHERE id = ?",
        (int(material_id),),
    ).fetchone()
    conexao.close()

    if not linha or not linha[0] or _status_do_material(linha[2], linha[3]) not in VISIVEIS:
        return None
    return linha[0], linha[1]
