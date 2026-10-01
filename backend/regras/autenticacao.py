"""Regras de negócio do backend: login, cadastro e recuperação de senha.

Fica separado do main.py de propósito, sem depender do FastAPI, para poder
ser testado sozinho (com sqlite3 puro).
"""

import hmac
import secrets
import sqlite3
from datetime import datetime, timedelta

from infra.security import hash_senha, verificar_senha

from infra.database import CAMINHO_DB as DB_PATH
from infra.database import abrir_conexao
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

# Palpites errados antes de o código de recuperação ser descartado.
#
# São 6 dígitos, 900 mil combinações. Sem este teto, e sem limite por IP na
# frente, um atacante percorre o espaço inteiro em minutos. Com o teto, a chance
# de acertar em 5 tentativas é de 1 em 180 mil — e a pessoa que de fato esqueceu
# a senha erra uma ou duas vezes, não cinco.
MAX_TENTATIVAS_RESET = 5

# Falhas de login antes de bloquear, e por quanto tempo.
#
# O bloqueio é por e-mail e temporário. Temporário porque o mesmo mecanismo que
# impede um robô de testar senhas permite a qualquer um trancar a conta de um
# colega digitando errado de propósito; 15 minutos tornam isso um incômodo, e
# não um jeito de impedir alguém de entregar uma prova.
#
# Por IP fica para o servidor de verdade, na frente da aplicação (limit_req do
# nginx, ou o equivalente do provedor). Aqui a aplicação não sabe o IP real: por
# trás de um proxy, todo mundo chega com o IP do proxy.
MAX_FALHAS_LOGIN = 5
JANELA_LOGIN_MINUTOS = 15

# Hash de uma senha qualquer, para conferir contra ele quando o e-mail não
# existe. Ver o comentário em realizar_login.
_HASH_DE_ENGANO = hash_senha("senha-que-ninguem-tem")


def _conectar():
    return abrir_conexao()


def _falhas_recentes(cursor, email: str) -> int:
    limite = (datetime.utcnow() - timedelta(minutes=JANELA_LOGIN_MINUTOS)).isoformat()
    # As antigas saem aqui mesmo: a tabela só precisa lembrar da janela atual.
    cursor.execute(
        "DELETE FROM tentativas_login WHERE email = ? AND criado_em < ?", (email, limite)
    )
    cursor.execute("SELECT COUNT(*) FROM tentativas_login WHERE email = ?", (email,))
    return cursor.fetchone()[0]


def realizar_login(email: str, senha: str) -> dict:
    email = email.strip().lower()

    conexao = _conectar()
    cursor = conexao.cursor()

    # Bloqueado: responde **sem conferir a senha**. Conferir e responder
    # "bloqueado" mesmo quando ela está certa ainda deixaria o robô continuar
    # testando — bastaria medir o tempo da resposta.
    if _falhas_recentes(cursor, email) >= MAX_FALHAS_LOGIN:
        conexao.commit()
        conexao.close()
        return {
            "sucesso": False,
            "mensagem": (
                f"Muitas tentativas erradas. Aguarde {JANELA_LOGIN_MINUTOS} minutos"
                " ou use \"Esqueci minha senha\"."
            ),
        }

    cursor.execute("SELECT id, senha, tipo, nome FROM users WHERE email = ?", (email,))
    usuario = cursor.fetchone()

    # **Tempo igual para conta que existe e que não existe.** Sem o hash de
    # engano, e-mail inexistente respondia 57x mais rápido (1ms contra 71ms,
    # medido), porque a conferência da senha — o PBKDF2 — nem rodava. A
    # mensagem era a mesma, mas o cronômetro entregava quem é aluno daqui.
    senha_confere = verificar_senha(senha, usuario[1] if usuario else _HASH_DE_ENGANO)

    if not (usuario and senha_confere):
        cursor.execute(
            "INSERT INTO tentativas_login (email, criado_em) VALUES (?, ?)",
            (email, datetime.utcnow().isoformat()),
        )
        conexao.commit()
        conexao.close()
        return {"sucesso": False, "mensagem": "E-mail ou senha incorretos."}

    # Acertou: o histórico de erros da janela some. Senão quem errou quatro
    # vezes de manhã entraria na tarde com uma tentativa só de margem.
    cursor.execute("DELETE FROM tentativas_login WHERE email = ?", (email,))
    conexao.commit()
    conexao.close()

    user_id, _, tipo, nome = usuario
    pagina = PAGINAS.get(tipo)

    # Perfil sem tela (valor inesperado na coluna `tipo`): não há para onde
    # mandar a pessoa, e uma sessão sem destino seria acesso a coisa nenhuma.
    if not pagina:
        return {"sucesso": False, "mensagem": "E-mail ou senha incorretos."}

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


# Uma frase só, para os dois casos. Ver a nota em solicitar_recuperacao.
RESPOSTA_RECUPERACAO = (
    "Se houver uma conta com esse e-mail, enviamos um código de recuperação para ela."
)


