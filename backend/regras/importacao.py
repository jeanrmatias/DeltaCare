"""Importação de alunos em massa, a partir de planilha.

Cadastrar uma turma inteira um a um é o tipo de trabalho que faz a
administração desistir da ferramenta. Aqui a secretaria envia a planilha que
ela já tem e o sistema devolve um relatório do que entrou e do que foi
rejeitado, linha a linha.

Formatos: CSV e XLSX. **Sem dependência nova**: o `.xlsx` é um ZIP com XML
dentro, e `zipfile` + `ElementTree` são da biblioteca padrão. Trazer o
openpyxl ou o pandas para ler três colunas seria desproporcional — o projeto
já escreve o próprio PDF e o próprio hash de senha pelo mesmo motivo.

PDF ficou de fora: o texto de um PDF não tem estrutura de tabela, e adivinhar
colunas a partir de posição no papel erra em silêncio. Um erro silencioso num
cadastro acadêmico é pior do que pedir a planilha.
"""

import base64
import csv
import io
import re
import zipfile
from xml.etree import ElementTree

# Nomes aceitos para cada coluna. A secretaria não deveria ter que renomear o
# cabeçalho da planilha para o nosso padrão.
COLUNAS = {
    "nome": {"nome", "nome completo", "aluno", "estudante", "nome do aluno"},
    "email": {"email", "e-mail", "e mail", "correio", "email institucional"},
    "matricula": {"matricula", "matrícula", "ra", "registro", "registro academico",
                  "registro acadêmico", "numero de matricula"},
}

LIMITE_LINHAS = 500

