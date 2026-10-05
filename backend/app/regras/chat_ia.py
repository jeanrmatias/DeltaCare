"""Chat de IA do aluno: RAG restrito ao material em PDF liberado pelo
professor na turma. Sem depender do FastAPI (testável sozinho).

Depende do pacote `pypdf` (extrair texto do PDF) e de um servidor Ollama
local com os modelos `gpt-oss:20b` (chat) e `nomic-embed-text` (embeddings):

    ollama pull gpt-oss:20b
    ollama pull nomic-embed-text

As funções que falam com o modelo (gerar_embeddings, gerar_embedding e
gerar_resposta_chat) ficam isoladas: toda a lógica de negócio (chunking,
busca por similaridade, montagem do prompt, matrícula) recebe essas funções
como parâmetro (gerar_embeddings_fn / gerar_embedding_fn / gerar_resposta_fn),
então dá pra testar com versões falsas delas. O endereço do Ollama pode ser
trocado pela variável de ambiente OLLAMA_URL (padrão http://127.0.0.1:11434).
"""

import heapq
import json
import operator
import os
import re
import unicodedata
import urllib.request
from datetime import datetime, timezone

from infra.vetores import desempacotar, empacotar, normalizar
from regras.turmas import buscar_usuario, conectar

# 127.0.0.1, e não "localhost". No Windows, "localhost" tenta o IPv6 (::1)
# primeiro; o Ollama só escuta no IPv4, e cada chamada esperava ~2 s antes de
# cair para ele. Medido: 2.178 ms por chamada contra 11 ms. Cada pergunta ao
# chat faz duas chamadas — eram 4 s de espera por pergunta, sem fazer nada.
OLLAMA_URL_PADRAO = "http://127.0.0.1:11434"
OLLAMA_URL = os.environ.get("OLLAMA_URL", OLLAMA_URL_PADRAO)
MODELO_EMBEDDING = os.environ.get("MODELO_EMBEDDING", "nomic-embed-text")
# Padrão é o gpt-oss:20b. Dá pra trocar com a variável MODELO_CHAT sem
# mexer no código (ex.: pra testar com um modelo menor numa GPU com menos
# VRAM, tipo llama3.1:8b).
MODELO_CHAT = os.environ.get("MODELO_CHAT", "gpt-oss:20b")
# O gpt-oss é um modelo de raciocínio: ele "pensa" antes de responder, e
# esses tokens de raciocínio custam tempo. Para o nosso caso (responder a
# partir de trechos já selecionados) o esforço baixo basta e corta o tempo
# de resposta pela metade, sem perder qualidade. Medido com o material de
# teste: 31s -> 13s. Modelos que não são de raciocínio ignoram esse campo.
ESFORCO_RACIOCINIO = os.environ.get("ESFORCO_RACIOCINIO", "low")
TAMANHO_CHUNK = 800  # caracteres
SOBREPOSICAO = 100

# Quantos trechos vão para o contexto do modelo.
# Medido com uma apostila de 18 trechos: com 5, a busca perdia informação em
# 8% das perguntas; com 10, acertou todas. Dez trechos ocupam ~2,5 mil dos
# 4096 tokens de contexto, deixando folga suficiente para a resposta — 14 já
# deixaria só ~570 tokens e arriscaria cortar o texto no meio.
TOP_K = 10

# Peso do casamento literal de termos na ordenação dos trechos (ver
# _pontuar_trecho). Pequeno de propósito: desempata entre trechos já
# semanticamente próximos, sem virar busca por palavra.
PESO_BUSCA_LITERAL = 0.12

