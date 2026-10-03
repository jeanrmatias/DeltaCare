"""Regras de negócio do backend: login, contas e recuperação de senha.

Fica separado do main.py de propósito, sem depender do FastAPI, para poder
ser testado sozinho (com sqlite3 puro).
"""

import hashlib
import hmac
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

from infra.security import hash_senha, verificar_senha
from regras.senhas import problema_da_senha

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

    cursor.execute(
        "SELECT id, senha, tipo, nome, desativado_em, senha_provisoria, segundo_fator FROM users WHERE email = ?",
        (email,),
    )
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

    conexao.commit()
    conexao.close()

    user_id, _, tipo, nome, desativado_em, senha_provisoria, segundo_fator = usuario

    # Conta com exclusão aprovada (regras/privacidade.py). Só é dito **depois**
    # de a senha conferir: antes disso, "desativada" contaria a qualquer um que
    # aquele e-mail é de alguém daqui.
    if desativado_em:
        return {
            "sucesso": False,
            "mensagem": "Esta conta foi desativada a pedido. Para reativar, fale com a secretaria.",
        }

    # Perfil sem tela (valor inesperado na coluna `tipo`): não há para onde
    # mandar a pessoa, e uma sessão sem destino seria acesso a coisa nenhuma.
    if not PAGINAS.get(tipo):
        return {"sucesso": False, "mensagem": "E-mail ou senha incorretos."}

    # Professor e administração: a senha certa ainda não abre a sessão. Chega
    # um código no e-mail, e só ele abre (confirmar_codigo).
    if tipo in TIPOS_COM_SEGUNDO_FATOR and segundo_fator:
        return _iniciar_segundo_fator(user_id, email, nome)

    return _abrir_sessao(user_id, email, tipo, nome, senha_provisoria)


def _abrir_sessao(user_id: int, email: str, tipo: str, nome: str, senha_provisoria) -> dict:
    """O login terminou: abre a sessão e zera os erros de login da janela.

    Zerar só aqui, e não ao acertar a senha, é o que impede a volta da
    adivinhação pelo código: quem tem a senha e chuta códigos não zera o
    contador entrando de novo — cada código errado conta como erro de login.
    """
    from infra.sessoes import criar_sessao

    conexao = _conectar()
    conexao.execute("DELETE FROM tentativas_login WHERE email = ?", (email,))
    conexao.commit()
    conexao.close()

    # O token é o que prova a identidade nas requisições seguintes —
    # nenhuma rota protegida aceita e-mail vindo do cliente (infra/sessoes.py).
    return {
        "sucesso": True,
        "mensagem": "Login bem-sucedido!",
        "pagina": PAGINAS[tipo],
        "email": email,
        "tipo": tipo,
        # Contas anteriores à coluna `nome` não têm esse dado; o front
        # cai no e-mail nesse caso.
        "nome": nome or "",
        "token": criar_sessao(user_id),
        # A tela leva direto à troca; o servidor recusa o resto até lá
        # (main.usuario_logado).
        "trocar_senha": bool(senha_provisoria),
    }


# =========================================================================
# Segundo fator: código por e-mail para professor e administração
# =========================================================================
#
# Decisão da instituição: quem mexe em nota, material e conta de outras
# pessoas entra com a senha **e** um código que chega no e-mail. O aluno,
# não — o que ele alcança é só dele, e o atrito de todo dia pesaria mais.
#
# O código vale VALIDADE_DO_CODIGO, aceita MAX_TENTATIVAS_CODIGO palpites e
# pode ser reenviado MAX_REENVIOS vezes, com um intervalo entre um e outro.
# Ele não é guardado: fica o hash dele com o desafio (um segredo aleatório
# por login), e a comparação é de tempo constante.

TIPOS_COM_SEGUNDO_FATOR = {"adm", "professor"}
VALIDADE_DO_CODIGO = timedelta(minutes=10)
MAX_TENTATIVAS_CODIGO = 5
MAX_REENVIOS = 3
INTERVALO_REENVIO = timedelta(seconds=60)