NAMESPACE_XLSX = {"n": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def _normalizar_cabecalho(texto: str) -> str:
    texto = (texto or "").strip().lower()
    # Remove acento de forma simples: só precisamos casar com a lista acima.
    for de, para in (("á", "a"), ("â", "a"), ("ã", "a"), ("é", "e"), ("ê", "e"),
                     ("í", "i"), ("ó", "o"), ("ô", "o"), ("õ", "o"), ("ú", "u"), ("ç", "c")):
        texto = texto.replace(de, para)
    return re.sub(r"\s+", " ", texto)


def _mapear_colunas(cabecalho: list) -> dict:
    """Descobre em qual posição está cada campo conhecido."""
    posicoes = {}

    for indice, titulo in enumerate(cabecalho):
        normalizado = _normalizar_cabecalho(titulo)
        for campo, aceitos in COLUNAS.items():
            if normalizado in aceitos and campo not in posicoes:
                posicoes[campo] = indice

    return posicoes


def _ler_csv(conteudo: bytes) -> list:
    # A planilha pode vir do Excel brasileiro (cp1252) ou de exportação web.
    for codificacao in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            texto = conteudo.decode(codificacao)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("Não foi possível ler o arquivo: codificação desconhecida.")

    # Excel brasileiro salva CSV com ponto e vírgula; o resto do mundo, vírgula.
    amostra = texto[:2000]
    separador = ";" if amostra.count(";") > amostra.count(",") else ","

    return [linha for linha in csv.reader(io.StringIO(texto), delimiter=separador)]


def _ler_xlsx(conteudo: bytes) -> list:
    """Lê a primeira aba de um .xlsx usando só a biblioteca padrão."""
    with zipfile.ZipFile(io.BytesIO(conteudo)) as arquivo:
        # Textos ficam numa tabela compartilhada; as células só guardam o índice.
        compartilhados = []
        if "xl/sharedStrings.xml" in arquivo.namelist():
            raiz = ElementTree.fromstring(arquivo.read("xl/sharedStrings.xml"))
            for item in raiz.findall("n:si", NAMESPACE_XLSX):
                # O texto pode estar quebrado em vários <t> quando há formatação.
                partes = [no.text or "" for no in item.iter(f"{{{NAMESPACE_XLSX['n']}}}t")]
                compartilhados.append("".join(partes))

        nome_aba = next(
            (n for n in arquivo.namelist() if n.startswith("xl/worksheets/sheet")), None
        )
        if not nome_aba:
            raise ValueError("A planilha não tem nenhuma aba legível.")

        raiz = ElementTree.fromstring(arquivo.read(nome_aba))

        linhas = []
        for linha in raiz.iter(f"{{{NAMESPACE_XLSX['n']}}}row"):
            valores = []
            for celula in linha.findall("n:c", NAMESPACE_XLSX):
                valor = celula.find("n:v", NAMESPACE_XLSX)
                texto = valor.text if valor is not None else ""

                if celula.get("t") == "s" and texto:
                    indice = int(texto)
                    texto = compartilhados[indice] if indice < len(compartilhados) else ""
                elif celula.get("t") == "inlineStr":
                    inline = celula.find("n:is/n:t", NAMESPACE_XLSX)
                    texto = inline.text if inline is not None else ""

                valores.append(texto or "")
            linhas.append(valores)

        return linhas


def _parece_email(valor: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", valor or ""))


def analisar_planilha(arquivo_base64: str, nome_arquivo: str) -> dict:
    """Lê a planilha e devolve as linhas válidas e as rejeitadas, sem gravar.

    Separado da importação de propósito: o admin vê o que vai acontecer antes
    de acontecer, e uma planilha com metade das linhas erradas não cria
    metade das contas.
    """
    extensao = (nome_arquivo or "").lower().rsplit(".", 1)[-1]

    try:
        conteudo = base64.b64decode(arquivo_base64)
    except Exception:
        return {"sucesso": False, "mensagem": "Arquivo inválido."}

    try:
        if extensao == "csv":
            linhas = _ler_csv(conteudo)
        elif extensao in ("xlsx", "xlsm"):
            linhas = _ler_xlsx(conteudo)
        else:
            return {
                "sucesso": False,
                "mensagem": "Formato não suportado. Envie um arquivo .csv ou .xlsx.",
            }
    except Exception as erro:
        return {"sucesso": False, "mensagem": f"Não foi possível ler a planilha: {erro}"}

    linhas = [linha for linha in linhas if any((celula or "").strip() for celula in linha)]

    if not linhas:
        return {"sucesso": False, "mensagem": "A planilha está vazia."}

    posicoes = _mapear_colunas(linhas[0])

    faltando = [campo for campo in ("nome", "email") if campo not in posicoes]
    if faltando:
        return {
            "sucesso": False,
            "mensagem": (
                "A planilha precisa ter as colunas "
                + " e ".join(f'"{c}"' for c in faltando)
                + ". Cabeçalho encontrado: "
                + ", ".join(str(c) for c in linhas[0] if str(c).strip())
            ),
        }

    validos = []
    rejeitados = []
    emails_vistos = set()

    for numero, linha in enumerate(linhas[1:], start=2):
        if numero - 1 > LIMITE_LINHAS:
            rejeitados.append({"linha": numero, "motivo": f"Acima do limite de {LIMITE_LINHAS} linhas por envio."})
            break

        def valor(campo):
            indice = posicoes.get(campo)
            if indice is None or indice >= len(linha):
                return ""
            return str(linha[indice] or "").strip()

        nome = valor("nome")
        email = valor("email").lower()
        matricula = valor("matricula")

        if not nome:
            rejeitados.append({"linha": numero, "motivo": "Nome vazio.", "email": email})
            continue

        if not _parece_email(email):
            rejeitados.append({"linha": numero, "motivo": f'E-mail inválido: "{email}".', "nome": nome})
            continue

        if email in emails_vistos:
            rejeitados.append({"linha": numero, "motivo": "E-mail repetido na própria planilha.", "email": email})
            continue

        emails_vistos.add(email)
        validos.append({"linha": numero, "nome": nome, "email": email, "matricula": matricula})

    return {
        "sucesso": True,
        "validos": validos,
        "rejeitados": rejeitados,
        "total_linhas": len(linhas) - 1,
        "colunas_encontradas": sorted(posicoes.keys()),
    }


def importar_alunos(admin_email: str, arquivo_base64: str, nome_arquivo: str,
                    turma_id: int | None = None, senha_padrao: str = "") -> dict:
    """Cria as contas da planilha. Linhas inválidas são puladas, não abortam.

    A senha é a mesma para todos e provisória: a alternativa seria gerar uma
    por aluno e a secretaria teria que distribuir 60 senhas diferentes. O
    fluxo esperado é o aluno trocar no primeiro acesso.
    """
    from regras.autenticacao import criar_conta_staff

    if len(senha_padrao) < 6:
        return {"sucesso": False, "mensagem": "A senha provisória precisa ter pelo menos 6 caracteres."}

    analise = analisar_planilha(arquivo_base64, nome_arquivo)

    if not analise.get("sucesso"):
        return analise

    criados = []
    falhas = list(analise["rejeitados"])

    for registro in analise["validos"]:
        resultado = criar_conta_staff(
            admin_email,
            registro["email"],
            senha_padrao,
            "aluno",
            nome=registro["nome"],
            matricula=registro["matricula"],
            turma_id=turma_id,
        )

        if resultado.get("sucesso"):
            criados.append(registro["email"])
        else:
            falhas.append({
                "linha": registro["linha"],
                "email": registro["email"],
                "motivo": resultado.get("mensagem", "Erro desconhecido."),
            })

    return {
        "sucesso": True,
        "mensagem": f"{len(criados)} aluno(s) importado(s). {len(falhas)} linha(s) rejeitada(s).",
        "criados": criados,
        "rejeitados": falhas,
        "total_criados": len(criados),
        "total_rejeitados": len(falhas),
    }
