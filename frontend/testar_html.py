"""Verifica a estrutura das páginas HTML.

    cd frontend
    python testar_html.py

Usa o parser da biblioteca padrão, e não expressão regular. Duas vezes nesta
base um script de edição em massa cortou HTML no meio — engolindo um
`</aside>` e todo o cabeçalho da página — e a checagem por regex deixou passar,
porque ela só conta tags e não entende aninhamento.

Roda em menos de um segundo e não precisa de servidor.
"""

import glob
import os
import sys
from html.parser import HTMLParser

# Tags que não fecham. As de SVG entram aqui porque o parser do Python não
# conhece a sintaxe de auto-fechamento do XML (<path />).
SEM_FECHAMENTO = {
    "br", "hr", "img", "input", "meta", "link", "source", "track",
    "area", "base", "col", "embed", "param", "wbr",
    "path", "circle", "rect", "line", "polyline", "polygon", "ellipse", "use", "stop",
}


class VerificadorHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.pilha = []
        self.erros = []

    def handle_starttag(self, tag, atributos):
        if tag not in SEM_FECHAMENTO:
            self.pilha.append((tag, self.getpos()[0]))

    def handle_endtag(self, tag):
        if tag in SEM_FECHAMENTO:
            return

        if not self.pilha:
            self.erros.append("linha %d: </%s> sem abertura" % (self.getpos()[0], tag))
            return

        aberta, linha_abertura = self.pilha.pop()
        if aberta != tag:
            self.erros.append(
                "linha %d: </%s> fecha <%s> que abriu na linha %d"
                % (self.getpos()[0], tag, aberta, linha_abertura)
            )


def verificar(caminho: str) -> list:
    with open(caminho, encoding="utf-8") as arquivo:
        conteudo = arquivo.read()

    verificador = VerificadorHTML()
    verificador.feed(conteudo)

    erros = list(verificador.erros)

    # `svg` sobra na pilha porque o conteúdo interno usa auto-fechamento.
    nao_fechadas = [(t, l) for t, l in verificador.pilha if t != "svg"]
    for tag, linha in nao_fechadas:
        erros.append("linha %d: <%s> aberta e nunca fechada" % (linha, tag))

    # Marcas de corte no meio de uma tag, que o parser às vezes tolera.
    if "< <" in conteudo or "<  <" in conteudo:
        erros.append("há '<' seguido de '<': provável tag cortada no meio")

    return erros


def main() -> int:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    paginas = sorted(glob.glob(os.path.join("**", "*.html"), recursive=True))

    if not paginas:
        print("Nenhuma página encontrada.")
        return 1

    com_problema = 0

    for caminho in paginas:
        erros = verificar(caminho)

        if erros:
            com_problema += 1
            print("[ERRO] %s" % caminho)
            for erro in erros:
                print("       %s" % erro)
        else:
            print("[ok]   %s" % caminho)

    print()
    print("%d página(s) verificada(s), %d com problema." % (len(paginas), com_problema))

    return 1 if com_problema else 0


if __name__ == "__main__":
    sys.exit(main())
