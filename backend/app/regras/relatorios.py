"""Relatórios: a turma por mês, a turma agora, e onde os alunos mais erram.

Três leituras dos mesmos registros — entregas, acessos a material, conversas
com o assistente —, e nenhuma inventa número: mês sem registro aparece vazio,
e disciplina com pouca nota corrigida avisa que tem pouca nota corrigida.

**Quem vê o quê.** A administração vê todas as turmas; o professor, só as
disciplinas dele dentro da turma. Ninguém vê aluno identificado aqui: o
relatório é da turma. O professor que quer saber de um aluno tem a tela
Desempenho das disciplinas dele; a administração não tem — entregas e
conversas não são dela (ver regras/conteudo.py).

**Os números reaproveitam as regras de sempre**, para não haver dois jeitos
de calcular a mesma coisa: o aproveitamento é nota sobre pontos
(desempenho._percentual), o tópico que mais erra vem de
desempenho._erros_por_topico, e o XP é aluno.xp_no_periodo, com as mesmas
travas contra XP farmado.

**O mês é o do horário gravado (UTC).** Uma entrega às 22h do último dia, no
horário de Brasília, conta no mês seguinte. Três horas na virada não mudam a
leitura de um mês, e é a mesma régua do XP.
"""

from datetime import datetime, timedelta, timezone

from infra import fuso
from regras.aluno import xp_no_periodo
from regras.desempenho import _erros_por_topico, _percentual
from regras.semestres import semestre_vigente
from regras.turmas import buscar_usuario, conectar

# Aluno com aproveitamento médio abaixo disto conta como "com dificuldade".
LIMITE_DIFICULDADE = 60
# Menos notas corrigidas que isto, e a média de uma disciplina diz pouco.
MINIMO_DE_NOTAS = 5
# O painel ao vivo: o que conta como "agora" e quantos eventos mostra.
JANELA_AGORA = timedelta(hours=1)
JANELA_DIA = timedelta(hours=24)
EVENTOS_RECENTES = 12

COBERTURAS = ("completa", "parcial", "nenhuma", "sem_material")
MESES = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _quando(texto):
    """Data gravada → datetime com fuso (sem fuso = UTC). Inválida → None."""
    if not texto:
        return None
    try:
        data = datetime.fromisoformat(str(texto).replace("Z", "+00:00"))
    except ValueError:
        return None
    return data if data.tzinfo else data.replace(tzinfo=timezone.utc)


def _mes(texto) -> str | None:
    """O mês no fuso da instituição: a noite do dia 31 é do mês 31."""
    return fuso.mes(texto)


def _rotulo_do_mes(chave: str) -> str:
    ano, mes = chave.split("-")
    return f"{MESES[int(mes) - 1]}/{ano}"


def _media(valores):
    valores = [v for v in valores if v is not None]
    return round(sum(valores) / len(valores), 1) if valores else None


def _porcento(parte, total):
    return round(100 * parte / total, 1) if total else None


# =========================================================================
# Quem pode ver qual turma
# =========================================================================

def _quem(conexao, email: str):
    usuario = buscar_usuario(conexao, email)
    return (usuario[0], usuario[1]) if usuario and usuario[1] in ("adm", "professor") else (None, None)


def _disciplinas_da_turma(conexao, usuario_id: int, tipo: str, coorte_id: int) -> list:
    """(id, nome) das disciplinas da turma que essa pessoa pode ver."""
    sql = "SELECT id, nome FROM turmas WHERE coorte_id = ?"
    parametros = [int(coorte_id)]
    if tipo == "professor":
        sql += " AND professor_id = ?"
        parametros.append(usuario_id)
    return conexao.execute(sql + " ORDER BY nome", parametros).fetchall()


