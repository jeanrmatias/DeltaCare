"""Lacunas do material: o que os alunos perguntam e o material não responde.

O assistente sabe, a cada resposta, se o material cobriu a pergunta por
inteiro, em parte ou nada (regras/chat_ia.py). Aqui isso vira um recado para
o professor: "a dobutamina é citada, mas sem a dose — 4 alunos perguntaram".
É o que fecha o ciclo de um material raso: o assistente não pode completar a
lacuna, mas o professor pode.

**Privacidade, que manda no desenho.** A política promete que a conversa com o
assistente é individual. Então o professor não vê, nunca:

- o texto da pergunta — só o assunto, em poucas palavras, que o modelo resume;
- quem perguntou — só quantos alunos;
- assunto de um aluno só: com um, dá para deduzir quem foi. Um assunto aparece
  quando pelo menos MIN_ALUNOS alunos diferentes perguntaram sobre ele, e a
  tela diz quantos ficaram de fora por isso.

Quando o aluno pede a exclusão da conta, as conversas dele são apagadas
(regras/privacidade.py) e saem destas contagens junto.
"""

import re
from collections import Counter
from datetime import datetime, timezone

from regras.chat_ia import _normalizar_para_busca
from regras.turmas import buscar_usuario, conectar

# Abaixo disso o assunto não aparece: com um aluno só, o professor saberia quem
# perguntou. Dois é o mínimo que já não aponta ninguém numa turma; subir o
# número protege mais e mostra menos.
MIN_ALUNOS = 2

TIPOS = {
    "parcial": "O material cita, mas não explica",
    "nenhuma": "O material não trata do tema",
}


def chave_do_assunto(assunto: str) -> str:
    """'A dobutamina.' e 'dobutamina' são o mesmo assunto."""
    texto = _normalizar_para_busca(assunto or "")
    texto = re.sub(r"[^\w\s-]", " ", texto)
    texto = re.sub(r"^(o|a|os|as|um|uma)\s+", "", texto.strip())
    return re.sub(r"\s+", " ", texto).strip()


def _turmas_do_professor(conexao, professor_id: int, turma_id: int | None) -> list:
    sql = "SELECT id, nome, semestre FROM turmas WHERE professor_id = ?"
    parametros = [professor_id]
    if turma_id is not None:
        sql += " AND id = ?"
        parametros.append(int(turma_id))
    return conexao.execute(sql + " ORDER BY nome", parametros).fetchall()


def listar_lacunas(professor_email: str, turma_id: int | None = None) -> dict:
    conexao = conectar()
    professor = buscar_usuario(conexao, professor_email)
    if not professor or professor[1] != "professor":
        conexao.close()
        return {"sucesso": False, "mensagem": "Só o professor vê as lacunas do material.", "disciplinas": []}

    turmas = _turmas_do_professor(conexao, professor[0], turma_id)
    if turma_id is not None and not turmas:
        conexao.close()
        return {"sucesso": False, "mensagem": "Disciplina não encontrada.", "disciplinas": []}

    disciplinas = []
    for tid, nome, semestre in turmas:
        tratados = dict(conexao.execute(
            "SELECT assunto, tratado_em FROM lacunas_tratadas WHERE turma_id = ?", (tid,)
        ).fetchall())
        linhas = conexao.execute(
            """
            SELECT aluno_id, cobertura, assunto, lacuna, criado_em FROM chat_mensagens
             WHERE turma_id = ? AND papel = 'assistant'
               AND cobertura IN ('parcial', 'nenhuma', 'sem_material')
            """,
            (tid,),
        ).fetchall()

        grupos = {}
        sem_material = {"perguntas": 0, "alunos": set()}
        for aluno_id, cobertura, assunto, lacuna, criado_em in linhas:
            if cobertura == "sem_material":
                sem_material["perguntas"] += 1
                sem_material["alunos"].add(aluno_id)
                continue
            chave = chave_do_assunto(assunto)
            # Tratado: só contam as perguntas feitas depois que o professor
            # marcou. Pergunta nova sobre o mesmo assunto traz ele de volta.
            if not chave or (chave in tratados and criado_em <= tratados[chave]):
                continue
            grupo = grupos.setdefault(chave, {"nomes": Counter(), "alunos": set(), "coberturas": Counter(),
                                              "lacunas": Counter(), "perguntas": 0, "ultima": ""})
            grupo["nomes"][assunto.strip()] += 1
            grupo["alunos"].add(aluno_id)
            grupo["coberturas"][cobertura] += 1
            if lacuna:
                grupo["lacunas"][lacuna.strip()] += 1
            grupo["perguntas"] += 1
            grupo["ultima"] = max(grupo["ultima"], criado_em)

        visiveis = [(chave, g) for chave, g in grupos.items() if len(g["alunos"]) >= MIN_ALUNOS]
        visiveis.sort(key=lambda item: (-len(item[1]["alunos"]), -item[1]["perguntas"], item[0]))

        disciplinas.append({
            "id": tid,
            "nome": nome,
            "semestre": semestre,
            "lacunas": [
                {
                    "chave": chave,
                    "assunto": g["nomes"].most_common(1)[0][0],
                    "tipo": "parcial" if g["coberturas"]["parcial"] >= g["coberturas"]["nenhuma"] else "nenhuma",
                    "alunos": len(g["alunos"]),
                    "perguntas": g["perguntas"],
                    "o_que_falta": [texto for texto, _ in g["lacunas"].most_common(3)],
                    "ultima_em": g["ultima"],
                }
                for chave, g in visiveis
            ],
            "ocultas": len(grupos) - len(visiveis),
            "sem_material": {"perguntas": sem_material["perguntas"], "alunos": len(sem_material["alunos"])},
        })

    conexao.close()
    return {"sucesso": True, "min_alunos": MIN_ALUNOS, "tipos": TIPOS, "disciplinas": disciplinas}


def marcar_tratada(professor_email: str, turma_id: int, assunto: str) -> dict:
    """O professor publicou material sobre o assunto: ele sai da lista até
    alguém perguntar de novo."""
    chave = chave_do_assunto(assunto)
    if not chave:
        return {"sucesso": False, "mensagem": "Assunto inválido."}

    conexao = conectar()
    professor = buscar_usuario(conexao, professor_email)
    if not professor or not _turmas_do_professor(conexao, professor[0], turma_id):
        conexao.close()
        return {"sucesso": False, "mensagem": "Disciplina não encontrada."}

    conexao.execute(
        "INSERT INTO lacunas_tratadas (turma_id, assunto, tratado_em) VALUES (?, ?, ?)"
        " ON CONFLICT (turma_id, assunto) DO UPDATE SET tratado_em = excluded.tratado_em",
        (int(turma_id), chave, datetime.now(timezone.utc).isoformat()),
    )
    conexao.commit()
    conexao.close()
    return {"sucesso": True, "mensagem": "Marcado como tratado. Volta para a lista se alguém perguntar de novo."}
