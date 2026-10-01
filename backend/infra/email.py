"""Envio de e-mail por SMTP, só com a biblioteca padrão.

Configurado por variável de ambiente, como o resto do sistema:

    DELTACARE_SMTP_HOST        smtp.instituicao.edu.br
    DELTACARE_SMTP_PORTA       587 (padrão)
    DELTACARE_SMTP_SEGURANCA   starttls (padrão) | ssl | nenhuma
    DELTACARE_SMTP_USUARIO     conta que autentica no servidor
    DELTACARE_SMTP_SENHA       senha dessa conta
    DELTACARE_SMTP_REMETENTE   "Delta Care <nao-responda@...>" (padrão: o usuário)

Sem DELTACARE_SMTP_HOST, nada é enviado: a mensagem vai para o console do
servidor, com um aviso dizendo isso. É o comportamento de desenvolvimento — e
o servidor avisa ao subir, para ninguém ir para produção achando que envia.

Nunca lança. Quem chama é uma ação do usuário (pedir código de recuperação), e
a falha do servidor de e-mail não pode virar erro na tela — nem, no caso da
recuperação, uma resposta diferente que revele se a conta existe.
"""

import os
import smtplib
import ssl
import threading
from email.message import EmailMessage

TIMEOUT_SEGUNDOS = 15


def _config() -> dict:
    usuario = os.environ.get("DELTACARE_SMTP_USUARIO", "").strip()
    return {
        "host": os.environ.get("DELTACARE_SMTP_HOST", "").strip(),
        "porta": int(os.environ.get("DELTACARE_SMTP_PORTA", "587") or 587),
        "seguranca": os.environ.get("DELTACARE_SMTP_SEGURANCA", "starttls").strip().lower(),
        "usuario": usuario,
        "senha": os.environ.get("DELTACARE_SMTP_SENHA", ""),
        "remetente": os.environ.get("DELTACARE_SMTP_REMETENTE", "").strip() or usuario,
    }


def email_configurado() -> bool:
    return bool(_config()["host"])


def enviar_email(destino: str, assunto: str, texto: str) -> bool:
    """Envia agora. Devolve se o servidor de e-mail aceitou a mensagem."""
    config = _config()

    if not config["host"]:
        print(
            "[Delta Care] E-mail NÃO enviado (DELTACARE_SMTP_HOST não definido).\n"
            f"  para: {destino}\n  assunto: {assunto}\n  {texto}"
        )
        return False

    mensagem = EmailMessage()
    mensagem["From"] = config["remetente"]
    mensagem["To"] = destino
    mensagem["Subject"] = assunto
    mensagem.set_content(texto)

    try:
        if config["seguranca"] == "ssl":
            servidor = smtplib.SMTP_SSL(
                config["host"], config["porta"],
                context=ssl.create_default_context(), timeout=TIMEOUT_SEGUNDOS,
            )
        else:
            servidor = smtplib.SMTP(config["host"], config["porta"], timeout=TIMEOUT_SEGUNDOS)

        with servidor:
            if config["seguranca"] == "starttls":
                servidor.starttls(context=ssl.create_default_context())
            if config["usuario"]:
                servidor.login(config["usuario"], config["senha"])
            servidor.send_message(mensagem)
        return True
    except (smtplib.SMTPException, OSError) as erro:
        # Sem o texto da mensagem no log: ele pode conter um código de
        # recuperação válido, e log costuma ser lido por mais gente.
        print(f"[Delta Care] Falha ao enviar e-mail para {destino}: {erro}")
        return False


def enviar_em_segundo_plano(destino: str, assunto: str, texto: str) -> threading.Thread:
    """Envia sem segurar a resposta da requisição.

    Na recuperação de senha isto não é só conforto: enviar e-mail leva um ou
    dois segundos, e só acontece quando a conta existe. Esperando o envio, a
    rota responderia mais devagar para conta real do que para inexistente — e o
    cronômetro voltaria a dizer quem é aluno, o vazamento que já fechamos no
    login e na mensagem desta mesma rota.
    """
    tarefa = threading.Thread(target=enviar_email, args=(destino, assunto, texto), daemon=True)
    tarefa.start()
    return tarefa
