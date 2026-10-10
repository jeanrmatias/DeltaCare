"""Trilha de auditoria: quem fez o quê, quando, de onde, e se deu certo.

Registra as ações que mexem em conta, permissão, matrícula e dado pessoal —
toda escrita da administração, as exclusões de conteúdo do professor, a cópia
de dados pessoais — e os eventos de acesso: login (certo, errado, bloqueado),
código de dois fatores, recuperação e troca de senha.

Quem registra é um ponto só, na entrada da API (`main.AuditarAcoes`): uma
rota nova de administração entra na trilha sem ninguém lembrar de chamar
nada. Aqui ficam o que guardar, como mostrar e quanto tempo manter.

**O que nunca entra:** senha, código de verificação, o desafio do login
em andamento, token, arquivo. O corpo
da requisição é filtrado antes de gravar (`_limpar`).

**Só a administração lê**, e a trilha não tem rota de escrita nem de
exclusão: ninguém apaga o próprio rastro pela API. Depois de
RETENCAO_DIAS, o registro sai sozinho (LGPD: guardar só enquanto serve).
Quando uma conta é anonimizada, o e-mail dela some da trilha também.
"""

import json
import re
from datetime import datetime, timedelta, timezone

from regras.turmas import buscar_usuario, conectar

RETENCAO_DIAS = 365
LIMITE_DA_LISTA = 300

# O que a ação é, em português. A chave é (verbo, rota como declarada no
# main.py). Rota sem rótulo aparece como está — é melhor que sumir.
ROTULOS = {
    ("POST", "/login"): "Login",
    ("POST", "/login/codigo"): "Código de verificação (2FA)",
    ("POST", "/login/codigo/reenviar"): "Reenvio do código (2FA)",
    ("POST", "/logout"): "Saída",
    ("POST", "/recuperar-senha"): "Pedido de recuperação de senha",
    ("POST", "/redefinir-senha"): "Senha redefinida pelo código",
    ("PUT", "/eu/senha"): "Troca da própria senha",
    ("GET", "/aluno/privacidade/exportar"): "Cópia dos próprios dados (LGPD)",
    ("POST", "/admin/usuarios"): "Conta criada",
    ("POST", "/admin/usuarios/exclusao"): "Conta excluída",
    ("POST", "/admin/importar"): "Planilha de alunos importada",
    ("POST", "/admin/turmas"): "Disciplina criada",
    ("DELETE", "/admin/turmas/{turma_id}"): "Disciplina excluída",
    ("PUT", "/admin/turmas/{turma_id}/professor"): "Professor da disciplina trocado",
    ("POST", "/admin/coortes"): "Turma criada",
    ("DELETE", "/admin/coortes/{coorte_id}"): "Turma desfeita",
    ("POST", "/admin/coortes/{coorte_id}/alunos"): "Aluno colocado na turma",
    ("DELETE", "/admin/coortes/{coorte_id}/alunos"): "Aluno tirado da turma",
    ("POST", "/admin/excecoes"): "Exceção de disciplina criada",
    ("DELETE", "/admin/excecoes"): "Exceção de disciplina removida",
    ("POST", "/admin/matriculas"): "Matrícula avulsa",
    ("DELETE", "/admin/matriculas"): "Matrícula removida",
    ("PUT", "/admin/semestre"): "Semestre vigente virado",
    ("POST", "/admin/denuncias/{denuncia_id}"): "Denúncia tratada",
    ("PUT", "/admin/privacidade/solicitacoes/{solicitacao_id}"): "Pedido de privacidade decidido",
    ("POST", "/admin/privacidade/solicitacoes/{solicitacao_id}/reverter"): "Exclusão de conta desfeita",
    ("DELETE", "/materiais/{material_id}"): "Material excluído",
    ("DELETE", "/chat/historico"): "Conversa com o assistente apagada",
    ("DELETE", "/atividades/{atividade_id}"): "Atividade excluída",
    ("DELETE", "/avisos/{aviso_id}"): "Aviso excluído",
}