# O prompt não manda o modelo sugerir "pergunte ao professor". Decidir o
# próximo passo do aluno é comportamento de produto, e o modelo improvisava uma
# frase diferente a cada recusa — inclusive mandando procurar o professor por
# uma pergunta que não tinha relação nenhuma com a matéria. Quem oferece o
# caminho agora é a interface (OfertaProfessor, em frontend/src/paginas/aluno/
# Chat.jsx), e ela oferece com condicional, porque a plataforma não sabe se a
# pergunta faz sentido.
#
# Nem a interface aponta *qual* professor ou disciplina. Já apontou, buscando
# as palavras da pergunta no material das outras disciplinas do aluno, e
# errava: no teste piloto, uma pergunta de crânio feita em Anatomia foi
# mandada para Cardiologia porque uma palavra aparecia lá. Caminho errado é
# pior que nenhum: quem escolhe o professor é o aluno.
PROMPT_SISTEMA = """Você é o assistente de estudos da Delta Care, plataforma de ensino de uma faculdade de medicina. Responda SOMENTE com base nos trechos de material fornecidos abaixo, que vieram do material que o professor disponibilizou para esta turma.

Regras:
- Não use nenhum conhecimento externo, mesmo que você saiba a resposta.
- Não deduza. Cada afirmação da resposta precisa estar escrita no material sobre aquele assunto. Se o material diz que um medicamento é usado em certo estágio, e em outro ponto fala de um tipo de tratamento para o mesmo estágio, isso NÃO diz qual é a classe do medicamento — não afirme que ele é daquele tipo.
- A pergunta pode estar coberta por inteiro, em parte ou nada:
  - Por inteiro: responda.
  - Em parte (o material fala do assunto, mas não responde exatamente o que foi perguntado — por exemplo, diz para que um medicamento é usado e em que dose, mas não o que ele é: a classe, o mecanismo): apresente o que o material traz sobre o assunto. Não responda só "o material não cobre": o que ele traz é útil para o aluno.
  - Nada (o material não fala do assunto): diga numa frase que o material disponibilizado não cobre esse ponto, sem acrescentar mais nada ao texto.
- "O que é X?" só tem cobertura completa se o material disser o que X é (a natureza, a classe, a definição). Dizer para que X serve, quando se usa ou em que dose é cobertura parcial.
- No campo "lacuna", escreva em poucas palavras o que a pergunta pede e o material NÃO traz (ex.: para "por que se faz o exame X?", se o material só descreve como fazer: "o motivo do exame"). Deixe vazio se a cobertura for completa. A plataforma mostra a lacuna ao aluno; não a repita dentro da resposta.
- No campo "assunto", escreva só o termo principal da pergunta, em 1 a 3 palavras: o nome do medicamento, da doença, do procedimento ou do conceito, como o material escreve (ex.: "metformina", "escala de Glasgow"). O aspecto perguntado não entra no assunto: para "qual a classe da metformina?", o assunto é "metformina" e "classe" vai na lacuna. Nada sobre quem pergunta nem dado pessoal.
- Não complete lacunas com conhecimento próprio, e não sugira o que o aluno deve fazer em seguida — disso a plataforma cuida.
- Quando ajudar o aluno a se localizar no material, mencione a seção ou o tópico de onde veio a informação (ex.: "na seção de critérios de interrupção").
- Seja didático, claro e objetivo, no nível de um estudante de medicina.
- Responda sempre no formato JSON pedido, com todos os campos — inclusive quando o material não cobrir nada.
- Escreva a resposta no campo "resposta" e, em "fontes_usadas", liste apenas os materiais que você realmente usou. Em "cobertura", diga se o material cobriu a pergunta "completa", em "parcial" ou "nenhuma". Com cobertura "nenhuma", deixe "fontes_usadas" vazio. Não escreva "Fonte:" dentro da resposta — o sistema já mostra as fontes para o aluno.
"""

# O que o modelo diz sobre o quanto o material cobriu a pergunta. É campo do
# schema, e não frase da resposta, porque a plataforma age sobre ele: com
# "parcial" ou "nenhuma" a tela oferece levar a dúvida ao professor — o
# material tem uma lacuna, e quem pode preenchê-la é ele.
COBERTURAS = ("completa", "parcial", "nenhuma")