def _agora_utc() -> datetime:
    return datetime.now(timezone.utc)


def _hash_do_codigo(desafio: str, codigo: str) -> str:
    return hashlib.sha256(f"{desafio}:{codigo}".encode()).hexdigest()


def _mascarar(email: str) -> str:
    """"pr*******@deltacare.com": diz para onde foi sem mostrar o endereço inteiro."""
    usuario, _, dominio = email.partition("@")
    return f"{usuario[:2]}{'*' * max(len(usuario) - 2, 3)}@{dominio}"


def _enviar_codigo(email: str, nome: str, codigo: str) -> None:
    from infra.email import enviar_em_segundo_plano

    minutos = int(VALIDADE_DO_CODIGO.total_seconds() // 60)
    enviar_em_segundo_plano(
        email,
        "Delta Care — seu código de acesso",
        f"Olá{', ' + nome.split()[0] if nome else ''}.\n\n"
        f"Seu código para entrar no Delta Care é: {codigo}\n\n"
        f"Ele vale por {minutos} minutos e só serve uma vez.\n\n"
        "Se não foi você que tentou entrar, alguém sabe a sua senha: troque-a no perfil "
        "e avise a administração.\n",
    )


def _iniciar_segundo_fator(user_id: int, email: str, nome: str) -> dict:
    desafio = secrets.token_urlsafe(32)
    codigo = f"{secrets.randbelow(10 ** 6):06d}"
    agora = _agora_utc()
    conexao = _conectar()
    # Um desafio por pessoa: entrar de novo invalida o código anterior.
    conexao.execute("DELETE FROM desafios_login WHERE user_id = ? OR expira_em < ?", (user_id, agora.isoformat()))
    conexao.execute(
        "INSERT INTO desafios_login (desafio, user_id, codigo_hash, criado_em, expira_em, ultimo_envio)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (desafio, user_id, _hash_do_codigo(desafio, codigo), agora.isoformat(),
         (agora + VALIDADE_DO_CODIGO).isoformat(), agora.isoformat()),
    )
    conexao.commit()
    conexao.close()
    _enviar_codigo(email, nome, codigo)
    return {
        "sucesso": True,
        "segundo_fator": True,
        "desafio": desafio,
        "email_mascarado": _mascarar(email),
        "mensagem": "Enviamos um código de 6 dígitos para o seu e-mail.",
    }


def _desafio(conexao, desafio: str):
    return conexao.execute(
        "SELECT d.user_id, d.codigo_hash, d.expira_em, d.tentativas, d.reenvios, d.ultimo_envio,"
        "       u.email, u.tipo, u.nome, u.senha_provisoria, u.desativado_em"
        "  FROM desafios_login d JOIN users u ON u.id = d.user_id WHERE d.desafio = ?",
        ((desafio or "").strip(),),
    ).fetchone()