# Rotas fora de /admin que também entram.
ROTAS_AUDITADAS = {chave for chave in ROTULOS if not chave[1].startswith("/admin/")}

# Campos que nunca vão para a trilha, em qualquer corpo.
_SIGILOSOS = ("senha", "token", "codigo", "desafio", "arquivo", "base64")


def auditar(metodo: str, rota: str) -> bool:
    """Essa requisição entra na trilha? `rota` como declarada ("/materiais/{material_id}")."""
    if metodo == "GET":
        return (metodo, rota) in ROTAS_AUDITADAS
    return rota.startswith("/admin/") or (metodo, rota) in ROTAS_AUDITADAS


# Antes de a rota ser resolvida só se tem o caminho concreto
# ("/materiais/12"). Isto decide, por ele, se vale guardar o corpo da
# requisição: ler e segurar o corpo de toda requisição (um upload de 15MB)
# para depois descobrir que ela não entra na trilha seria desperdício.
_PADROES = [
    (metodo, re.compile("^" + re.sub(r"\{[^}]+\}", "[^/]+", rota) + "$"))
    for metodo, rota in ROTAS_AUDITADAS
]


def candidata(metodo: str, caminho: str) -> bool:
    if metodo not in ("GET", "HEAD", "OPTIONS") and caminho.startswith("/admin/"):
        return True
    return any(metodo == m and padrao.match(caminho) for m, padrao in _PADROES)


def _sigilosa(chave) -> bool:
    return any(sigilo in str(chave).lower() for sigilo in _SIGILOSOS)


def _sem_sigilo(valor, profundidade: int = 0):
    """O valor sem as chaves sigilosas, em qualquer nível. Antes só o primeiro
    nível era filtrado: uma senha dentro de um objeto aninhado ia para a trilha
    inteira, no json.dumps da lista ou do dicionário."""
    if profundidade > 5:
        return "…"
    if isinstance(valor, dict):
        return {str(chave): _sem_sigilo(item, profundidade + 1) for chave, item in valor.items()
                if not _sigilosa(chave)}
    if isinstance(valor, list):
        return [_sem_sigilo(item, profundidade + 1) for item in valor[:20]]
    return valor


def _limpar(corpo) -> dict:
    if not isinstance(corpo, dict):
        return {}
    limpo = {}
    for chave, valor in corpo.items():
        if _sigilosa(chave):
            continue
        chave, valor = str(chave), _sem_sigilo(valor, 1)
        if isinstance(valor, str):
            valor = valor[:200]
        elif isinstance(valor, (list, dict)):
            valor = json.dumps(valor, ensure_ascii=False)[:200]
        limpo[chave] = valor
    return limpo


def registrar(metodo: str, rota: str, parametros: dict, corpo, quem: dict | None, email_informado: str,
              ip: str, status: int, resposta) -> None:
    """Grava uma linha. Nunca levanta: auditoria quebrada não pode derrubar a
    ação que ela está registrando (o erro vai para o log do servidor)."""
    resposta = resposta if isinstance(resposta, dict) else {}
    sucesso = status < 400 and resposta.get("sucesso", True) is not False
    detalhe = {"parametros": parametros or {}, "dados": _limpar(corpo)}
    conexao = conectar()
    try:
        conexao.execute(
            "INSERT INTO auditoria (criado_em, usuario_id, usuario_email, metodo, rota, detalhe, ip, status, sucesso, mensagem)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                datetime.now(timezone.utc).isoformat(),
                quem["id"] if quem else None,
                str(quem["email"] if quem else (email_informado or "")).strip().lower()[:200],
                metodo, rota, json.dumps(detalhe, ensure_ascii=False), ip or "", status, int(sucesso),
                str(resposta.get("mensagem") or (resposta.get("detail") if isinstance(resposta.get("detail"), str) else ""))[:300],
            ),
        )
        conexao.commit()
    except Exception as erro:  # noqa: BLE001 — ver docstring
        print(f"[Delta Care] Falha ao gravar a auditoria de {metodo} {rota}: {erro}")
    finally:
        conexao.close()


