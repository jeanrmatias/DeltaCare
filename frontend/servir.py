"""Servidor estático do frontend, para desenvolvimento e demonstração.

    python servir.py          # http://127.0.0.1:5500

Por que não usar `python -m http.server` direto: ele não manda cabeçalho de
cache nenhum, só `Last-Modified`. Sem `Cache-Control`, o navegador aplica um
cache heurístico e pode continuar usando a versão antiga de um .js mesmo depois
do arquivo mudar — foi exatamente isso que aconteceu ao migrar para a
autenticação por token: a página carregava o auth.js antigo e quebrava.

Aqui todo arquivo vai com `no-store`, então o que você vê no navegador é sempre
o que está no disco. Em produção o comportamento desejado é o oposto (cache
longo com hash no nome do arquivo), mas aqui previsibilidade vale mais.
"""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

PORTA = 5500


class SemCache(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()


if __name__ == "__main__":
    # ThreadingHTTPServer, e não TCPServer: o navegador abre várias conexões em
    # paralelo e as mantém vivas. Um servidor de uma requisição por vez fica
    # bloqueado na primeira conexão ociosa e a página inteira pendura.
    ThreadingHTTPServer.allow_reuse_address = True

    with ThreadingHTTPServer(("127.0.0.1", PORTA), SemCache) as servidor:
        print(f"Frontend em http://127.0.0.1:{PORTA}")
        print("Ctrl+C para parar.")
        try:
            servidor.serve_forever()
        except KeyboardInterrupt:
            print("\nEncerrado.")
