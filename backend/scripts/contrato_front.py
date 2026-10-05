"""Confere se o front (React, em frontend/) e o back falam a mesma língua.

A quebra que nenhum teste de regra pega, porque cada lado está certo sozinho:
**o front chama uma rota que não existe**, ou com o verbo errado. O back
renomeia `/admin/coortes/excecoes` para `/admin/excecoes`, esquece de mudar
uma tela, e ela passa a responder 404/405 — só no navegador. E o contrário:
rota que nenhuma tela chama mais.

Leitura estática do código, sem navegador: pega o que dá para pegar sem
executar. Usado pelos testes (backend/testes/testes.py) e pode ser rodado
sozinho, de dentro de backend/:

    python scripts/contrato_front.py
"""

import glob
import os
import re

# backend/scripts/contrato_front.py → a raiz do projeto fica três níveis acima.
RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FRONT = os.path.join(RAIZ, "frontend", "src")

_LITERAL = re.compile(r"([`\"'])(/[^`\"']*)\1")
_METODO = re.compile(r"method:\s*([^,}\n]+)")


def _sem_comentarios(texto: str) -> str:
    """O JS sem comentários de bloco nem linhas só de comentário.

    Comentário não é código: `api("/x")` citado num comentário não pode contar
    como chamada — nem para acusar rota inexistente, nem para esconder uma
    rota órfã atrás de uma chamada comentada. Troca cada comentário por
    quebras de linha, para a numeração das mensagens continuar certa.

    Comentário no fim de uma linha de código fica: separar `//` de comentário
    de `//` dentro de uma URL exigiria interpretar o JS.
    """
    def em_branco(achado):
        return "\n" * achado.group(0).count("\n")

    texto = re.sub(r"/\*.*?\*/", em_branco, texto, flags=re.S)
    return re.sub(r"(?m)^[ \t]*//.*$", "", texto)


def _arquivos_front():
    for padrao in ("*.js", "*.jsx"):
        for caminho in sorted(glob.glob(os.path.join(FRONT, "**", padrao), recursive=True)):
            if not caminho.endswith(".test.js"):
                yield caminho


# O caminho da API aparece também fora de api(): no hook useApi, no download
# (baixarArquivo) e na prop `caminho` do visualizador — todos GET.
_USO_GET = re.compile(r"\b(?:useApi|baixarArquivo)\(|\bcaminho=\{")


def _argumento(texto: str, inicio: int) -> str:
    """O que vai do parêntese (ou chave) aberto em `inicio - 1` até o que o fecha."""
    abre = texto[inicio - 1]
    fecha = {"(": ")", "{": "}"}[abre]
    profundidade = 1
    for posicao in range(inicio, len(texto)):
        if texto[posicao] == abre:
            profundidade += 1
        elif texto[posicao] == fecha:
            profundidade -= 1
            if profundidade == 0:
                return texto[inicio:posicao]
    return ""


def _caminhos_literais(trecho: str) -> list:
    """Os caminhos (`/...`) escritos num trecho. Num template com condição
    (`/aluno/ranking${x ? ... : ""}`), o `${` sem fechar é a consulta: sai."""
    caminhos = []
    for achado in re.finditer(r"([`\"'])(/[^`\"']*)", trecho):
        caminho = re.sub(r"\$\{[^}]*$", "", achado.group(2))
        if len(caminho) > 1:
            caminhos.append(caminho)
    return caminhos


def chamadas_do_front() -> list:
    """(arquivo, linha, verbo, caminho no fonte, caminho concreto) das telas."""
    resultado = []
    for arquivo in _arquivos_front():
        texto = _sem_comentarios(open(arquivo, encoding="utf-8").read())
        relativo = os.path.relpath(arquivo, RAIZ)

        def linha(posicao):
            return texto.count("\n", 0, posicao) + 1

        # Atalhos da própria tela que só repassam para `api` — como o
        # `chamar(caminho, opcoes)` da tela de Turmas — contam como `api`.
        # Sem isto, as chamadas feitas por eles não passavam pelo contrato.
        atalhos = [
            nome for nome, caminho, opcoes in re.findall(r"function (\w+)\((\w+)\s*,\s*(\w+)\)", texto)
            if re.search(rf"\bapi\(\s*{caminho}\s*,\s*{opcoes}\s*\)", texto)
        ]
        nomes = "|".join(["api", "apiPublica", *atalhos])
        for achado in re.finditer(rf"\b({nomes})\(", texto):
            argumentos = _argumento(texto, achado.end())
            primeiro = re.match(r"\s*([`\"'])(.*?)\1", argumentos, re.S)
            if not primeiro:
                continue
            # apiPublica é sempre POST (login, recuperação); api lê o `method`.
            metodos = ["POST"] if achado.group(1) == "apiPublica" else _metodos(argumentos)
            for concreto in _normalizar(primeiro.group(2), texto):
                for metodo in metodos:
                    resultado.append((relativo, linha(achado.start()), metodo, primeiro.group(2), concreto))

        for achado in _USO_GET.finditer(texto):
            argumento = _argumento(texto, achado.end())
            # `useApi(caminho)`: o caminho está na definição da variável.
            variavel = re.fullmatch(r"\s*([A-Za-z_]\w*)\s*", argumento)
            if variavel:
                # A última definição antes do uso: dois componentes no mesmo
                # arquivo podem ter cada um o seu `caminho`.
                definicoes = list(re.finditer(rf"\bconst {variavel.group(1)}\s*=\s*(.+)", texto[:achado.start()]))
                argumento = definicoes[-1].group(1) if definicoes else ""
            for fonte in _caminhos_literais(argumento):
                for concreto in _normalizar(fonte, texto):
                    resultado.append((relativo, linha(achado.start()), "GET", fonte, concreto))

    return resultado


