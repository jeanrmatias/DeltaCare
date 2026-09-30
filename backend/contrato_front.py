"""Confere se o front e o back falam a mesma língua.

Dois tipos de quebra que nenhum teste de regra pega, porque cada lado está
certo sozinho:

1. **O front chama uma rota que não existe**, ou com o verbo errado. O back
   renomeia `/admin/coortes/excecoes` para `/admin/excecoes`, esquece de mudar
   uma tela, e ela passa a responder 404/405 — só no navegador.
2. **O script procura um elemento que a página não tem.** `querySelector`
   devolve null, e a tela quebra na primeira linha que usa o resultado.

Leitura estática do código, sem navegador: pega o que dá para pegar sem
executar. Usado pelos testes (backend/testes.py) e pode ser rodado sozinho:

    python contrato_front.py
"""

import glob
import os
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONT = os.path.join(RAIZ, "frontend")

# Scripts carregados em quase toda página, que procuram elementos opcionais e
# conferem se eles existem antes de usar (notificações, perfil, diálogo...).
# A conferência de id vale para os scripts de cada tela.
COMPARTILHADOS = {
    "config.js", "dialogo.js", "auth.js", "perfil.js", "notificacoes.js",
    "visualizador.js", "markdown.js", "calendario.js", "modulos.js",
}

_CHAMADA = re.compile(
    r"\b(?:api|apiPublica)\(\s*(?:([`\"'])(.*?)\1|([A-Za-z_]\w*))\s*(?:,\s*(\{.*?\}))?\s*\)",
    re.S,
)
_LITERAL = re.compile(r"([`\"'])(/[^`\"']*)\1")
_METODO = re.compile(r"method:\s*([^,}\n]+)")


def _arquivos_js():
    for caminho in sorted(glob.glob(os.path.join(FRONT, "**", "*.js"), recursive=True)):
        if not caminho.endswith("testes.mjs"):
            yield caminho


def _definicao(texto: str, nome: str, antes_de: int | None = None) -> str:
    """O trecho `const nome = ...;`, para resolver caminho guardado em variável.

    Com `antes_de`, pega a definição mais próxima **antes** da chamada: um
    arquivo pode ter `const caminho` em duas funções, e a primeira do arquivo
    não é necessariamente a da chamada.
    """
    definicoes = list(re.finditer(rf"\b(?:const|let)\s+{nome}\s*=\s*(.*?);", texto, re.S))
    if antes_de is not None:
        definicoes = [d for d in definicoes if d.start() < antes_de]
        definicoes = definicoes[-1:]
    return definicoes[0].group(1) if definicoes else ""


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


def chamadas_do_front() -> list:
    """(arquivo, linha, verbo, caminho no fonte, caminho concreto)."""
    resultado = []
    for arquivo in _arquivos_js():
        texto = open(arquivo, encoding="utf-8").read()
        relativo = os.path.relpath(arquivo, RAIZ)

        for achado in _CHAMADA.finditer(texto):
            linha = texto.count("\n", 0, achado.start()) + 1
            opcoes = achado.group(4)

            if achado.group(2) is not None:
                fontes = [achado.group(2)]
            else:
                # api(caminho, ...): o caminho está numa variável da função.
                definicao = _definicao(texto, achado.group(3), antes_de=achado.start())
                fontes = [m.group(2) for m in _LITERAL.finditer(definicao)]

            for fonte in fontes:
                for concreto in _normalizar(fonte, texto):
                    for metodo in _metodos(opcoes):
                        resultado.append((relativo, linha, metodo, fonte, concreto))

    return resultado


def links_de_api_no_front() -> list:
    """Rotas usadas como link (`${API_URL}/entregas/${id}/arquivo`), sempre GET."""
    resultado = []
    for arquivo in _arquivos_js():
        texto = open(arquivo, encoding="utf-8").read()
        for achado in re.finditer(r"\$\{API_URL\}(/[^`\"'\s]*)", texto):
            for concreto in _normalizar(achado.group(1), texto):
                resultado.append((os.path.relpath(arquivo, RAIZ), "GET", concreto))
    return resultado


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
    usados = [(m, c) for *_, m, _, c in chamadas_do_front()] + [
        (m, c) for _, m, c in links_de_api_no_front()
    ]
    return sorted(
        f"{metodo} {caminho}"
        for metodo, caminho, rx in rotas
        if not any(m == metodo and rx.match(c) for m, c in usados)
    )


def ids_ausentes() -> list:
    """Elementos que o script de uma página procura e que ninguém cria."""
    problemas = []
    for pagina in sorted(glob.glob(os.path.join(FRONT, "**", "*.html"), recursive=True)):
        html = open(pagina, encoding="utf-8").read()
        pasta = os.path.dirname(pagina)
        ids = set(re.findall(r'\bid="([^"]+)"', html))

        scripts = []
        for src in re.findall(r'<script src="([^"?]+)', html):
            caminho_js = os.path.normpath(os.path.join(pasta, src))
            if not os.path.exists(caminho_js):
                problemas.append(f"{os.path.relpath(pagina, RAIZ)}: script inexistente {src}")
                continue
            texto = open(caminho_js, encoding="utf-8").read()
            # Ids criados pelo próprio JS também existem na página.
            ids |= set(re.findall(r'\bid="([\w-]+)"', texto))
            ids |= set(re.findall(r'\.id\s*=\s*"([\w-]+)"', texto))
            if os.path.basename(src) not in COMPARTILHADOS:
                scripts.append((os.path.basename(src), texto))

        for nome, texto in scripts:
            procurados = set(re.findall(r'querySelector\(\s*"#([\w-]+)"\s*\)', texto))
            for faltando in sorted(procurados - ids):
                problemas.append(f"{os.path.relpath(pagina, RAIZ)} + {nome}: #{faltando}")

    return problemas


if __name__ == "__main__":
    import sys
    import tempfile

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    os.environ.setdefault(
        "DELTACARE_DB", os.path.join(tempfile.gettempdir(), f"contrato_{os.getpid()}.db")
    )
    import main

    total = len(chamadas_do_front())
    print(f"{total} chamadas do front conferidas")
    for titulo, itens in (
        ("chamadas sem rota", chamadas_sem_rota(main.app)),
        ("ids ausentes", ids_ausentes()),
        ("rotas que o front nunca chama", rotas_nunca_chamadas(main.app)),
    ):
        print(f"\n{titulo} ({len(itens)}):")
        for item in itens:
            print("  ", item)
