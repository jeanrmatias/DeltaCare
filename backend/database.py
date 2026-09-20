import os
import sqlite3

from security import hash_senha

CAMINHO_DB = "deltacare.db"


def configurar_banco():
    print("Python está procurando o banco em:", os.path.abspath(CAMINHO_DB))

    conexao = sqlite3.connect(CAMINHO_DB)
    cursor = conexao.cursor()
    print("Conexão com o banco de dados estabelecida com sucesso!")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            senha TEXT NOT NULL,
            tipo TEXT NOT NULL
        )
    ''')
    conexao.commit()

    # Migração: adiciona as colunas usadas na recuperação de senha, para
    # bancos criados antes dessa funcionalidade existir.
    cursor.execute("PRAGMA table_info(users)")
    colunas = {linha[1] for linha in cursor.fetchall()}

    if "reset_token" not in colunas:
        cursor.execute("ALTER TABLE users ADD COLUMN reset_token TEXT")
    if "reset_expira" not in colunas:
        cursor.execute("ALTER TABLE users ADD COLUMN reset_expira TEXT")

    conexao.commit()

    # Migração: senhas antigas gravadas em texto puro (de antes do hash)
    # são convertidas automaticamente na primeira execução. Um hash gerado
    # por hash_senha() sempre tem o formato "salt_hex$hash_hex".
    cursor.execute("SELECT id, senha FROM users")
    for id_usuario, senha in cursor.fetchall():
        if "$" not in senha:
            cursor.execute(
                "UPDATE users SET senha = ? WHERE id = ?",
                (hash_senha(senha), id_usuario)
            )
    conexao.commit()

    conexao.close()


if __name__ == "__main__":
    configurar_banco()