def solicitar_recuperacao(email: str) -> dict:
    email = email.strip().lower()

    conexao = _conectar()
    cursor = conexao.cursor()

    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
    usuario = cursor.fetchone()

    # **A mesma resposta para conta que existe e conta que não existe.**
    #
    # Dizer "não encontramos essa conta" transforma esta rota num verificador de
    # cadastro: quem tiver uma lista de e-mails descobre quais são alunos desta
    # instituição, um por requisição. Numa faculdade de medicina isso é a lista
    # de matriculados, e é dado pessoal.
    if not usuario:
        conexao.close()
        return {"mensagem": RESPOSTA_RECUPERACAO}

    token = f"{secrets.randbelow(900000) + 100000}"
    expira = (datetime.utcnow() + timedelta(minutes=VALIDADE_TOKEN_MINUTOS)).isoformat()

    # O contador zera junto: pedir um código novo devolve as 5 tentativas.
    cursor.execute(
        "UPDATE users SET reset_token = ?, reset_expira = ?, reset_tentativas = 0 WHERE id = ?",
        (token, expira, usuario[0]),
    )
    conexao.commit()
    conexao.close()

    # Em segundo plano: enviar leva um ou dois segundos e só acontece quando a
    # conta existe. Esperando aqui, o tempo de resposta diria quem é aluno
    # (ver infra/email.enviar_em_segundo_plano). Sem SMTP configurado, o
    # código vai para o console do servidor, como antes.
    from infra.email import enviar_em_segundo_plano

    enviar_em_segundo_plano(
        email,
        "Delta Care — código para redefinir sua senha",
        f"Seu código de recuperação é: {token}\n\n"
        f"Ele vale por {VALIDADE_TOKEN_MINUTOS} minutos e pode ser usado uma vez só. "
        f"Depois de {MAX_TENTATIVAS_RESET} tentativas erradas, ele deixa de valer e é "
        "preciso pedir outro.\n\n"
        "Se não foi você que pediu, ignore este e-mail: sua senha continua a mesma.",
    )

    return {"mensagem": RESPOSTA_RECUPERACAO}


def redefinir_senha(email: str, token: str, nova_senha: str) -> dict:
    """Troca a senha usando o código enviado por e-mail.

    **`email` é obrigatório, e é o que fecha o furo principal.** Antes a busca
    era `WHERE reset_token = ?` — global. Um atacante tentava códigos contra
    *qualquer* conta com recuperação pendente, e acertar bastava para entrar em
    alguma. Amarrando ao e-mail, ele precisa acertar o código **daquela** pessoa,
    e o contador de tentativas limita isso a 5 palpites.
    """
    email = (email or "").strip().lower()
    token = (token or "").strip()

    if len(nova_senha) < 6:
        return {"sucesso": False, "mensagem": "A nova senha precisa ter pelo menos 6 caracteres."}

    if not email or not token:
        return {"sucesso": False, "mensagem": "Código inválido."}

    conexao = _conectar()
    cursor = conexao.cursor()

    cursor.execute(
        "SELECT id, reset_token, reset_expira, reset_tentativas FROM users WHERE email = ?",
        (email,),
    )
    usuario = cursor.fetchone()

    # Conta inexistente e conta sem recuperação pendente dão a mesma resposta de
    # código errado — a rota não conta a ninguém quem tem cadastro aqui.
    if not usuario or not usuario[1]:
        conexao.close()
        return {"sucesso": False, "mensagem": "Código inválido."}

    id_usuario, token_guardado, expira, tentativas = usuario

    if not expira or datetime.utcnow() > datetime.fromisoformat(expira):
        conexao.close()
        return {"sucesso": False, "mensagem": "Código expirado. Solicite um novo."}

    if not hmac.compare_digest(token, token_guardado):
        tentativas = (tentativas or 0) + 1

        # Estourou o teto: o código morre. Continuar aceitando palpites depois
        # de cinco erros é o mesmo que não ter teto.
        if tentativas >= MAX_TENTATIVAS_RESET:
            cursor.execute(
                "UPDATE users SET reset_token = NULL, reset_expira = NULL, reset_tentativas = 0"
                " WHERE id = ?",
                (id_usuario,),
            )
            conexao.commit()
            conexao.close()
            return {
                "sucesso": False,
                "mensagem": "Código errado muitas vezes. Solicite um novo código.",
            }

        cursor.execute(
            "UPDATE users SET reset_tentativas = ? WHERE id = ?", (tentativas, id_usuario)
        )
        conexao.commit()
        conexao.close()
        return {"sucesso": False, "mensagem": "Código inválido."}

    cursor.execute(
        "UPDATE users SET senha = ?, reset_token = NULL, reset_expira = NULL,"
        " reset_tentativas = 0 WHERE id = ?",
        (hash_senha(nova_senha), id_usuario),
    )

    # Trocar a senha derruba as sessões abertas. Se a conta foi tomada, a senha
    # nova não serve para nada enquanto o token antigo do invasor continuar
    # valendo por 12 horas.
    cursor.execute("DELETE FROM sessoes WHERE user_id = ?", (id_usuario,))

    # E destranca o login: a mensagem de bloqueio manda justamente para cá, e
    # quem acabou de provar pelo e-mail que é dono da conta não deve continuar
    # esperando 15 minutos.
    cursor.execute("DELETE FROM tentativas_login WHERE email = ?", (email,))
    conexao.commit()
    conexao.close()

    return {"sucesso": True, "mensagem": "Senha redefinida com sucesso!"}
