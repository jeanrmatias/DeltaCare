"""Sessão autenticada por token.

O problema que isto resolve: até aqui o backend acreditava no e-mail que o
front mandava em cada requisição. Quem soubesse o e-mail de um professor
conseguia editar os materiais dele — a regra de permissão existia, mas não
havia nada provando que o autor da requisição era quem dizia ser.

Agora o login devolve um token aleatório, guardado no banco, e cada rota
protegida descobre o usuário a partir desse token (header
`Authorization: Bearer <token>`). Nenhuma rota volta a aceitar identidade
vinda do corpo ou da query string.

Por que token opaco no banco e não JWT: dá para revogar na hora (logout,
conta suspensa), não exige gerenciar chave de assinatura e é menos código
para revisar. JWT faz sentido quando há vários serviços validando sem
consultar o banco, o que não é o caso aqui.
"""

import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

from infra.database import CAMINHO_DB, abrir_conexao

# Uma sessão dura o suficiente para uma aula ou uma demonstração sem obrigar
# o usuário a logar de novo no meio.
DURACAO_SESSAO = timedelta(hours=12)


def resumo_do_token(token: str) -> str:
    """O que o banco guarda no lugar do token: o SHA-256 dele.

    O banco vai para o backup todo dia. Com o token como o navegador recebe,
    quem pusesse a mão numa cópia entrava como qualquer pessoa com sessão
    aberta, por até 12 horas, sem senha e sem o código por e-mail. Com o hash,
    a cópia não abre sessão nenhuma. Sem sal de propósito: o token já é
    aleatório (256 bits), não há dicionário a evitar, e a busca precisa
    achar a linha pelo valor.
    """
    return hashlib.sha256(token.encode()).hexdigest()


def _conectar():
    return abrir_conexao()


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def criar_sessao(user_id: int) -> str:
    """Gera um token novo para o usuário e devolve o token."""
    token = secrets.token_urlsafe(32)
    agora = _agora()

    conexao = _conectar()
    cursor = conexao.cursor()
    cursor.execute(
        "INSERT INTO sessoes (token, user_id, criado_em, expira_em) VALUES (?, ?, ?, ?)",
        (
            resumo_do_token(token),
            user_id,
            agora.isoformat(),
            (agora + DURACAO_SESSAO).isoformat(),
        ),
    )
    conexao.commit()
    conexao.close()

    return token


def buscar_usuario_da_sessao(token: str):
    """Devolve {"id", "email", "tipo"} do dono do token, ou None.

    Retorna None tanto para token inexistente quanto para token expirado —
    de fora, os dois casos são a mesma coisa: não autenticado.
    """
    if not token:
        return None

    conexao = _conectar()
    cursor = conexao.cursor()
    # Conta desativada não tem sessão válida. A desativação já apaga as
    # sessões; o filtro aqui é o cinto junto do suspensório — uma sessão que
    # escapasse (criada no mesmo instante, banco restaurado) não abriria nada.
    cursor.execute(
        '''
        SELECT u.id, u.email, u.tipo, s.expira_em, u.senha_provisoria
        FROM sessoes s
        JOIN users u ON u.id = s.user_id
        WHERE s.token = ? AND u.desativado_em IS NULL
        ''',
        (resumo_do_token(token),),
    )
    linha = cursor.fetchone()
    conexao.close()

    if not linha:
        return None

    user_id, email, tipo, expira_em, senha_provisoria = linha

    try:
        expira = datetime.fromisoformat(expira_em)
        if expira.tzinfo is None:
            expira = expira.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None

    if expira <= _agora():
        encerrar_sessao(token)
        return None

    return {"id": user_id, "email": email, "tipo": tipo, "token": token, "senha_provisoria": bool(senha_provisoria)}


def encerrar_sessao(token: str) -> None:
    """Invalida um token (logout). Silencioso se o token já não existe."""
    if not token:
        return

    conexao = _conectar()
    cursor = conexao.cursor()
    cursor.execute("DELETE FROM sessoes WHERE token = ?", (resumo_do_token(token),))
    conexao.commit()
    conexao.close()


def limpar_sessoes_expiradas() -> int:
    """Remove sessões vencidas. Chamado no start do servidor."""
    conexao = _conectar()
    cursor = conexao.cursor()
    cursor.execute("DELETE FROM sessoes WHERE expira_em <= ?", (_agora().isoformat(),))
    removidas = cursor.rowcount
    conexao.commit()
    conexao.close()
    return removidas