def confirmar_codigo(desafio: str, codigo: str) -> dict:
    """O código do e-mail confere: abre a sessão (o mesmo retorno do login)."""
    desafio = (desafio or "").strip()
    conexao = _conectar()
    linha = _desafio(conexao, desafio)
    if not linha:
        conexao.close()
        return {"sucesso": False, "expirado": True, "mensagem": "Este código não vale mais. Entre de novo para receber outro."}

    user_id, codigo_hash, expira_em, tentativas, _, _, email, tipo, nome, senha_provisoria, desativado_em = linha
    if datetime.fromisoformat(expira_em) < _agora_utc() or desativado_em:
        conexao.execute("DELETE FROM desafios_login WHERE desafio = ?", (desafio,))
        conexao.commit()
        conexao.close()
        return {"sucesso": False, "expirado": True, "mensagem": "O código expirou. Entre de novo para receber outro."}

    if not hmac.compare_digest(_hash_do_codigo(desafio, (codigo or "").strip()), codigo_hash):
        # Cada código errado conta como erro de login (ver _abrir_sessao).
        conexao.execute("INSERT INTO tentativas_login (email, criado_em) VALUES (?, ?)",
                        (email, datetime.utcnow().isoformat()))
        tentativas += 1
        if tentativas >= MAX_TENTATIVAS_CODIGO:
            conexao.execute("DELETE FROM desafios_login WHERE desafio = ?", (desafio,))
            conexao.commit()
            conexao.close()
            return {"sucesso": False, "expirado": True, "mensagem": "Código errado vezes demais. Entre de novo para receber outro."}
        conexao.execute("UPDATE desafios_login SET tentativas = ? WHERE desafio = ?", (tentativas, desafio))
        conexao.commit()
        conexao.close()
        restantes = MAX_TENTATIVAS_CODIGO - tentativas
        return {"sucesso": False, "mensagem": f"Código incorreto. Restam {restantes} tentativa(s)."}

    conexao.execute("DELETE FROM desafios_login WHERE desafio = ?", (desafio,))
    conexao.commit()
    conexao.close()
    return _abrir_sessao(user_id, email, tipo, nome, senha_provisoria)


def reenviar_codigo(desafio: str) -> dict:
    """Um código novo para o mesmo login (o anterior deixa de valer)."""
    desafio = (desafio or "").strip()
    conexao = _conectar()
    linha = _desafio(conexao, desafio)
    agora = _agora_utc()
    if not linha or datetime.fromisoformat(linha[2]) < agora:
        conexao.close()
        return {"sucesso": False, "expirado": True, "mensagem": "Este login expirou. Entre de novo."}
    user_id, _, _, _, reenvios, ultimo_envio, email, _, nome, _, _ = linha
    if reenvios >= MAX_REENVIOS:
        conexao.close()
        return {"sucesso": False, "expirado": True, "mensagem": "Já reenviamos o código vezes demais. Entre de novo."}
    espera = datetime.fromisoformat(ultimo_envio) + INTERVALO_REENVIO - agora
    if espera.total_seconds() > 0:
        conexao.close()
        return {"sucesso": False, "mensagem": f"Aguarde {int(espera.total_seconds()) + 1} segundos para pedir outro código."}

    codigo = f"{secrets.randbelow(10 ** 6):06d}"
    conexao.execute(
        "UPDATE desafios_login SET codigo_hash = ?, tentativas = 0, reenvios = reenvios + 1, ultimo_envio = ?,"
        " expira_em = ? WHERE desafio = ?",
        (_hash_do_codigo(desafio, codigo), agora.isoformat(), (agora + VALIDADE_DO_CODIGO).isoformat(), desafio),
    )
    conexao.commit()
    conexao.close()
    _enviar_codigo(email, nome, codigo)
    return {"sucesso": True, "mensagem": "Enviamos um código novo. O anterior não vale mais."}


def email_do_desafio(desafio: str) -> str:
    """De quem é este login em andamento — para a trilha de auditoria."""
    conexao = _conectar()
    linha = _desafio(conexao, desafio)
    conexao.close()
    return linha[6] if linha else ""


