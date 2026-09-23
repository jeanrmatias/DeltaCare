"""Chat de IA do aluno: RAG restrito ao material em PDF liberado pelo
professor na turma. Sem depender do FastAPI (testável sozinho).

Depende do pacote `pypdf` (extrair texto do PDF) e de um servidor Ollama
local com os modelos `gpt-oss:20b` (chat) e `nomic-embed-text` (embeddings):

    ollama pull gpt-oss:20b
    ollama pull nomic-embed-text

As duas únicas funções que falam com o modelo (gerar_embedding e
gerar_resposta_chat) ficam isoladas: toda a lógica de negócio (chunking,
busca por similaridade, montagem do prompt, matrícula) recebe essas funções
como parâmetro (gerar_embedding_fn / gerar_resposta_fn), então dá pra testar
com versões falsas delas. O endereço do Ollama pode ser trocado pela variável
de ambiente OLLAMA_URL (padrão http://localhost:11434).
"""

import json
import math
import os
import urllib.request
from datetime import datetime, timezone

from logica_turmas import buscar_usuario, conectar

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODELO_EMBEDDING = "nomic-embed-text"
MODELO_CHAT = "gpt-oss:20b"
TAMANHO_CHUNK = 800  # caracteres
SOBREPOSICAO = 100
TOP_K = 5

PROMPT_SISTEMA = """Você é o assistente de estudos da Delta Care, plataforma de ensino de uma \
faculdade de medicina. Responda SOMENTE com base nos trechos de material fornecidos abaixo, que \
vieram do material que o professor disponibilizou para esta turma.

Regras:
- Não use nenhum conhecimento externo, mesmo que você saiba a resposta.
- Se os trechos não tiverem informação suficiente para responder, diga claramente que o \
material disponibilizado não cobre esse ponto e sugira que o aluno pergunte ao professor. Não \
tente completar a lacuna com conhecimento próprio.
- Sempre que possível, indique de qual material a informação veio.
- Seja didático, claro e objetivo, no nível de um estudante de medicina.
"""


# =========================================================================
# Chamadas ao Ollama local (isoladas para poder trocar por um fake no teste)
# =========================================================================