def turmas_para_relatorio(email: str) -> dict:
    """As turmas que aparecem no seletor: todas para a administração; para o
    professor, as que têm alguma disciplina dele."""
    conexao = conectar()
    try:
        usuario_id, tipo = _quem(conexao, email)
        if not usuario_id:
            return {"sucesso": False, "mensagem": "Relatórios são da administração e dos professores.", "turmas": []}
        sql = "SELECT DISTINCT c.id, c.nome, c.semestre FROM coortes c JOIN turmas t ON t.coorte_id = c.id"
        parametros = []
        if tipo == "professor":
            sql += " WHERE t.professor_id = ?"
            parametros.append(usuario_id)
        linhas = conexao.execute(sql + " ORDER BY c.semestre DESC, c.nome", parametros).fetchall()
    finally:
        conexao.close()
    return {
        "sucesso": True,
        "perfil": tipo,
        "turmas": [{"id": i, "nome": nome, "semestre": semestre} for i, nome, semestre in linhas],
    }


def _abrir(email: str, coorte_id: int):
    """Confere o acesso e devolve (conexao, turma, disciplinas) ou um erro."""
    conexao = conectar()
    usuario_id, tipo = _quem(conexao, email)
    if not usuario_id:
        conexao.close()
        return None, {"sucesso": False, "mensagem": "Relatórios são da administração e dos professores."}
    turma = conexao.execute("SELECT id, nome, semestre FROM coortes WHERE id = ?", (int(coorte_id),)).fetchone()
    disciplinas = _disciplinas_da_turma(conexao, usuario_id, tipo, coorte_id) if turma else []
    if not turma or not disciplinas:
        conexao.close()
        # A mesma resposta para turma que não existe e turma sem disciplina
        # dele: o professor não descobre por aqui quais turmas existem.
        return None, {"sucesso": False, "mensagem": "Turma não encontrada entre as suas."}
    return (conexao, {"id": turma[0], "nome": turma[1], "semestre": turma[2]}, disciplinas), None


# =========================================================================
# Os registros de que tudo é feito
# =========================================================================

def _registros(conexao, ids: list) -> dict:
    marcas = ",".join("?" * len(ids))
    return {
        "matriculas": conexao.execute(
            f"SELECT m.turma_id, m.aluno_id FROM matriculas m JOIN users u ON u.id = m.aluno_id"
            # Quem saiu (conta desativada) não conta como aluno que "não entregou".
            f" WHERE m.turma_id IN ({marcas}) AND u.tipo = 'aluno' AND u.desativado_em IS NULL", ids).fetchall(),
        "atividades": conexao.execute(
            f"SELECT id, turma_id, titulo, pontos, prazo, tipo, topico, assunto, data_liberacao FROM atividades"
            f" WHERE turma_id IN ({marcas}) AND rascunho = 0", ids).fetchall(),
        "entregas": conexao.execute(
            f"SELECT e.aluno_id, a.turma_id, e.atividade_id, e.enviado_em, e.nota, a.pontos, a.prazo, e.respostas"
            f"  FROM entregas e JOIN atividades a ON a.id = e.atividade_id"
            f" WHERE a.turma_id IN ({marcas}) AND e.enviado_em IS NOT NULL", ids).fetchall(),
        "acessos": conexao.execute(
            f"SELECT ac.aluno_id, m.turma_id, ac.material_id, ac.criado_em, m.titulo"
            f"  FROM acessos_material ac JOIN materiais m ON m.id = ac.material_id"
            f" WHERE m.turma_id IN ({marcas})", ids).fetchall(),
        "chat": conexao.execute(
            f"SELECT aluno_id, turma_id, papel, cobertura, criado_em FROM chat_mensagens"
            f" WHERE turma_id IN ({marcas})", ids).fetchall(),
    }


