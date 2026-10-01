"""Cria a conta de administração num servidor novo.

    python criar_admin.py

Pergunta e-mail, nome e senha no terminal (a senha não aparece enquanto é
digitada). É o único jeito de a primeira conta de confiança nascer: nenhuma
rota da API cria admin sem um admin já logado, de propósito.

Em produção, use este, e **nunca** o seed_demo.py: o seed cria contas de
demonstração com a senha "demo123", que qualquer pessoa que já viu o projeto
conhece.

Recusa se já existir um admin. O segundo em diante é criado pela tela de
Usuários, por quem já é admin — e assim fica registrado quem criou quem.
"""

import getpass
import sys

from infra.database import abrir_conexao, configurar_banco
from infra.security import hash_senha

TAMANHO_MINIMO_SENHA = 10


def criar_primeiro_admin(email: str, nome: str, senha: str) -> dict:
    email = (email or "").strip().lower()
    nome = (nome or "").strip()

    if "@" not in email or not nome:
        return {"sucesso": False, "mensagem": "Informe um e-mail válido e o nome completo."}
    # Mais exigente que a conta comum: esta abre tudo.
    if len(senha) < TAMANHO_MINIMO_SENHA:
        return {"sucesso": False, "mensagem": f"A senha da administração precisa de {TAMANHO_MINIMO_SENHA} caracteres ou mais."}

    configurar_banco(silencioso=True)
    conexao = abrir_conexao()
    try:
        if conexao.execute("SELECT 1 FROM users WHERE tipo = 'adm'").fetchone():
            return {"sucesso": False, "mensagem": "Já existe administração. Crie as próximas contas pela tela de Usuários."}
        if conexao.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
            return {"sucesso": False, "mensagem": "Já existe uma conta com esse e-mail."}

        conexao.execute(
            "INSERT INTO users (email, senha, tipo, nome) VALUES (?, ?, 'adm', ?)",
            (email, hash_senha(senha), nome),
        )
        conexao.commit()
    finally:
        conexao.close()

    return {"sucesso": True, "mensagem": f"Administração criada: {email}"}


if __name__ == "__main__":
    email = input("E-mail da administração: ")
    nome = input("Nome completo: ")
    senha = getpass.getpass("Senha (não aparece): ")
    if senha != getpass.getpass("Repita a senha: "):
        print("As senhas não conferem.")
        sys.exit(1)

    resultado = criar_primeiro_admin(email, nome, senha)
    print(resultado["mensagem"])
    sys.exit(0 if resultado["sucesso"] else 1)
