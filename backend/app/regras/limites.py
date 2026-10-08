"""O tamanho máximo de cada texto que chega de fora.

Sem limite, uma pergunta de um megabyte ia inteira para o modelo de IA (e
segurava o servidor de IA, que atende um por vez, por minutos) e ficava no
banco; um enunciado ou uma resposta gigante fazia o mesmo com a tela de quem
abrisse. Os limites são largos para o uso real e fechados para o abuso. Em
produção o Caddy ainda barra o corpo inteiro acima de 25 MB (deploy/Caddyfile).

Mensagens, avisos, anotações e pedidos de privacidade já tinham o seu limite,
no próprio módulo, e continuam com ele.
"""

NOME = 120             # pessoa, turma, disciplina
TITULO = 200           # material, atividade
PERGUNTA = 2_000       # pergunta ao assistente
ALTERNATIVA = 500      # cada alternativa de questão
TEXTO_CURTO = 2_000    # descrição de denúncia, enunciado de questão
TEXTO = 20_000         # enunciado de atividade, resposta dissertativa, descrição de material, devolutiva
QUESTOES = 100         # questões por atividade
ALTERNATIVAS = 10      # alternativas por questão


def excesso(*campos) -> str | None:
    """A mensagem do primeiro campo acima do limite, ou None.

        excesso((titulo, TITULO, "O título"), (enunciado, TEXTO, "O enunciado"))
    """
    for valor, limite, rotulo in campos:
        if valor and len(str(valor)) > limite:
            return f"{rotulo} passa de {limite} caracteres."
    return None
