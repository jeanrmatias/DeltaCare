"""Cabeçalhos de segurança em toda resposta da API e das telas.

Ficam aqui, e não só no Caddy, para valerem do mesmo jeito rodando o uvicorn
direto (desenvolvimento, demonstração na máquina do professor). O Caddy só
acrescenta o HSTS, que depende de haver HTTPS.

- **Content-Security-Policy** (só nas telas, em /app): o navegador só executa
  script vindo do próprio servidor, e só carrega fonte do Google Fonts. Se um
  dia escapar um XSS — texto da IA, nome de arquivo, o que for —, o script
  injetado não roda e não tem para onde mandar o token. `blob:` é o
  visualizador de material (PDF, imagem e vídeo abertos sem baixar). As
  rotas de documentação da API (/docs) usam scripts de CDN e ficam de fora.
- **frame-ancestors 'none'** e **X-Frame-Options: DENY**: ninguém põe o Delta
  Care dentro de outro site para enganar o clique (clickjacking).
- **nosniff**: o navegador respeita o tipo declarado. Um .txt com HTML
  dentro continua texto.
- **Referrer-Policy**: endereço interno não vaza para site externo.
- **Permissions-Policy**: câmera, microfone e localização desligados.
"""

POLITICA_DAS_TELAS = "; ".join([
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' https://fonts.googleapis.com",
    "font-src 'self' https://fonts.gstatic.com",
    "img-src 'self' data: blob:",
    "media-src 'self' blob:",
    "frame-src 'self' blob:",
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
])

SEMPRE = [
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"same-origin"),
    (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
]


class CabecalhosDeSeguranca:
    """Middleware ASGI puro (o mesmo formato de FecharConexoesDaRequisicao)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        caminho = scope.get("path", "")
        extras = list(SEMPRE)
        if caminho == "/app" or caminho.startswith("/app/"):
            extras.append((b"content-security-policy", POLITICA_DAS_TELAS.encode()))

        async def enviar(mensagem):
            if mensagem["type"] == "http.response.start":
                existentes = {nome.lower() for nome, _ in mensagem.get("headers", [])}
                mensagem["headers"] = list(mensagem.get("headers", [])) + [
                    (nome, valor) for nome, valor in extras if nome not in existentes
                ]
            await send(mensagem)

        await self.app(scope, receive, enviar)