def montar_schema_resposta(titulos_disponiveis: list) -> dict:
    """Schema que o Ollama impõe ao decodificar a resposta do modelo.

    Isto substitui a instrução de texto que pedia uma linha "FONTES_USADAS:" no
    fim da resposta. A diferença importa: instrução no prompt é pedido, e o
    modelo desobedecia de formas variadas (escrevia **FONTES_USADAS:** em
    negrito, como item de lista, ou reescrevia o título com acento). Com o
    schema, o Ollama restringe os tokens que podem ser gerados — o formato
    deixa de depender de obediência.

    O `enum` em fontes_usadas é a parte mais forte: o modelo só consegue emitir
    um título que exista de verdade entre os materiais recuperados, então não há
    como inventar fonte nem grafar o título diferente.
    """
    schema_fonte = {"type": "string"}

    # enum vazio é inválido em JSON Schema; sem material indexado, a lista fica
    # livre (e o modelo deve devolvê-la vazia de qualquer forma).
    if titulos_disponiveis:
        schema_fonte["enum"] = list(titulos_disponiveis)

    return {
        "type": "object",
        "properties": {
            "resposta": {"type": "string"},
            "fontes_usadas": {"type": "array", "items": schema_fonte},
            "cobertura": {"type": "string", "enum": list(COBERTURAS)},
            "lacuna": {"type": "string"},
            "assunto": {"type": "string"},
        },
        "required": ["resposta", "fontes_usadas", "cobertura", "lacuna", "assunto"],
    }


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


# Quantos trechos vão numa chamada de embedding. Um PDF de aula tem dezenas a
# centenas de trechos; em lote, cada um sai ~30% mais barato que um por
# chamada (medido: 30 ms contra 42 ms por trecho), e o resultado é o mesmo
# vetor. Lote grande demais seguraria a vaga de IA por mais tempo de uma vez.
TAMANHO_LOTE_EMBEDDING = 32


def gerar_embeddings(textos: list) -> list:
    """Um embedding por texto, na mesma ordem, em lotes."""
    vetores = []
    for inicio in range(0, len(textos), TAMANHO_LOTE_EMBEDDING):
        lote = textos[inicio:inicio + TAMANHO_LOTE_EMBEDDING]
        vetores.extend(_chamar_ollama("/api/embed", {"model": MODELO_EMBEDDING, "input": lote})["embeddings"])
    return vetores


def gerar_embedding(texto: str) -> list:
    return gerar_embeddings([texto])[0]


def gerar_resposta_chat(mensagens: list, schema: dict | None = None) -> dict:
    """Pede a resposta ao modelo e devolve {"resposta": str, "fontes_usadas": list}.

    Quando `schema` é informado, o Ollama restringe a geração ao formato — o
    conteúdo volta como JSON garantido, sem precisar de regex para extrair as
    fontes (ver montar_schema_resposta).
    """
    corpo = {
        "model": MODELO_CHAT,
        "messages": mensagens,
        "stream": False,
        "think": ESFORCO_RACIOCINIO,
        "options": {"temperature": 0.2},
    }

    if schema:
        corpo["format"] = schema

    conteudo = _chamar_ollama("/api/chat", corpo)["message"]["content"]

    if not schema:
        return {"resposta": conteudo, "fontes_usadas": None, "cobertura": None, "lacuna": "", "assunto": ""}

    try:
        dados = json.loads(conteudo)
    except json.JSONDecodeError:
        return _resposta_fora_do_formato(conteudo)

    return {
        "resposta": (dados.get("resposta") or "").strip(),
        "fontes_usadas": dados.get("fontes_usadas"),
        "cobertura": dados.get("cobertura"),
        "lacuna": (dados.get("lacuna") or "").strip(),
        "assunto": (dados.get("assunto") or "").strip(),
    }


_CAMPO_SOLTO = re.compile(r"^(resposta|assunto|lacuna|cobertura|fontes_usadas)\s*:\s*(.*)$", re.I)