def _situacao_das_entregas(registros, turma_ids: set, agora: datetime):
    """Para cada (atividade com prazo vencido × aluno matriculado): no prazo,
    atrasada ou não entregue. Devolve uma lista (turma_id, mes_do_prazo, situacao).

    Atividade sem prazo não entra: não há "atrasado" sem data.
    """
    entregues = {(aluno, atividade): enviado for aluno, _, atividade, enviado, *_ in registros["entregas"]}
    alunos_da = {}
    for turma_id, aluno in registros["matriculas"]:
        alunos_da.setdefault(turma_id, set()).add(aluno)

    situacoes = []
    for atividade_id, turma_id, _, _, prazo_texto, *_ in registros["atividades"]:
        prazo = _quando(prazo_texto)
        if turma_id not in turma_ids or not prazo:
            continue
        for aluno in alunos_da.get(turma_id, ()):
            enviado = _quando(entregues.get((aluno, atividade_id)))
            if enviado:
                situacao = "no_prazo" if enviado <= prazo else "atrasadas"
            elif prazo < agora:
                situacao = "nao_entregues"
            else:
                continue  # ainda dá tempo: não é nada ainda
            situacoes.append((turma_id, _mes(prazo_texto), situacao))
    return situacoes


def _eventos_de_estudo(registros):
    """(aluno, turma_id, quando) de tudo que é o aluno estudando."""
    for aluno, turma_id, _, criado_em, _ in registros["acessos"]:
        yield aluno, turma_id, criado_em
    for aluno, turma_id, papel, _, criado_em in registros["chat"]:
        if papel == "user":
            yield aluno, turma_id, criado_em
    for aluno, turma_id, _, enviado_em, *_ in registros["entregas"]:
        yield aluno, turma_id, enviado_em


# =========================================================================
# 1. A turma mês a mês
# =========================================================================

def _bloco_vazio():
    return {
        "notas": {"aproveitamento": None, "corrigidas": 0},
        "entregas": {"no_prazo": 0, "atrasadas": 0, "nao_entregues": 0},
        "engajamento": {"alunos_ativos": 0, "alunos": 0, "dias_de_estudo_por_aluno": None, "materiais_abertos": 0, "xp_medio": None},
        "chat": {"perguntas": 0, **{c: 0 for c in COBERTURAS}},
    }