def _definicao(texto: str, nome: str) -> str:
    """O trecho `const nome = ...;`, para resolver caminho guardado em constante."""
    definicao = re.search(rf"\b(?:const|let)\s+{nome}\s*=\s*(.*?);", texto, re.S)
    return definicao.group(1) if definicao else ""


def _normalizar(caminho: str, texto: str) -> list:
    """Transforma o caminho do fonte em caminhos concretos para casar com as rotas.

    - `${CONSTANTE}` no começo vira cada caminho literal da definição dela;
    - `${x}` ocupando um segmento inteiro (`/materiais/${id}/arquivo`) vira
      um valor qualquer;
    - `${x}` grudado no fim de um segmento (`/aluno/ranking${consulta}`) é
      query string montada à parte, e sai.
    """
    inicio = re.match(r"\$\{(\w+)\}", caminho)
    if inicio:
        resto = caminho[inicio.end():]
        bases = [m.group(2) for m in _LITERAL.finditer(_definicao(texto, inicio.group(1)))]
        return [c for base in bases for c in _normalizar(base + resto, texto)]

    caminho = caminho.split("?")[0]
    caminho = re.sub(r"(?<=[^/])\$\{[^}]+\}", "", caminho)
    caminho = re.sub(r"\$\{[^}]+\}", "X", caminho)
    return [caminho] if caminho.startswith("/") else []


def _metodos(opcoes: str) -> list:
    achado = _METODO.search(opcoes or "")
    if not achado:
        return ["GET"]
    # Ternário (`estaFora ? "DELETE" : "POST"`) vale pelos dois lados.
    return [m.upper() for m in re.findall(r"[\"'](\w+)[\"']", achado.group(1))] or ["GET"]


def rotas_do_back(app) -> list:
    """(verbo, caminho declarado, regex que casa o caminho concreto)."""
    rotas = []
    for rota in app.routes:
        for metodo in getattr(rota, "methods", None) or ():
            if metodo in ("HEAD", "OPTIONS"):
                continue
            padrao = "^" + re.sub(r"\{[^}]+\}", "[^/]+", rota.path) + "$"
            rotas.append((metodo, rota.path, re.compile(padrao)))
    return rotas


def chamadas_sem_rota(app) -> list:
    rotas = rotas_do_back(app)
    return [
        f"{arquivo}:{linha}  {metodo} {fonte}"
        for arquivo, linha, metodo, fonte, concreto in chamadas_do_front()
        if not any(m == metodo and rx.match(concreto) for m, _, rx in rotas)
    ]


def rotas_nunca_chamadas(app) -> list:
    rotas = rotas_do_back(app)
    usados = [(m, c) for *_, m, _, c in chamadas_do_front()]
    return sorted(
        f"{metodo} {caminho}"
        for metodo, caminho, rx in rotas
        if not any(m == metodo and rx.match(c) for m, c in usados)
    )


if __name__ == "__main__":
    import tempfile

    import _app  # noqa: F401  (põe backend/app no caminho de import)

    os.environ.setdefault(
        "DELTACARE_DB", os.path.join(tempfile.gettempdir(), f"contrato_{os.getpid()}.db")
    )
    import main

    print(f"{len(chamadas_do_front())} chamadas do front conferidas")
    for titulo, itens in (
        ("chamadas sem rota", chamadas_sem_rota(main.app)),
        ("rotas que o front nunca chama", rotas_nunca_chamadas(main.app)),
    ):
        print(f"\n{titulo} ({len(itens)}):")
        for item in itens:
            print("  ", item)
