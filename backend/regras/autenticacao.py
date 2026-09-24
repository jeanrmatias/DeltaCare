"""Regras de negócio do backend: login, cadastro e recuperação de senha.

Fica separado do main.py de propósito, sem depender do FastAPI, para poder
ser testado sozinho (com sqlite3 puro).
"""

import secrets
import sqlite3
from datetime import datetime, timedelta

from infra.security import hash_senha, verificar_senha

from infra.database import CAMINHO_DB as DB_PATH
TIPOS_VALIDOS = ("adm", "professor", "aluno")
# Os caminhos precisam bater com as pastas reais em frontend/ — a pasta do
# administrador chama-se "administracao", não "adm" (que é o valor do campo
# `tipo` no banco). Já foram coisas diferentes, e o login quebrou por isso.
PAGINAS = {
    "adm": "administracao/adm.html",
    "professor": "professor/prof.html",
    "aluno": "aluno/inicio.html",
}
VALIDADE_TOKEN_MINUTOS = 15


def _conectar():
    return sqlite3.connect(DB_PATH)


def realizar_login(email: str, senha: str) -> dict:
    email = email.strip().lower()

    conexao = _conectar()
    cursor = conexao.cursor()
    cursor.execute("SELECT id, senha, tipo, nome FROM users WHERE email = ?", (email,))
    usuario = cursor.fetchone()
    conexao.close()

    if usuario and verificar_senha(senha, usuario[1]):
        user_id, _, tipo, nome = usuario
        pagina = PAGINAS.get(tipo)
        if pagina:
            # O token é o que prova a identidade nas requisições seguintes —
            # nenhuma rota protegida aceita e-mail vindo do cliente (infra/sessoes.py).
            from infra.sessoes import criar_sessao

            return {
                "sucesso": True,
                "mensagem": "Login bem-sucedido!",
                "pagina": pagina,
                "email": email,
                "tipo": tipo,
                # Contas anteriores à coluna `nome` não têm esse dado; o front
                # cai no e-mail nesse caso.
                "nome": nome or "",
                "token": criar_sessao(user_id),
            }

    return {"sucesso": False, "mensagem": "E-mail ou senha incorretos."}


def cadastrar_usuario(email: str, senha: str, tipo: str, nome: str = "") -> dict:
    """Cadastro público. Só cria conta de aluno — professor e admin são
    contas de confiança e só podem ser criadas por um administrador
    (ver criar_conta_staff), senão qualquer pessoa poderia se cadastrar
    como admin direto por essa rota.
    """
    email = email.strip().lower()
    tipo = tipo.strip().lower()
    nome = (nome or "").strip()

    if tipo != "aluno":
        return {
            "sucesso": False,
            "mensagem": "O cadastro público é só para conta de aluno.",
        }

    if not nome:
        return {"sucesso": False, "mensagem": "Informe seu nome completo."}

    if len(senha) < 6:
        return {"sucesso": False, "mensagem": "A senha precisa ter pelo menos 6 caracteres."}

    conexao = _conectar()
    cursor = conexao.cursor()

    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
    if cursor.fetchone():
        conexao.close()
        return {"sucesso": False, "mensagem": "Já existe uma conta com esse e-mail."}

    cursor.execute(
        "INSERT INTO users (email, senha, tipo, nome) VALUES (?, ?, ?, ?)",
        (email, hash_senha(senha), tipo, nome),
    )
    conexao.commit()
    conexao.close()

    return {"sucesso": True, "mensagem": "Conta criada com sucesso!"}


def criar_conta_staff(
    admin_email: str,
    email: str,
    senha: str,
    tipo: str,
    nome: str = "",
    disciplinas: str = "",
    matricula: str = "",
    turma_id: int | None = None,
) -> dict:
    """Cria conta de qualquer perfil. Só um admin já existente pode chamar
    isso (mesmo padrão de permissão usado em regras/turmas.criar_turma).

    Aceita também "aluno", e isso não contradiz a restrição do cadastro
    público: lá o risco é qualquer pessoa da internet escolher o próprio
    perfil, e por isso `cadastrar_usuario` só cria aluno. Aqui quem cria já é
    um administrador autenticado, e uma instituição precisa poder cadastrar a
    turma inteira sem depender de cada aluno se inscrever sozinho.

    `disciplinas` só vale para professor e `matricula` só para aluno; cada um é
    ignorado nos outros perfis em vez de dar erro, para o formulário poder
    enviar sempre o mesmo corpo. `turma_id` matricula o aluno já na criação —
    é o que evita cadastrar a turma inteira e depois matricular um a um.
    """
    admin_email = admin_email.strip().lower()
    email = email.strip().lower()
    tipo = tipo.strip().lower()
    nome = (nome or "").strip()

    if tipo not in ("professor", "adm", "aluno"):
        return {"sucesso": False, "mensagem": "Tipo inválido. Use 'aluno', 'professor' ou 'adm'."}

    if not nome:
        return {"sucesso": False, "mensagem": "Informe o nome completo."}

    if len(senha) < 6:
        return {"sucesso": False, "mensagem": "A senha precisa ter pelo menos 6 caracteres."}

    conexao = _conectar()
    cursor = conexao.cursor()

    cursor.execute("SELECT tipo FROM users WHERE email = ?", (admin_email,))
    admin = cursor.fetchone()
    if not admin or admin[0] != "adm":
        conexao.close()
        return {"sucesso": False, "mensagem": "Só um administrador pode criar essa conta."}

    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
    if cursor.fetchone():
        conexao.close()
        return {"sucesso": False, "mensagem": "Já existe uma conta com esse e-mail."}

    cursor.execute(
        "INSERT INTO users (email, senha, tipo, nome, disciplinas, matricula) VALUES (?, ?, ?, ?, ?, ?)",
        (
            email,
            hash_senha(senha),
            tipo,
            nome,
            (disciplinas or "").strip() if tipo == "professor" else None,
            (matricula or "").strip() if tipo == "aluno" else None,
        ),
    )
    conexao.commit()
    conexao.close()

    if tipo == "aluno" and turma_id:
        from regras.matriculas import matricular_aluno

        resultado = matricular_aluno(admin_email, email, turma_id)
        if not resultado.get("sucesso"):
            return {
                "sucesso": True,
                "mensagem": f"Conta criada, mas não foi possível matricular: {resultado.get('mensagem')}",
            }
        return {"sucesso": True, "mensagem": "Conta criada e aluno matriculado na turma!"}

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