def _resposta_fora_do_formato(conteudo: str) -> dict:
    """O modelo às vezes ignora o JSON — visto com o gpt-oss nas recusas, que
    vinham como frase solta ou como "**Assunto:** ... **Cobertura:** ...".

    Duas regras, as duas do lado seguro:
    - **nenhuma fonte é atribuída.** Antes, JSON inválido citava tudo que a
      busca trouxe; uma recusa saía com fonte e contava XP. Fonte que o modelo
      não declarou não é fonte.
    - **o aluno nunca vê a lista de campos.** Se veio "Campo: valor", aproveita
      os campos; o texto mostrado é a resposta, ou, se não houver, a frase de
      que o material não cobre.
    """
    campos = {}
    soltas = []
    for linha in conteudo.strip().splitlines():
        limpa = linha.replace("*", "").strip()
        achado = _CAMPO_SOLTO.match(limpa)
        if achado:
            campos[achado.group(1).lower()] = achado.group(2).strip()
        elif limpa:
            soltas.append(limpa)

    cobertura = (campos.get("cobertura") or "").strip(" .").lower()
    resposta = campos.get("resposta") or " ".join(soltas)
    if not resposta:
        resposta = "O material disponibilizado não cobre esse ponto."
    return {
        "resposta": resposta,
        "fontes_usadas": [],
        "cobertura": cobertura if cobertura in COBERTURAS else None,
        "lacuna": campos.get("lacuna", ""),
        "assunto": campos.get("assunto", ""),
    }


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


def indexar_material(material_id: int, gerar_embeddings_fn=gerar_embeddings) -> dict:
    """Extrai o texto do PDF do material, divide em chunks e salva os
    embeddings. Só funciona para materiais do tipo 'pdf' com arquivo salvo.
    Chamar depois que um material PDF é criado ou publicado.

    O mesmo PDF publicado em várias disciplinas é **um arquivo só** (ver
    criar_material_em_turmas). Se ele já foi indexado para outra disciplina,
    os trechos são copiados de lá: o texto e os vetores seriam idênticos, e
    refazer custaria o tempo do modelo outra vez por disciplina.
    """
    conexao = conectar()
    try:
        material = conexao.execute("SELECT tipo, arquivo_caminho FROM materiais WHERE id = ?", (material_id,)).fetchone()
        if not material or material[0] != "pdf" or not material[1]:
            return {"sucesso": False, "mensagem": "Material não é um PDF com arquivo salvo."}
        caminho = material[1]

        irmao = conexao.execute(
            """
            SELECT MIN(m.id) FROM materiais m
             WHERE m.arquivo_caminho = ? AND m.id != ?
               AND EXISTS (SELECT 1 FROM material_chunks c WHERE c.material_id = m.id)
            """,
            (caminho, material_id),
        ).fetchone()[0]
        if irmao:
            conexao.execute("DELETE FROM material_chunks WHERE material_id = ?", (material_id,))
            total = conexao.execute(
                "INSERT INTO material_chunks (material_id, indice, texto, embedding, vetor)"
                " SELECT ?, indice, texto, embedding, vetor FROM material_chunks WHERE material_id = ? ORDER BY indice",
                (material_id, irmao),
            ).rowcount
            conexao.commit()
            return {"sucesso": True, "mensagem": f"{total} trecho(s) reaproveitado(s).", "total_chunks": total}
    finally:
        conexao.close()

    # O trabalho lento — ler o PDF e esperar o modelo — sem conexão aberta. E
    # os vetores antes de apagar os trechos antigos: se o Ollama cair no meio,
    # o material continua com o índice que tinha.
    try:
        texto = extrair_texto_pdf(caminho)
    except Exception as erro:
        return {"sucesso": False, "mensagem": f"Não foi possível ler o PDF: {erro}"}

    chunks = dividir_em_chunks(texto)
    if not chunks:
        return {"sucesso": False, "mensagem": "O PDF não tem texto extraível (pode ser um PDF escaneado sem OCR)."}

    embeddings = gerar_embeddings_fn(chunks)
    if len(embeddings) != len(chunks):
        return {"sucesso": False, "mensagem": "O modelo devolveu um número de vetores diferente do de trechos."}

    conexao = conectar()
    try:
        conexao.execute("DELETE FROM material_chunks WHERE material_id = ?", (material_id,))
        conexao.executemany(
            "INSERT INTO material_chunks (material_id, indice, texto, embedding, vetor) VALUES (?, ?, ?, '', ?)",
            [(material_id, indice, chunk, empacotar(vetor)) for indice, (chunk, vetor) in enumerate(zip(chunks, embeddings))],
        )
        conexao.commit()
    finally:
        conexao.close()

    return {"sucesso": True, "mensagem": f"{len(chunks)} trecho(s) indexado(s).", "total_chunks": len(chunks)}