def relatorio_mensal(email: str, coorte_id: int) -> dict:
    aberto, erro = _abrir(email, coorte_id)
    if erro:
        return erro
    conexao, turma, disciplinas = aberto
    try:
        ids = [d[0] for d in disciplinas]
        registros = _registros(conexao, ids)
        agora = _agora()

        # Os meses: do primeiro registro até hoje. Mês sem nada no meio aparece
        # (zerado); antes do primeiro registro, não — seria só ruído.
        datas = [_mes(q) for *_, q in _eventos_de_estudo(registros)]
        datas += [_mes(a[4]) for a in registros["atividades"] if _quando(a[4]) and _quando(a[4]) < agora]
        datas = sorted(d for d in datas if d)
        if not datas:
            return {"sucesso": True, "turma": turma, "disciplinas": [{"id": i, "nome": n} for i, n in disciplinas], "meses": []}
        meses = []
        ano, mes = map(int, datas[0].split("-"))
        fim = agora.astimezone(fuso.FUSO).strftime("%Y-%m")
        while f"{ano:04d}-{mes:02d}" <= max(fim, datas[-1]):
            meses.append(f"{ano:04d}-{mes:02d}")
            ano, mes = (ano + 1, 1) if mes == 12 else (ano, mes + 1)

        blocos = {(m, t): _bloco_vazio() for m in meses for t in ids + ["total"]}
        alunos_da = {}
        for turma_id, aluno in registros["matriculas"]:
            alunos_da.setdefault(turma_id, set()).add(aluno)
        todos_os_alunos = set().union(*alunos_da.values()) if alunos_da else set()

        # Notas, pelo mês em que o aluno entregou.
        percentuais = {}
        for _, turma_id, _, enviado, nota, pontos, *_ in registros["entregas"]:
            p = _percentual(nota, pontos)
            if p is not None and _mes(enviado) in meses:
                for chave in (turma_id, "total"):
                    percentuais.setdefault((_mes(enviado), chave), []).append(p)
        for (m, chave), lista in percentuais.items():
            blocos[(m, chave)]["notas"] = {"aproveitamento": _media(lista), "corrigidas": len(lista)}

        # Entregas, pelo mês do prazo.
        for turma_id, m, situacao in _situacao_das_entregas(registros, set(ids), agora):
            if m in meses:
                for chave in (turma_id, "total"):
                    blocos[(m, chave)]["entregas"][situacao] += 1

        # Engajamento.
        ativos, dias = {}, {}
        for aluno, turma_id, quando in _eventos_de_estudo(registros):
            m = _mes(quando)
            if m not in meses:
                continue
            for chave in (turma_id, "total"):
                ativos.setdefault((m, chave), set()).add(aluno)
                dias.setdefault((m, chave), set()).add((aluno, fuso.dia(quando)))
        abertos = {}
        for aluno, turma_id, material_id, criado_em, _ in registros["acessos"]:
            m = _mes(criado_em)
            if m in meses:
                for chave in (turma_id, "total"):
                    abertos.setdefault((m, chave), set()).add((aluno, material_id))
        for m in meses:
            for chave in ids + ["total"]:
                bloco = blocos[(m, chave)]["engajamento"]
                quem = ativos.get((m, chave), set())
                bloco["alunos"] = len(todos_os_alunos if chave == "total" else alunos_da.get(chave, ()))
                bloco["alunos_ativos"] = len(quem)
                bloco["dias_de_estudo_por_aluno"] = round(len(dias[(m, chave)]) / len(quem), 1) if quem else None
                bloco["materiais_abertos"] = len(abertos.get((m, chave), ()))

        # XP do mês, só no total da turma: XP é do aluno, não da disciplina.
        # xp_no_periodo conta "de um dia em diante", então o do mês é a
        # diferença entre o começo dele e o começo do seguinte.
        cursor = conexao.cursor()
        inicios = [f"{m}-01" for m in meses]
        ano, mes = map(int, meses[-1].split("-"))
        inicios.append(f"{ano + 1:04d}-01-01" if mes == 12 else f"{ano:04d}-{mes + 1:02d}-01")
        xp_por_mes = {m: [] for m in meses}
        for aluno in todos_os_alunos:
            acumulado = [xp_no_periodo(cursor, aluno, set(ids), inicio) for inicio in inicios]
            for indice, m in enumerate(meses):
                xp_por_mes[m].append(acumulado[indice] - acumulado[indice + 1])
        for m in meses:
            blocos[(m, "total")]["engajamento"]["xp_medio"] = _media(xp_por_mes[m])

        # Chat de IA: perguntas e o quanto o material cobriu. Nunca o texto.
        for _, turma_id, papel, cobertura, criado_em in registros["chat"]:
            m = _mes(criado_em)
            if m not in meses:
                continue
            for chave in (turma_id, "total"):
                bloco = blocos[(m, chave)]["chat"]
                if papel == "user":
                    bloco["perguntas"] += 1
                elif cobertura in COBERTURAS:
                    bloco[cobertura] += 1
    finally:
        conexao.close()

    return {
        "sucesso": True,
        "turma": turma,
        "disciplinas": [{"id": i, "nome": n} for i, n in disciplinas],
        "limite_dificuldade": LIMITE_DIFICULDADE,
        "meses": [
            {
                "mes": m,
                "rotulo": _rotulo_do_mes(m),
                "total": blocos[(m, "total")],
                "disciplinas": [{"id": i, "nome": n, **blocos[(m, i)]} for i, n in disciplinas],
            }
            for m in meses
        ],
    }


# =========================================================================
# 2. A turma agora
# =========================================================================

