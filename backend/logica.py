"""Regras de negócio do backend: login, cadastro e recuperação de senha.

Fica separado do main.py de propósito, sem depender do FastAPI, para poder
ser testado sozinho (com sqlite3 puro).
"""

import secrets
import sqlite3
from datetime import datetime, timedelta

from security import hash_senha, verificar_senha

DB_PATH = "deltacare.db"
TIPOS_VALIDOS = ("adm", "professor", "aluno")
PAGINAS = {"adm": "adm.html", "professor": "prof.html", "aluno": "aluno.html"}
VALIDADE_TOKEN_MINUTOS = 15


def _conectar():
    return sqlite3.connect(DB_PATH)


def realizar_login(email: str, senha: str) -> dict:
    email = email.strip().lower()

    conexao = _conectar()
    cursor = conexao.cursor()
    cursor.execute("SELECT senha, tipo FROM users WHERE email = ?", (email,))
    usuario = cursor.fetchone()
    conexao.close()

    if usuario and verificar_senha(senha, usuario[0]):
        pagina = PAGINAS.get(usuario[1])
        if pagina:
            return {"mensagem": "Login bem-sucedido!", "pagina": pagina}

    return {"mensagem": "E-mail ou senha incorretos."}


def cadastrar_usuario(email: str, senha: str, tipo: str) -> dict:
    email = email.strip().lower()
    tipo = tipo.strip().lower()

    if tipo not in TIPOS_VALIDOS:
        return {
            "sucesso": False,
            "mensagem": f"Tipo inválido. Use um destes: {', '.join(TIPOS_VALIDOS)}.",
        }

    if len(senha) < 6:
        return {"sucesso": False, "mensagem": "A senha precisa ter pelo menos 6 caracteres."}

    conexao = _conectar()
    cursor = conexao.cursor()

    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
    if cursor.fetchone():
        conexao.close()
        return {"sucesso": False, "mensagem": "Já existe uma conta com esse e-mail."}

    cursor.execute(
        "INSERT INTO users (email, senha, tipo) VALUES (?, ?, ?)",
        (email, hash_senha(senha), tipo),
    )
    conexao.commit()
    conexao.close()

    return {"sucesso": True, "mensagem": "Conta criada com sucesso!"}


def solicitar_recuperacao(email: str) -> dict:
    email = email.strip().lower()

    conexao = _conectar()
    cursor = conexao.cursor()

    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
    usuario = cursor.fetchone()

    if not usuario:
        conexao.close()
        return {"mensagem": "Não encontramos uma conta com esse e-mail."}

    token = f"{secrets.randbelow(900000) + 100000}"
    expira = (datetime.utcnow() + timedelta(minutes=VALIDADE_TOKEN_MINUTOS)).isoformat()

    cursor.execute(
        "UPDATE users SET reset_token = ?, reset_expira = ? WHERE id = ?",
        (token, expira, usuario[0]),
    )
    conexao.commit()
    conexao.close()

    # Ainda não há um serviço de e-mail configurado, então por enquanto o
    # código só é impresso no console do backend (simulando o envio). Basta
    # trocar esta linha por um envio real (SMTP, SendGrid etc.) quando
    # houver um serviço disponível.
    print(f"[Delta Care] Código de recuperação para {email}: {token} (válido por {VALIDADE_TOKEN_MINUTOS} min)")

    return {"mensagem": "Enviamos um código de recuperação para seu e-mail."}


def redefinir_senha(token: str, nova_senha: str) -> dict:
    if len(nova_senha) < 6:
        return {"sucesso": False, "mensagem": "A nova senha precisa ter pelo menos 6 caracteres."}

    conexao = _conectar()
    cursor = conexao.cursor()

    cursor.execute("SELECT id, reset_expira FROM users WHERE reset_token = ?", (token,))
    usuario = cursor.fetchone()

    if not usuario:
        conexao.close()
        return {"sucesso": False, "mensagem": "Código inválido."}

    id_usuario, expira = usuario

    if not expira or datetime.utcnow() > datetime.fromisoformat(expira):
        conexao.close()
        return {"sucesso": False, "mensagem": "Código expirado. Solicite um novo."}

    cursor.execute(
        "UPDATE users SET senha = ?, reset_token = NULL, reset_expira = NULL WHERE id = ?",
        (hash_senha(nova_senha), id_usuario),
    )
    conexao.commit()
    conexao.close()

    return {"sucesso": True, "mensagem": "Senha redefinida com sucesso!"}