def reindexar_do_professor(professor_email: str, material_id: int, gerar_embeddings_fn=gerar_embeddings) -> dict:
    """O professor manda indexar de novo um PDF que ficou fora do chat.

    Só o dono do material. É o caminho de volta para quando o assistente
    estava fora do ar na publicação: sem isto, o professor teria de excluir e
    publicar de novo — e perderia acessos, favoritos e anotações dos alunos.
    """
    conexao = conectar()
    try:
        dono = conexao.execute(
            "SELECT m.tipo FROM materiais m JOIN users u ON u.id = m.professor_id WHERE m.id = ? AND u.email = ?",
            (int(material_id), (professor_email or "").strip().lower()),
        ).fetchone()
    finally:
        conexao.close()
    if not dono:
        return {"sucesso": False, "mensagem": "Material não encontrado entre os seus."}
    if dono[0] != "pdf":
        return {"sucesso": False, "mensagem": "Só PDF entra no chat: o assistente não lê vídeo, link nem documento."}
    resultado = indexar_material(int(material_id), gerar_embeddings_fn=gerar_embeddings_fn)
    if resultado["sucesso"]:
        resultado["mensagem"] = f"Pronto: o assistente já responde com este material ({resultado['total_chunks']} trechos)."
    return resultado


# =========================================================================
# Busca por similaridade + geração da resposta
# =========================================================================

# Palavras que aparecem em praticamente todo trecho de material didático e por
# isso não ajudam a distinguir um do outro.
PALAVRAS_COMUNS = {
    "qual", "quais", "como", "quando", "onde", "porque", "para", "pela", "pelo",
    "que", "sao", "esta", "este", "essa", "esse", "dos", "das", "com", "sem",
    "disciplina", "material", "protocolo", "adotada", "adotado", "sobre",
    "paciente", "clinico", "clinica", "aula", "conteudo", "seguinte",
}


def _normalizar_para_busca(texto: str) -> str:
    """Minúsculas e sem acento, para casar 'Crânio' com 'cranio'."""
    sem_acento = "".join(
        letra for letra in unicodedata.normalize("NFD", texto)
        if unicodedata.category(letra) != "Mn"
    )
    return sem_acento.casefold()


def _termos_distintivos(pergunta: str) -> list:
    """Termos da pergunta que valem para busca literal.

    Ficam de fora as palavras comuns; sobram siglas, códigos, números e
    palavras longas — justamente o que costuma identificar um assunto
    específico ("CHA2DS2-VASc", "NT-proBNP", "Takotsubo", "0,05").
    """
    candidatos = re.findall(r"[a-z0-9][a-z0-9\-,\.]{2,}", _normalizar_para_busca(pergunta))

    return [
        termo for termo in candidatos
        if termo not in PALAVRAS_COMUNS
        and (any(c.isdigit() for c in termo) or "-" in termo or len(termo) > 4)
    ]


def _pontuar_trecho(texto: str, similaridade: float, termos: list) -> float:
    """Combina similaridade semântica com correspondência literal de termos.

    Por que não usar só o cosseno: um trecho de 800 caracteres em que apenas
    80 respondem à pergunta tem o embedding dominado pelos outros 720, que
    costumam ser texto genérico. Medindo numa apostila de 18 trechos, o trecho
    que definia o "escore ARR-7" caía para a 7ª posição por similaridade pura —
    atrás de trechos que não respondiam nada — e o modelo respondia que o
    material não cobria o assunto. Com o bônus literal ele vai para a 1ª, e
    nenhuma das outras perguntas testadas piorou.

    O bônus é pequeno de propósito: ele desempata dentro de um conjunto já
    semanticamente próximo, em vez de transformar a busca em "procurar palavra".
    """
    if not termos:
        return similaridade

    alvo = _normalizar_para_busca(texto)
    encontrados = sum(1 for termo in termos if termo in alvo)

    return similaridade + PESO_BUSCA_LITERAL * (encontrados / len(termos))