def painel_ao_vivo(email: str, coorte_id: int) -> dict:
    """O que está acontecendo: última hora, últimas 24 horas, atividades em
    aberto e os eventos mais recentes — sem nome de aluno."""
    aberto, erro = _abrir(email, coorte_id)
    if erro:
        return erro
    conexao, turma, disciplinas = aberto
    try:
        ids = [d[0] for d in disciplinas]
        nomes = dict(disciplinas)
        registros = _registros(conexao, ids)
    finally:
        conexao.close()
    agora = _agora()

    def recente(quando, janela):
        data = _quando(quando)
        return bool(data and agora - janela <= data <= agora)

    eventos = list(_eventos_de_estudo(registros))
    perguntas = [c for c in registros["chat"] if c[2] == "user"]
    alunos_da = {}
    for turma_id, aluno in registros["matriculas"]:
        alunos_da.setdefault(turma_id, set()).add(aluno)

    # Atividades em aberto: publicadas, liberadas, com prazo por vir.
    entregas_por_atividade = {}
    for aluno, _, atividade_id, _, nota, pontos, *_ in registros["entregas"]:
        entregas_por_atividade.setdefault(atividade_id, []).append(_percentual(nota, pontos))
    abertas = []
    for atividade_id, turma_id, titulo, _, prazo_texto, *_, liberacao in registros["atividades"]:
        prazo = _quando(prazo_texto)
        liberada = _quando(liberacao)
        if not prazo or prazo < agora or (liberada and liberada > agora):
            continue
        notas = entregas_por_atividade.get(atividade_id, [])
        abertas.append({
            "titulo": titulo,
            "disciplina": nomes[turma_id],
            "prazo": prazo.isoformat(),
            "entregues": len(notas),
            "alunos": len(alunos_da.get(turma_id, ())),
            "aproveitamento": _media(notas),
        })
    abertas.sort(key=lambda a: a["prazo"])

    # O semestre até agora, por disciplina.
    situacoes = _situacao_das_entregas(registros, set(ids), agora)
    resumo = []
    for turma_id, nome in disciplinas:
        notas = [_percentual(n, p) for _, t, _, _, n, p, *_ in registros["entregas"] if t == turma_id]
        devidas = [s for t, _, s in situacoes if t == turma_id]
        resumo.append({
            "id": turma_id,
            "nome": nome,
            "alunos": len(alunos_da.get(turma_id, ())),
            "aproveitamento": _media(notas),
            "no_prazo": _porcento(devidas.count("no_prazo"), len(devidas)),
            "ativos_7_dias": len({a for a, t, q in eventos if t == turma_id and recente(q, timedelta(days=7))}),
        })

    # Os últimos eventos, para a tela "mexer" quando alguém estuda.
    titulos_atividade = {a[0]: a[2] for a in registros["atividades"]}
    recentes = (
        [{"tipo": "entrega", "disciplina": nomes[t], "detalhe": titulos_atividade.get(atv, ""), "quando": q}
         for _, t, atv, q, *_ in registros["entregas"]]
        + [{"tipo": "material", "disciplina": nomes[t], "detalhe": titulo, "quando": q}
           for _, t, _, q, titulo in registros["acessos"]]
        + [{"tipo": "pergunta", "disciplina": nomes[t], "detalhe": "", "quando": q} for _, t, _, _, q in perguntas]
    )
    recentes = sorted((e for e in recentes if _quando(e["quando"])), key=lambda e: _quando(e["quando"]), reverse=True)

    return {
        "sucesso": True,
        "turma": turma,
        "gerado_em": agora.isoformat(),
        "agora": {"alunos_ativos": len({a for a, _, q in eventos if recente(q, JANELA_AGORA)})},
        "ultimas_24h": {
            "alunos_ativos": len({a for a, _, q in eventos if recente(q, JANELA_DIA)}),
            "perguntas": sum(1 for *_, q in perguntas if recente(q, JANELA_DIA)),
            "materiais_abertos": sum(1 for *_, q, _ in registros["acessos"] if recente(q, JANELA_DIA)),
            "entregas": sum(1 for _, _, _, q, *_ in registros["entregas"] if recente(q, JANELA_DIA)),
        },
        "atividades_abertas": abertas,
        "disciplinas": resumo,
        "recentes": recentes[:EVENTOS_RECENTES],
    }


