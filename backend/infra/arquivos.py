"""Salva os arquivos de materiais enviados em base64 no disco local.

Sem servidor de arquivos (S3 etc.) configurado ainda, os arquivos ficam
salvos dentro da própria pasta do backend, em uploads/materiais/. O envio
é feito em base64 dentro do JSON (em vez de multipart/form-data) para não
depender do pacote python-multipart.
"""

import base64
import binascii
import os
import uuid

# Raiz dos arquivos enviados. DELTACARE_UPLOADS existe pelo mesmo motivo que
# DELTACARE_DB: os testes precisam de uma pasta só deles. Antes a raiz era
# fixa em "uploads", relativa à pasta de onde o processo rodava — e a suíte,
# rodando de backend/, apagava no teardown a mesma uploads/entregas em que o
# servidor de desenvolvimento grava o trabalho dos alunos.
RAIZ_UPLOADS = os.environ.get("DELTACARE_UPLOADS", "uploads")
PASTA_UPLOADS = os.path.join(RAIZ_UPLOADS, "materiais")
PASTA_ENTREGAS = os.path.join(RAIZ_UPLOADS, "entregas")
TAMANHO_MAXIMO_MB = 15
TAMANHO_MAXIMO_BYTES = TAMANHO_MAXIMO_MB * 1024 * 1024

EXTENSOES_PERMITIDAS = {
    "pdf": {".pdf"},
    "documento": {".pdf", ".doc", ".docx", ".txt", ".odt"},
    "video": {".mp4", ".mov", ".webm", ".mkv"},
    # Entrega de aluno. Mais largo que "documento" porque em medicina o
    # trabalho pode ser a foto de uma peça anatômica, um traçado de ECG
    # digitalizado ou a planilha de um estudo — e recusar isso obrigaria o
    # aluno a converter tudo para PDF antes de entregar.
    "entrega": {
        ".pdf", ".doc", ".docx", ".odt", ".txt", ".rtf",
        ".png", ".jpg", ".jpeg", ".webp",
        ".xlsx", ".csv", ".ppt", ".pptx", ".odp",
    },
}


def extensao_valida(tipo: str, nome_arquivo: str) -> bool:
    _, extensao = os.path.splitext(nome_arquivo.lower())
    return extensao in EXTENSOES_PERMITIDAS.get(tipo, set())


def salvar_arquivo_base64(
    conteudo_base64: str, nome_original: str, tipo: str, pasta: str = PASTA_UPLOADS
) -> dict:
    """Decodifica e salva o arquivo. Retorna {sucesso, mensagem, caminho}.

    `pasta` separa material de entrega no disco. Não é segurança — quem
    autoriza o download é a regra de negócio, nunca o caminho — mas um
    diretório só com trabalho de aluno é o que torna possível dar backup,
    expurgar por semestre ou responder a um pedido de exclusão de dados sem
    varrer o resto.
    """

    if not extensao_valida(tipo, nome_original):
        extensoes = ", ".join(sorted(EXTENSOES_PERMITIDAS.get(tipo, [])))
        return {
            "sucesso": False,
            "mensagem": f"Formato não permitido para '{tipo}'. Use: {extensoes}.",
        }

    # O front pode mandar como data URL (data:<mime>;base64,<dados>) ou só o base64 puro.
    if "," in conteudo_base64 and conteudo_base64.strip().startswith("data:"):
        conteudo_base64 = conteudo_base64.split(",", 1)[1]

    try:
        dados = base64.b64decode(conteudo_base64, validate=True)
    except (binascii.Error, ValueError):
        return {"sucesso": False, "mensagem": "Arquivo inválido ou corrompido."}

    if len(dados) > TAMANHO_MAXIMO_BYTES:
        return {"sucesso": False, "mensagem": f"O arquivo passa do limite de {TAMANHO_MAXIMO_MB}MB."}

    if len(dados) == 0:
        return {"sucesso": False, "mensagem": "O arquivo está vazio."}

    os.makedirs(pasta, exist_ok=True)

    # O nome no disco é um uuid, e não o que o aluno mandou: nome de arquivo
    # vindo do cliente carrega "../", caractere de caminho e colisão entre dois
    # alunos que chamaram o trabalho de "relatorio.pdf". O nome original volta
    # para a pessoa na hora do download, guardado à parte no banco.
    _, extensao = os.path.splitext(nome_original)
    nome_no_disco = f"{uuid.uuid4().hex}{extensao.lower()}"
    caminho = os.path.join(pasta, nome_no_disco)

    with open(caminho, "wb") as arquivo:
        arquivo.write(dados)

    return {"sucesso": True, "mensagem": "Arquivo salvo.", "caminho": caminho}


def remover_arquivo(caminho: str) -> None:
    if caminho and os.path.isfile(caminho):
        try:
            os.remove(caminho)
        except OSError:
            pass