def _chamar_ollama(caminho: str, corpo: dict) -> dict:
    requisicao = urllib.request.Request(
        f"{OLLAMA_URL}{caminho}",
        data=json.dumps(corpo).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(requisicao, timeout=300) as resposta:
            return json.loads(resposta.read().decode("utf-8"))
    except OSError as erro:
        raise RuntimeError(f"Não foi possível falar com o Ollama em {OLLAMA_URL}: {erro}") from erro


def gerar_embedding(texto: str) -> list:
    resposta = _chamar_ollama("/api/embed", {"model": MODELO_EMBEDDING, "input": texto})
    return resposta["embeddings"][0]


def gerar_resposta_chat(mensagens: list) -> str:
    resposta = _chamar_ollama(
        "/api/chat",
        {
            "model": MODELO_CHAT,
            "messages": mensagens,
            "stream": False,
            "options": {"temperature": 0.2},
        },
    )
    return resposta["message"]["content"]


# =========================================================================
# Extração e indexação do PDF
# =========================================================================

def extrair_texto_pdf(caminho: str) -> str:
    from pypdf import PdfReader

    leitor = PdfReader(caminho)
    partes = [pagina.extract_text() or "" for pagina in leitor.pages]
    return "\n".join(partes).strip()


def dividir_em_chunks(texto: str, tamanho: int = TAMANHO_CHUNK, sobreposicao: int = SOBREPOSICAO) -> list:
    texto = " ".join(texto.split())
    if not texto:
        return []

    chunks = []
    inicio = 0
    while inicio < len(texto):
        fim = inicio + tamanho
        chunks.append(texto[inicio:fim])
        if fim >= len(texto):
            break
        inicio += tamanho - sobreposicao

    return chunks


def indexar_material(material_id: int, gerar_embedding_fn=gerar_embedding) -> dict:
    """Extrai o texto do PDF do material, divide em chunks e salva os
    embeddings. Só funciona para materiais do tipo 'pdf' com arquivo salvo.
    Chamar depois que um material PDF é criado ou publicado.
    """
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("SELECT tipo, arquivo_caminho FROM materiais WHERE id = ?", (material_id,))
    material = cursor.fetchone()

    if not material or material[0] != "pdf" or not material[1]:
        conexao.close()
        return {"sucesso": False, "mensagem": "Material não é um PDF com arquivo salvo."}

    _, caminho = material

    try:
        texto = extrair_texto_pdf(caminho)
    except Exception as erro:
        conexao.close()
        return {"sucesso": False, "mensagem": f"Não foi possível ler o PDF: {erro}"}

    chunks = dividir_em_chunks(texto)

    if not chunks:
        conexao.close()
        return {"sucesso": False, "mensagem": "O PDF não tem texto extraível (pode ser um PDF escaneado sem OCR)."}

    cursor.execute("DELETE FROM material_chunks WHERE material_id = ?", (material_id,))

    for indice, chunk in enumerate(chunks):
        embedding = gerar_embedding_fn(chunk)
        cursor.execute(
            "INSERT INTO material_chunks (material_id, indice, texto, embedding) VALUES (?, ?, ?, ?)",
            (material_id, indice, chunk, json.dumps(embedding)),
        )

    conexao.commit()
    conexao.close()

    return {"sucesso": True, "mensagem": f"{len(chunks)} trecho(s) indexado(s).", "total_chunks": len(chunks)}


# =========================================================================
# Busca por similaridade + geração da resposta
# =========================================================================

def _similaridade_cosseno(a: list, b: list) -> float:
    produto = sum(x * y for x, y in zip(a, b))
    norma_a = math.sqrt(sum(x * x for x in a))
    norma_b = math.sqrt(sum(y * y for y in b))
    if norma_a == 0 or norma_b == 0:
        return 0.0
    return produto / (norma_a * norma_b)


def _status_material(rascunho: int, data_liberacao) -> str:
    """Mesma regra de logica_materiais._calcular_status, reaplicada aqui
    pra evitar import cruzado (logica_materiais já importa de logica_turmas)."""
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


def buscar_trechos_relevantes(turma_id: int, pergunta: str, gerar_embedding_fn=gerar_embedding, top_k: int = TOP_K) -> list:
    """Busca os trechos de material mais relevantes pra pergunta, só entre
    os materiais já PUBLICADOS (não rascunho, e já liberados se agendados)
    da turma — o aluno nunca vê rascunho nem material agendado pro futuro.
    """
    embedding_pergunta = gerar_embedding_fn(pergunta)

    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute(
        '''
        SELECT c.texto, c.embedding, m.titulo, m.id, m.rascunho, m.data_liberacao
        FROM material_chunks c
        JOIN materiais m ON m.id = c.material_id
        WHERE m.turma_id = ?
        ''',
        (turma_id,),
    )
    linhas = cursor.fetchall()
    conexao.close()

    candidatos = []
    for texto, embedding_json, titulo_material, material_id, rascunho, data_liberacao in linhas:
        if _status_material(rascunho, data_liberacao) != "publicado":
            continue
        embedding = json.loads(embedding_json)
        pontuacao = _similaridade_cosseno(embedding_pergunta, embedding)
        candidatos.append({
            "texto": texto,
            "pontuacao": pontuacao,
            "material": titulo_material,
            "material_id": material_id,
        })

    candidatos.sort(key=lambda c: c["pontuacao"], reverse=True)
    return candidatos[:top_k]


def montar_contexto(trechos: list) -> str:
    if not trechos:
        return "(Nenhum trecho de material relevante foi encontrado para esta turma.)"
    partes = [f"[Material: {t['material']}]\n{t['texto']}" for t in trechos]
    return "\n\n---\n\n".join(partes)


def _salvar_mensagem(aluno_id: int, turma_id: int, papel: str, conteudo: str, fontes: list = None) -> None:
    conexao = conectar()
    agora = datetime.now(timezone.utc).isoformat()
    cursor = conexao.cursor()
    cursor.execute(
        "INSERT INTO chat_mensagens (aluno_id, turma_id, papel, conteudo, fontes, criado_em) VALUES (?, ?, ?, ?, ?, ?)",
        (aluno_id, turma_id, papel, conteudo, json.dumps(fontes) if fontes else None, agora),
    )
    conexao.commit()
    conexao.close()


def responder_pergunta(
    aluno_email: str,
    turma_id: int,
    pergunta: str,
    gerar_embedding_fn=gerar_embedding,
    gerar_resposta_fn=gerar_resposta_chat,
) -> dict:
    from logica_matriculas import aluno_matriculado_na_turma

    pergunta = pergunta.strip()
    if not pergunta:
        return {"sucesso": False, "mensagem": "Digite uma pergunta."}

    if not aluno_matriculado_na_turma(aluno_email, turma_id):
        return {"sucesso": False, "mensagem": "Você não está matriculado nessa turma."}

    conexao = conectar()
    aluno = buscar_usuario(conexao, aluno_email)
    conexao.close()

    trechos = buscar_trechos_relevantes(turma_id, pergunta, gerar_embedding_fn=gerar_embedding_fn)
    contexto = montar_contexto(trechos)

    mensagens = [
        {"role": "system", "content": PROMPT_SISTEMA},
        {"role": "user", "content": f"Material disponível:\n\n{contexto}\n\nPergunta do aluno: {pergunta}"},
    ]

    resposta_texto = gerar_resposta_fn(mensagens)
    fontes = sorted({t["material"] for t in trechos})

    _salvar_mensagem(aluno[0], turma_id, "user", pergunta)
    _salvar_mensagem(aluno[0], turma_id, "assistant", resposta_texto, fontes=fontes)

    return {"sucesso": True, "resposta": resposta_texto, "fontes": fontes}


def buscar_historico(aluno_email: str, turma_id: int) -> dict:
    conexao = conectar()
    aluno = buscar_usuario(conexao, aluno_email)

    if not aluno:
        conexao.close()
        return {"sucesso": False, "mensagem": "Aluno não encontrado.", "mensagens": []}

    cursor = conexao.cursor()
    cursor.execute(
        '''
        SELECT papel, conteudo, fontes, criado_em FROM chat_mensagens
        WHERE aluno_id = ? AND turma_id = ?
        ORDER BY criado_em
        ''',
        (aluno[0], turma_id),
    )
    mensagens = [
        {"papel": p, "conteudo": c, "fontes": json.loads(f) if f else [], "criado_em": e}
        for p, c, f, e in cursor.fetchall()
    ]
    conexao.close()

    return {"sucesso": True, "mensagens": mensagens}