def listar(admin_email: str, acao: str = "", busca: str = "", dias: int | None = 30, so_falhas: bool = False) -> dict:
    conexao = conectar()
    try:
        usuario = buscar_usuario(conexao, admin_email)
        if not usuario or usuario[1] != "adm":
            return {"sucesso": False, "mensagem": "Acesso restrito à administração.", "registros": []}
        filtros, parametros = [], []
        if dias:
            filtros.append("criado_em >= ?")
            parametros.append((datetime.now(timezone.utc) - timedelta(days=int(dias))).isoformat())
        if acao and " " in acao:
            metodo, rota = acao.split(" ", 1)
            filtros.append("metodo = ? AND rota = ?")
            parametros += [metodo, rota]
        if busca:
            filtros.append("(usuario_email LIKE ? OR detalhe LIKE ? OR mensagem LIKE ? OR ip LIKE ?)")
            parametros += [f"%{busca.strip()}%"] * 4
        if so_falhas:
            filtros.append("sucesso = 0")
        onde = (" WHERE " + " AND ".join(filtros)) if filtros else ""
        linhas = conexao.execute(
            "SELECT id, criado_em, usuario_email, metodo, rota, detalhe, ip, status, sucesso, mensagem"
            f" FROM auditoria{onde} ORDER BY criado_em DESC, id DESC LIMIT ?",
            parametros + [LIMITE_DA_LISTA],
        ).fetchall()
    finally:
        conexao.close()

    registros = []
    for id_, quando, email, metodo, rota, detalhe, ip, status, sucesso, mensagem in linhas:
        try:
            detalhe = json.loads(detalhe or "{}")
        except ValueError:
            detalhe = {}
        registros.append({
            "id": id_, "quando": quando, "quem": email, "acao": ROTULOS.get((metodo, rota), f"{metodo} {rota}"),
            "rota": f"{metodo} {rota}", "detalhe": detalhe, "ip": ip, "status": status,
            "sucesso": bool(sucesso), "mensagem": mensagem,
        })
    return {
        "sucesso": True,
        "registros": registros,
        "limite": LIMITE_DA_LISTA,
        "retencao_dias": RETENCAO_DIAS,
        "acoes": [{"valor": f"{m} {r}", "rotulo": rotulo} for (m, r), rotulo in sorted(ROTULOS.items(), key=lambda i: i[1])],
    }


def expurgar_antigos(agora: datetime | None = None) -> int:
    """Apaga o que passou de RETENCAO_DIAS. Devolve quantos."""
    limite = ((agora or datetime.now(timezone.utc)) - timedelta(days=RETENCAO_DIAS)).isoformat()
    conexao = conectar()
    try:
        apagados = conexao.execute("DELETE FROM auditoria WHERE criado_em < ?", (limite,)).rowcount
        conexao.commit()
    finally:
        conexao.close()
    return apagados


def anonimizar_na_trilha(conexao, usuario_id: int, email_antigo: str, email_novo: str,
                         nome_antigo: str = "", nome_novo: str = "") -> None:
    """A conta anonimizada some da trilha também: o registro de que algo
    aconteceu fica; o e-mail e o nome de quem fez ou sofreu a ação, não (a
    mensagem pode ter o nome: "Conta de Rafael Moreira desativada"). Sem
    commit: roda dentro da anonimização (regras/privacidade.py)."""
    conexao.execute("UPDATE auditoria SET usuario_email = ? WHERE usuario_id = ? OR usuario_email = ?",
                    (email_novo, usuario_id, email_antigo))
    trocas = [(email_antigo, email_novo)] + ([(nome_antigo, nome_novo)] if nome_antigo and len(nome_antigo) >= 3 else [])
    for antigo, novo in trocas:
        conexao.execute("UPDATE auditoria SET detalhe = REPLACE(detalhe, ?, ?), mensagem = REPLACE(mensagem, ?, ?)"
                        " WHERE detalhe LIKE ? OR mensagem LIKE ?",
                        (antigo, novo, antigo, novo, f"%{antigo}%", f"%{antigo}%"))