def _status_material(rascunho: int, data_liberacao) -> str:
    """Mesma regra de regras/materiais._calcular_status, reaplicada aqui
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

    Custo, medido com vetores de 768 dimensões: a busca percorre todos os
    trechos da disciplina a cada pergunta. Com o vetor em JSON e o bônus
    literal calculado para todos, eram 0,28 ms por trecho — 0,8 s numa
    disciplina com 30 PDFs, 2,8 s com 100. Ver infra/vetores.py e o corte
    abaixo.
    """
    pergunta_vetor = normalizar(gerar_embedding_fn(pergunta))
    termos = _termos_distintivos(pergunta)

    conexao = conectar()
    try:
        linhas = conexao.execute(
            '''
            SELECT c.texto, c.vetor, c.embedding, m.titulo, m.id, m.rascunho, m.data_liberacao
            FROM material_chunks c
            JOIN materiais m ON m.id = c.material_id
            WHERE m.turma_id = ? AND m.rascunho = 0
            ''',
            (turma_id,),
        ).fetchall()
    finally:
        conexao.close()

    candidatos = []
    for texto, vetor, embedding_json, titulo_material, material_id, rascunho, data_liberacao in linhas:
        # O rascunho já saiu no SQL. O agendado fica aqui de propósito: a regra
        # trata data sem fuso e data malformada, e o SQLite compararia as duas
        # como texto — seria trocar 30ms por um material aparecendo antes da
        # hora.
        if _status_material(rascunho, data_liberacao) != "publicado":
            continue
        # Vetor ainda em JSON: trecho gravado antes da coluna binária, que o
        # banco converte ao subir (infra/database.py).
        trecho = desempacotar(vetor) if vetor else normalizar(json.loads(embedding_json))
        # Os dois vetores têm norma 1: o produto escalar já é o cosseno.
        similaridade = sum(map(operator.mul, pergunta_vetor, trecho))
        candidatos.append((similaridade, texto, titulo_material, material_id))

    # O bônus literal (_pontuar_trecho) soma no máximo PESO_BUSCA_LITERAL.
    # Então um trecho com similaridade abaixo da k-ésima melhor menos esse
    # peso não alcança o top-k nem com o bônus inteiro: sai antes, sem pagar a
    # normalização do texto, que era o segundo maior custo da busca. O
    # resultado é o mesmo de pontuar todos (há teste comparando os dois).
    if len(candidatos) > top_k:
        folga = PESO_BUSCA_LITERAL if termos else 0.0
        corte = heapq.nlargest(top_k, (c[0] for c in candidatos))[-1] - folga
        candidatos = [c for c in candidatos if c[0] >= corte]

    pontuados = [
        {
            "texto": texto,
            "pontuacao": _pontuar_trecho(texto, similaridade, termos),
            "similaridade": similaridade,
            "material": titulo_material,
            "material_id": material_id,
        }
        for similaridade, texto, titulo_material, material_id in candidatos
    ]
    pontuados.sort(key=lambda c: c["pontuacao"], reverse=True)
    return pontuados[:top_k]


def montar_contexto(trechos: list) -> str:
    if not trechos:
        return "(Nenhum trecho de material relevante foi encontrado para esta turma.)"
    partes = [f"[Material: {t['material']}]\n{t['texto']}" for t in trechos]
    return "\n\n---\n\n".join(partes)