# =========================================================================
# 3. Onde os alunos mais têm dificuldade (administração)
# =========================================================================

def dificuldade_por_disciplina(admin_email: str, semestre: str | None = None) -> dict:
    """As disciplinas do semestre, da mais difícil para a mais fácil.

    "Mais difícil" é o **aproveitamento médio mais baixo** — nota sobre
    pontos das atividades corrigidas. Não há índice composto: um peso
    inventado entre nota, atraso e pergunta sem resposta esconderia por que
    uma disciplina subiu na lista. Os outros sinais aparecem ao lado, cada um
    com o seu número, e a coordenação lê os dois juntos.
    """
    conexao = conectar()
    try:
        usuario = buscar_usuario(conexao, admin_email)
        if not usuario or usuario[1] != "adm":
            return {"sucesso": False, "mensagem": "Acesso restrito à administração."}
        semestre = semestre or semestre_vigente()
        disciplinas = conexao.execute(
            "SELECT t.id, t.nome, c.nome, COALESCE(u.nome, u.email) FROM turmas t"
            "  LEFT JOIN coortes c ON c.id = t.coorte_id JOIN users u ON u.id = t.professor_id"
            " WHERE t.semestre = ? ORDER BY t.nome",
            (semestre,),
        ).fetchall()
        ids = [d[0] for d in disciplinas]
        registros = _registros(conexao, ids) if ids else None
        agora = _agora()
        situacoes = _situacao_das_entregas(registros, set(ids), agora) if ids else []
        linhas = []
        for turma_id, nome, nome_turma, professor in disciplinas:
            entregas = [e for e in registros["entregas"] if e[1] == turma_id]
            por_aluno = {}
            for aluno, _, _, _, nota, pontos, *_ in entregas:
                p = _percentual(nota, pontos)
                if p is not None:
                    por_aluno.setdefault(aluno, []).append(p)
            notas = [p for lista in por_aluno.values() for p in lista]
            devidas = [s for t, _, s in situacoes if t == turma_id]
            respostas = [c[3] for c in registros["chat"] if c[1] == turma_id and c[2] == "assistant" and c[3] in COBERTURAS]
            tipos = {a[0]: a for a in registros["atividades"]}
            objetivas = [(e[2], tipos[e[2]][6], tipos[e[2]][7], e[7]) for e in entregas
                         if e[2] in tipos and tipos[e[2]][5] == "objetiva"]
            topicos = _erros_por_topico(conexao, objetivas)
            linhas.append({
                "id": turma_id,
                "nome": nome,
                "turma": nome_turma,
                "professor": professor,
                "alunos": len({a for t, a in registros["matriculas"] if t == turma_id}),
                "aproveitamento": _media(notas),
                "corrigidas": len(notas),
                "poucos_dados": len(notas) < MINIMO_DE_NOTAS,
                "alunos_com_dificuldade": sum(1 for lista in por_aluno.values() if _media(lista) < LIMITE_DIFICULDADE),
                "alunos_com_nota": len(por_aluno),
                "nao_entregues": _porcento(devidas.count("nao_entregues"), len(devidas)),
                "atrasadas": _porcento(devidas.count("atrasadas"), len(devidas)),
                "perguntas_sem_resposta_completa": _porcento(sum(1 for c in respostas if c != "completa"), len(respostas)),
                "perguntas": sum(1 for c in registros["chat"] if c[1] == turma_id and c[2] == "user"),
                "topico_mais_errado": topicos[0] if topicos else None,
            })
    finally:
        conexao.close()

    # Sem nota nenhuma vai para o fim: não dá para dizer que é difícil nem fácil.
    linhas.sort(key=lambda d: (d["aproveitamento"] is None, d["aproveitamento"] or 0, -(d["nao_entregues"] or 0)))
    return {
        "sucesso": True,
        "semestre": semestre,
        "limite_dificuldade": LIMITE_DIFICULDADE,
        "minimo_de_notas": MINIMO_DE_NOTAS,
        "disciplinas": linhas,
    }