def criar_conta_staff(
    admin_email: str,
    email: str,
    senha: str,
    tipo: str,
    nome: str = "",
    disciplinas: str = "",
    matricula: str = "",
    turma_id: int | None = None,
    provisoria: bool = True,
    conferir_senha: bool = True,
    segundo_fator: bool = True,
) -> dict:
    """Cria conta de qualquer perfil. Só um admin já existente pode chamar
    isso (mesmo padrão de permissão usado em regras/turmas.criar_turma).

    É o **único** jeito de uma conta nascer pela API, inclusive a de aluno.
    Existiu um cadastro público de aluno (`POST /cadastro`); saiu porque
    nenhuma tela o usava e ele deixava qualquer pessoa da internet criar conta
    e esperar uma matrícula. Numa faculdade quem é aluno é decidido pela
    secretaria, não por quem preenche um formulário.

    `disciplinas` só vale para professor e `matricula` só para aluno; cada um é
    ignorado nos outros perfis em vez de dar erro, para o formulário poder
    enviar sempre o mesmo corpo. `turma_id` matricula o aluno já na criação —
    é o que evita cadastrar a turma inteira e depois matricular um a um.

    `segundo_fator=False` dispensa o código por e-mail de professor e
    administração — só nas contas de demonstração e nos testes, como o resto.

    `conferir_senha=False` só para as contas de demonstração do seed (senha
    `demo123`, que todo mundo conhece e que o seed avisa para nunca usar em
    produção). Toda conta de verdade passa por regras/senhas.py.
    """
    admin_email = admin_email.strip().lower()
    email = email.strip().lower()
    tipo = tipo.strip().lower()
    nome = (nome or "").strip()

    if tipo not in ("professor", "adm", "aluno"):
        return {"sucesso": False, "mensagem": "Tipo inválido. Use 'aluno', 'professor' ou 'adm'."}

    if not nome:
        return {"sucesso": False, "mensagem": "Informe o nome completo."}

    problema = problema_da_senha(senha, email, nome) if conferir_senha else None
    if problema:
        return {"sucesso": False, "mensagem": problema}

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
        # `provisoria` é o padrão de propósito: a senha foi escolhida por quem
        # criou a conta, não pelo dono — e, na planilha, é a mesma para a turma
        # inteira. O dono troca no primeiro acesso. Quem não deve ser forçado
        # (contas de demonstração, fixtures de teste) diz isso explicitamente.
        "INSERT INTO users (email, senha, tipo, nome, disciplinas, matricula, senha_provisoria, segundo_fator)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            email,
            hash_senha(senha),
            tipo,
            nome,
            (disciplinas or "").strip() if tipo == "professor" else None,
            (matricula or "").strip() if tipo == "aluno" else None,
            1 if provisoria else 0,
            1 if segundo_fator else 0,
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

    # Conta desativada recebe o mesmo silêncio que conta inexistente: trocar a
    # senha não a reativa, então mandar código seria só ruído.
    cursor.execute("SELECT id FROM users WHERE email = ? AND desativado_em IS NULL", (email,))
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

    problema = problema_da_senha(nova_senha, email)
    if problema:
        return {"sucesso": False, "mensagem": problema}

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
        " reset_tentativas = 0, senha_provisoria = 0 WHERE id = ?",
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


def alterar_senha(email: str, token_atual: str, senha_atual: str, nova_senha: str) -> dict:
    """O próprio usuário troca a senha — obrigatório no primeiro acesso com
    senha provisória, e possível a qualquer momento pelo perfil.

    Pede a senha atual: com a sessão aberta num computador do laboratório,
    outra pessoa trocaria a senha do dono e tomaria a conta. Ao trocar, as
    outras sessões dele caem (a senha antiga pode ter vazado); a de agora fica.
    """
    problema = problema_da_senha(nova_senha, email)
    if problema:
        return {"sucesso": False, "mensagem": problema}
    if nova_senha == senha_atual:
        return {"sucesso": False, "mensagem": "A nova senha precisa ser diferente da atual."}

    conexao = _conectar()
    linha = conexao.execute("SELECT id, senha FROM users WHERE email = ?", (email.strip().lower(),)).fetchone()
    if not linha or not verificar_senha(senha_atual or "", linha[1]):
        conexao.close()
        return {"sucesso": False, "mensagem": "A senha atual não confere."}

    conexao.execute("UPDATE users SET senha = ?, senha_provisoria = 0 WHERE id = ?", (hash_senha(nova_senha), linha[0]))
    conexao.execute("DELETE FROM sessoes WHERE user_id = ? AND token != ?", (linha[0], token_atual or ""))
    conexao.commit()
    conexao.close()
    return {"sucesso": True, "mensagem": "Senha alterada."}