def _salvar_mensagem(aluno_id: int, turma_id: int, papel: str, conteudo: str, fontes: list = None,
                     lacuna: str = "", cobertura: str = None, assunto: str = "") -> None:
    conexao = conectar()
    agora = datetime.now(timezone.utc).isoformat()
    cursor = conexao.cursor()
    cursor.execute(
        "INSERT INTO chat_mensagens (aluno_id, turma_id, papel, conteudo, fontes, lacuna, cobertura, assunto, criado_em)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (aluno_id, turma_id, papel, conteudo, json.dumps(fontes) if fontes else None, lacuna or None,
         cobertura, (assunto or "")[:80] or None, agora),
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
    from regras.matriculas import aluno_matriculado_na_turma

    pergunta = pergunta.strip()
    if not pergunta:
        return {"sucesso": False, "mensagem": "Digite uma pergunta."}

    if not aluno_matriculado_na_turma(aluno_email, turma_id):
        return {"sucesso": False, "mensagem": "Você não está matriculado nessa turma."}

    conexao = conectar()
    aluno = buscar_usuario(conexao, aluno_email)
    conexao.close()

    # A IA roda num serviço separado (Ollama). Se ele estiver fora do ar, o
    # aluno recebe uma mensagem clara em vez de um erro 500 — e a pergunta
    # dele não é perdida do histórico por causa disso.
    try:
        trechos = buscar_trechos_relevantes(turma_id, pergunta, gerar_embedding_fn=gerar_embedding_fn)

        # Disciplina sem nenhum texto que o assistente leia (só links e vídeos,
        # ou nada publicado): não há o que perguntar ao modelo. Chamá-lo
        # custava 10 a 20 segundos para ouvir "não cobre" — e escondia o
        # motivo real, que é outro.
        if not trechos:
            return _sem_material_legivel(aluno[0], turma_id, pergunta)

        contexto = montar_contexto(trechos)
        materiais_recuperados = sorted({t["material"] for t in trechos})

        mensagens = [
            {"role": "system", "content": PROMPT_SISTEMA},
            {"role": "user", "content": f"Material disponível:\n\n{contexto}\n\nPergunta do aluno: {pergunta}"},
        ]

        resultado_modelo = gerar_resposta_fn(mensagens, montar_schema_resposta(materiais_recuperados))
    except RuntimeError as erro:
        return {
            "sucesso": False,
            "mensagem": "O assistente de IA está indisponível no momento. Tente de novo em instantes.",
            "detalhe": str(erro),
        }

    resposta_texto = resultado_modelo["resposta"]
    fontes_declaradas = resultado_modelo["fontes_usadas"]

    # O schema restringe as fontes aos títulos reais. `None` só vem de um
    # modelo chamado sem schema (testes antigos): aí cita o que a busca trouxe.
    # Resposta fora do formato chega com lista vazia — ver
    # _resposta_fora_do_formato.
    fontes = materiais_recuperados if fontes_declaradas is None else sorted(set(fontes_declaradas))

    # Cobertura fora do formato (resposta de um modelo sem schema) é deduzida
    # das fontes, como era antes do campo existir.
    cobertura = resultado_modelo.get("cobertura")
    lacuna = resultado_modelo.get("lacuna") or ""
    if cobertura not in COBERTURAS:
        cobertura = "completa" if fontes else "nenhuma"
    if cobertura == "nenhuma":
        # "Não cobre" citando fonte seria contradição — e a fonte é o que faz a
        # pergunta contar XP (regras/aluno.py).
        fontes = []

    _salvar_mensagem(aluno[0], turma_id, "user", pergunta)
    # A lacuna é gravada: ela não está no texto da resposta, e sem ela uma
    # resposta parcial, relida amanhã no histórico, pareceria completa. Grava
    # também na cobertura "nenhuma": para o aluno é redundante ("não cobre"),
    # mas para o professor é o que falta (regras/lacunas.py).
    lacuna = lacuna if cobertura in ("parcial", "nenhuma") else ""
    _salvar_mensagem(aluno[0], turma_id, "assistant", resposta_texto, fontes=fontes, lacuna=lacuna,
                     cobertura=cobertura, assunto=resultado_modelo.get("assunto") or "")

    resultado = {
        "sucesso": True,
        "resposta": resposta_texto,
        "fontes": fontes,
        "cobertura": cobertura,
        # Na tela do aluno, a lacuna só aparece na resposta parcial.
        "lacuna": lacuna if cobertura == "parcial" else "",
    }
    return resultado


