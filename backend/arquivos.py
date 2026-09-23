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

PASTA_UPLOADS = os.path.join("uploads", "materiais")
TAMANHO_MAXIMO_MB = 15
TAMANHO_MAXIMO_BYTES = TAMANHO_MAXIMO_MB * 1024 * 1024

EXTENSOES_PERMITIDAS = {
    "pdf": {".pdf"},
    "documento": {".pdf", ".doc", ".docx", ".txt", ".odt"},
    "video": {".mp4", ".mov", ".webm", ".mkv"},
}


def extensao_valida(tipo: str, nome_arquivo: str) -> bool:
    _, extensao = os.path.splitext(nome_arquivo.lower())
    return extensao in EXTENSOES_PERMITIDAS.get(tipo, set())


def salvar_arquivo_base64(conteudo_base64: str, nome_original: str, tipo: str) -> dict:
    """Decodifica e salva o arquivo. Retorna {sucesso, mensagem, caminho}."""

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

    os.makedirs(PASTA_UPLOADS, exist_ok=True)

    _, extensao = os.path.splitext(nome_original)
    nome_no_disco = f"{uuid.uuid4().hex}{extensao.lower()}"
    caminho = os.path.join(PASTA_UPLOADS, nome_no_disco)

    with open(caminho, "wb") as arquivo:
        arquivo.write(dados)

    return {"sucesso": True, "mensagem": "Arquivo salvo.", "caminho": caminho}


def remover_arquivo(caminho: str) -> None:
    if caminho and os.path.isfile(caminho):
        try:
            os.remove(caminho)
        except OSError:
            pass