def _sem_material_legivel(aluno_id: int, turma_id: int, pergunta: str) -> dict:
    conexao = conectar()
    nome = conexao.execute("SELECT nome FROM turmas WHERE id = ?", (int(turma_id),)).fetchone()[0]
    conexao.close()

    resposta = (
        f"O material de {nome} ainda não tem nenhum texto que eu consiga ler: "
        "respondo a partir dos PDFs que o professor publica, e esta disciplina "
        "ainda não tem nenhum (links e vídeos eu não leio)."
    )
    _salvar_mensagem(aluno_id, turma_id, "user", pergunta)
    # "sem_material", e não "nenhuma": para o professor é outro recado — não
    # é um tema que falta, é a disciplina que não tem nada que o assistente leia.
    _salvar_mensagem(aluno_id, turma_id, "assistant", resposta, fontes=[], cobertura="sem_material")
    return {
        "sucesso": True,
        "resposta": resposta,
        "fontes": [],
        "cobertura": "nenhuma",
        "lacuna": "",
    }


def buscar_historico(aluno_email: str, turma_id: int) -> dict:
    conexao = conectar()
    aluno = buscar_usuario(conexao, aluno_email)

    if not aluno:
        conexao.close()
        return {"sucesso": False, "mensagem": "Aluno não encontrado.", "mensagens": []}

    cursor = conexao.cursor()
    cursor.execute(
        '''
        SELECT papel, conteudo, fontes, lacuna, cobertura, criado_em FROM chat_mensagens
        WHERE aluno_id = ? AND turma_id = ? AND apagada_em IS NULL
        ORDER BY criado_em
        ''',
        (aluno[0], turma_id),
    )
    mensagens = [
        {"papel": p, "conteudo": c, "fontes": json.loads(f) if f else [],
         "lacuna": (l or "") if cob == "parcial" else "", "criado_em": e}
        for p, c, f, l, cob, e in cursor.fetchall()
    ]
    conexao.close()

    return {"sucesso": True, "mensagens": mensagens}


# Marca das fontes de uma resposta apagada: só diz que havia fonte (a pergunta
# pontuou no XP), sem dizer qual material nem qual trecho.
FONTES_APAGADAS = '["apagada"]'


def apagar_historico(aluno_email: str, turma_id: int) -> dict:
    """O aluno apaga a conversa com o assistente numa disciplina.

    Some de verdade o que ele escreveu e o que o assistente respondeu: texto,
    fontes citadas e o "o que falta" da resposta. Fica a contagem, sem
    conteúdo: o dia, se o material respondeu e o assunto em poucas palavras —
    o mesmo que o professor já via nas lacunas, sem nome e só com 2+ alunos.
    Assim o XP e a sequência de dias do aluno não mudam, apagar e perguntar de
    novo não pontua duas vezes (fica o hash da pergunta, ver
    aluno.chave_da_pergunta) e os relatórios de meses fechados não mudam.

    Quem quer que nem isso fique pede a exclusão da conta (privacidade.py).
    """
    from regras.aluno import chave_da_pergunta

    conexao = conectar()
    try:
        aluno = buscar_usuario(conexao, aluno_email)
        if not aluno or aluno[1] != "aluno":
            return {"sucesso": False, "mensagem": "Aluno não encontrado."}
        agora = datetime.now(timezone.utc).isoformat()
        perguntas = conexao.execute(
            "SELECT id, conteudo FROM chat_mensagens"
            " WHERE aluno_id = ? AND turma_id = ? AND papel = 'user' AND apagada_em IS NULL",
            (aluno[0], turma_id),
        ).fetchall()
        conexao.executemany(
            "UPDATE chat_mensagens SET chave = ? WHERE id = ?",
            [(chave_da_pergunta(conteudo), id_mensagem) for id_mensagem, conteudo in perguntas],
        )
        apagadas = conexao.execute(
            """
            UPDATE chat_mensagens
               SET conteudo = '', lacuna = NULL, apagada_em = ?,
                   fontes = CASE WHEN fontes IS NULL OR trim(fontes) IN ('', '[]') THEN fontes ELSE ? END
             WHERE aluno_id = ? AND turma_id = ? AND apagada_em IS NULL
            """,
            (agora, FONTES_APAGADAS, aluno[0], turma_id),
        ).rowcount
        conexao.commit()
    finally:
        conexao.close()

    if not apagadas:
        return {"sucesso": True, "apagadas": 0, "mensagem": "Não havia conversa para apagar."}
    return {"sucesso": True, "apagadas": apagadas, "mensagem": "Conversa apagada."}
