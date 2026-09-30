"""Visão do aluno: materiais liberados e resumo da tela inicial.

Separado de regras/materiais.py de propósito. Lá, toda consulta parte do
professor dono do material (`professor_id = ?`), e o professor enxerga também
rascunho e material agendado. O aluno tem outra regra, mais restritiva:

1. só vê turma em que está matriculado;
2. dentro dela, só vê material já publicado — nunca rascunho, nunca agendado
   para uma data futura.

Misturar as duas visões na mesma função convidaria a um erro de filtro que
vazaria material não liberado. Aqui a regra do aluno fica isolada e explícita.
"""

import re
from datetime import datetime, timedelta, timezone

from regras.turmas import buscar_usuario, conectar


def _esta_publicado(rascunho: int, data_liberacao) -> bool:
    """Mesma regra de regras/materiais._calcular_status, na forma de sim/não.

    Reaplicada aqui para não criar import cruzado (logica_materiais já importa
    de logica_turmas). Se a regra mudar, os três pontos precisam mudar juntos —
    o outro é regras/chat_ia._status_material.
    """
    if rascunho:
        return False

    if data_liberacao:
        try:
            liberacao = datetime.fromisoformat(data_liberacao)
            if liberacao.tzinfo is None:
                liberacao = liberacao.replace(tzinfo=timezone.utc)
            if liberacao > datetime.now(timezone.utc):
                return False
        except ValueError:
            # Data inválida no banco: tratamos como publicado, que é o
            # comportamento já adotado em logica_materiais.
            pass

    return True


def _buscar_aluno(conexao, aluno_email: str):
    aluno = buscar_usuario(conexao, aluno_email)
    if not aluno or aluno[1] != "aluno":
        return None
    return aluno


def material_visivel_para(conexao, aluno_id: int, material_id: int):
    """(titulo, turma_id) do material, se o aluno pode vê-lo. Senão, None.

    A mesma regra do download: matriculado na disciplina, e material publicado
    (não rascunho, e já liberado se agendado). Favoritar e anotar passam por
    aqui — senão dava para marcar, por id, um material que o aluno nem vê, e
    descobrir pelo título devolvido que ele existe.
    """
    linha = conexao.execute(
        """
        SELECT m.titulo, m.turma_id, m.rascunho, m.data_liberacao
          FROM materiais m JOIN matriculas mt ON mt.turma_id = m.turma_id
         WHERE m.id = ? AND mt.aluno_id = ?
        """,
        (int(material_id), aluno_id),
    ).fetchone()

    if not linha or not _esta_publicado(linha[2], linha[3]):
        return None
    return linha[0], linha[1]


def listar_materiais_do_aluno(aluno_email: str, turma_id: int | None = None) -> dict:
    """Materiais publicados das turmas em que o aluno está matriculado.

    Com `turma_id`, restringe a uma turma — e só devolve algo se o aluno
    estiver matriculado nela.
    """
    conexao = conectar()
    aluno = _buscar_aluno(conexao, aluno_email)

    if not aluno:
        conexao.close()
        return {"sucesso": False, "mensagem": "Aluno não encontrado.", "materiais": []}

    consulta = '''
        SELECT m.id, m.titulo, m.descricao, m.tipo, m.link_url, m.arquivo_nome,
               m.assunto, m.topico, m.aula, m.semestre, m.rascunho,
               m.data_liberacao, m.criado_em, m.turma_id, t.nome, u.email
        FROM materiais m
        JOIN turmas t ON t.id = m.turma_id
        JOIN matriculas mt ON mt.turma_id = m.turma_id
        LEFT JOIN users u ON u.id = m.professor_id
        WHERE mt.aluno_id = ?
    '''
    parametros = [aluno[0]]

    if turma_id is not None:
        consulta += " AND m.turma_id = ?"
        parametros.append(turma_id)

    consulta += " ORDER BY m.criado_em DESC"

    cursor = conexao.cursor()
    cursor.execute(consulta, parametros)
    linhas = cursor.fetchall()

    # Estrela e contagem de anotações vêm junto, para a lista não precisar de
    # uma chamada por material. Só as do próprio aluno, claro.
    favoritos = {
        linha[0] for linha in cursor.execute(
            "SELECT material_id FROM favoritos WHERE aluno_id = ?", (aluno[0],)
        ).fetchall()
    }
    anotacoes = dict(cursor.execute(
        "SELECT material_id, COUNT(*) FROM anotacoes"
        " WHERE aluno_id = ? AND material_id IS NOT NULL GROUP BY material_id",
        (aluno[0],),
    ).fetchall())
    conexao.close()

    materiais = []
    for linha in linhas:
        (id_, titulo, descricao, tipo, link_url, arquivo_nome, assunto, topico,
         aula, semestre, rascunho, data_liberacao, criado_em, turma, turma_nome,
         professor_email) = linha

        # O filtro acontece aqui, e não no SQL, porque "publicado" depende da
        # hora atual (material agendado vira publicado sozinho).
        if not _esta_publicado(rascunho, data_liberacao):
            continue

        materiais.append({
            "id": id_,
            "titulo": titulo,
            "descricao": descricao,
            "tipo": tipo,
            "link_url": link_url,
            "arquivo_nome": arquivo_nome,
            "assunto": assunto,
            "topico": topico,
            "aula": aula,
            "semestre": semestre,
            "criado_em": criado_em,
            "turma_id": turma,
            "turma_nome": turma_nome,
            "professor_email": professor_email,
            "favorito": id_ in favoritos,
            "total_anotacoes": anotacoes.get(id_, 0),
        })

    return {"sucesso": True, "materiais": materiais}


def obter_arquivo_material_do_aluno(aluno_email: str, material_id: int):
    """(caminho_no_disco, nome_original) se o aluno pode baixar o material.

    Devolve None quando o aluno não está matriculado na turma do material, o
    material não está publicado, ou não há arquivo — de fora, todos esses casos
    são iguais, para não revelar a existência de material que ele não pode ver.
    """
    conexao = conectar()
    aluno = _buscar_aluno(conexao, aluno_email)

    if not aluno:
        conexao.close()
        return None

    cursor = conexao.cursor()
    cursor.execute(
        '''
        SELECT m.arquivo_caminho, m.arquivo_nome, m.rascunho, m.data_liberacao
        FROM materiais m
        JOIN matriculas mt ON mt.turma_id = m.turma_id
        WHERE m.id = ? AND mt.aluno_id = ?
        ''',
        (material_id, aluno[0]),
    )
    linha = cursor.fetchone()
    conexao.close()

    if not linha:
        return None

    caminho, nome_original, rascunho, data_liberacao = linha

    if not caminho or not _esta_publicado(rascunho, data_liberacao):
        return None

    return caminho, nome_original


# Quanto vale cada ação no XP. Os pesos são pequenos e explicados na tela: um
# número de "pontos" que o aluno não sabe de onde vem não engaja, irrita.
XP_POR_PERGUNTA = 5
XP_POR_MATERIAL_ACESSADO = 15
XP_POR_DIA_ATIVO = 25

# Atividade entregue vale mais do que qualquer ação avulsa, e a nota vale mais
# ainda: é o único sinal que mede se o aluno **aprendeu**, e não só se usou a
# plataforma.
XP_POR_ATIVIDADE_ENTREGUE = 20
XP_MAXIMO_POR_NOTA = 30

# Teto de perguntas que pontuam por dia.
#
# Sem isso, o XP de pergunta é farmável: bastava mandar qualquer coisa no chat
# em sequência. Junto com as outras duas regras de `_perguntas_que_pontuam`,
# fecha o buraco por três lados — só conta pergunta respondida pelo material,
# só conta pergunta distinta, e só até este limite por dia.
MAX_PERGUNTAS_QUE_PONTUAM_POR_DIA = 5

# Quantos XP cada nível exige. Progressão linear de propósito: uma curva
# elaborada agora seria calibrada sobre menos dados do que o sistema vai ter
# depois de um semestre de uso.
XP_POR_NIVEL = 150

# Faixas do nível: bronze, prata, ouro, platina.
#
# **Os limites foram calculados, não escolhidos por gosto.** Rodando os pesos
# acima sobre um semestre de 20 semanas:
#
#     só entra, não estuda (1 dia/sem)      575 XP  ->  nível  4
#     regular (3 dias/sem)                 3.460 XP  ->  nível 24
#     dedicado (5 dias/sem)                8.108 XP  ->  nível 55
#     teto prático (6 dias/sem, tudo)     12.800 XP  ->  nível 86
#
# Daí as faixas: quem só aparece fica em Bronze o semestre inteiro, o aluno
# regular termina em Ouro, e Platina exige um semestre dedicado. O teto prático
# é 86, bem acima de Platina — chegar na última faixa não é o fim da linha, o
# nível continua subindo dentro dela.
#
# Ordem decrescente de propósito: `faixa_do_nivel` devolve a primeira que couber.
FAIXAS = (
    {"chave": "platina", "nome": "Platina", "nivel_minimo": 45},
    {"chave": "ouro", "nome": "Ouro", "nivel_minimo": 20},
    {"chave": "prata", "nome": "Prata", "nivel_minimo": 10},
    {"chave": "bronze", "nome": "Bronze", "nivel_minimo": 1},
)

DIAS_ACOMPANHAMENTO = 14


def faixa_do_nivel(nivel: int) -> dict:
    """A faixa do nível, e o que falta para a seguinte.

    `proxima` vem junto porque a tela mostra "faltam 3 níveis para Ouro": uma
    faixa sem próximo degrau visível é só um adjetivo. Em Platina vem `None`, e
    aí a tela não promete um degrau que não existe.

    Nível abaixo de 1 não deveria acontecer — `nivel` é `1 + xp // 150` e XP
    nunca é negativo — mas é limitado a 1 em vez de estourar, porque uma tela
    de progresso quebrada por um número estranho é pior que uma faixa errada.
    """
    # Com o piso em 1 e a última faixa começando em 1, o laço abaixo **sempre**
    # encontra alguma. Não há caminho de saída sem faixa, e é por isso que não
    # existe um `return` de reserva aqui: o que havia repetia "Bronze, próxima
    # Prata no nível 10" à mão, e passaria a mentir calado no dia em que os
    # limites de FAIXAS mudassem — sem nenhum teste capaz de notar.
    nivel = max(int(nivel), 1)

    for indice, faixa in enumerate(FAIXAS):
        if nivel >= faixa["nivel_minimo"]:
            anterior = FAIXAS[indice - 1] if indice > 0 else None
            return {
                "chave": faixa["chave"],
                "nome": faixa["nome"],
                "nivel_minimo": faixa["nivel_minimo"],
                "proxima": anterior["nome"] if anterior else None,
                "nivel_da_proxima": anterior["nivel_minimo"] if anterior else None,
            }

    raise AssertionError(
        f"FAIXAS não cobre o nível {nivel}: a última precisa ter nivel_minimo = 1"
    )


def registrar_acesso_material(aluno_email: str, material_id: int) -> None:
    """Anota que o aluno abriu um material.

    Silencioso de propósito: uma falha ao registrar estatística não pode
    impedir o download que o aluno pediu.
    """
    try:
        conexao = conectar()
        aluno = _buscar_aluno(conexao, aluno_email)

        if aluno:
            conexao.execute(
                "INSERT INTO acessos_material (aluno_id, material_id, criado_em) VALUES (?, ?, ?)",
                (aluno[0], material_id, datetime.now(timezone.utc).isoformat()),
            )
            conexao.commit()

        conexao.close()
    except Exception:
        pass


def _filtro_de_turmas(coluna: str, turmas) -> tuple:
    """Pedaço de SQL que restringe `coluna` às disciplinas dadas.

    `turmas=None` não filtra (é o XP de todos os semestres). Um conjunto vazio
    filtra tudo fora: aluno sem disciplina no semestre tem zero XP nele, e não
    o XP da vida inteira por engano.
    """
    if turmas is None:
        return "", []
    if not turmas:
        return " AND 0", []
    marcadores = ",".join("?" for _ in turmas)
    return f" AND {coluna} IN ({marcadores})", list(turmas)


def _normalizar_pergunta(texto: str) -> str:
    """Reduz a pergunta a uma chave, para reconhecer repetição.

    Minúsculas, sem pontuação e sem espaço sobrando: "Qual a dose?" e
    "qual a dose" viram a mesma coisa.
    """
    limpo = re.sub(r"[^\w\s]", " ", (texto or "").lower(), flags=re.UNICODE)
    return " ".join(limpo.split())


def _perguntas_que_pontuam(cursor, aluno_id: int, turmas=None, desde: str | None = None) -> int:
    """Quantas perguntas do aluno valem XP.

    Contar toda pergunta era um buraco: mandar qualquer coisa no chat dava
    pontos, e quem escrevesse "aaa" cinquenta vezes subia de nível sem estudar.
    Três filtros, nesta ordem:

    1. **Foi respondida pelo material.** A resposta do assistente guarda as
       fontes que citou; quando ele recusa ("não encontrei no material"), não
       há fonte. Pergunta recusada não pontua — o que se quer premiar é o aluno
       usando o material da turma, não o volume de mensagens.
    2. **É distinta.** Repetir a mesma pergunta não acumula.
    3. **Cabe no teto do dia.** Mesmo perguntas boas e diferentes param de
       pontuar depois de `MAX_PERGUNTAS_QUE_PONTUAM_POR_DIA`.

    O aluno continua podendo perguntar à vontade: o limite é só do XP.

    `desde` (AAAA-MM-DD) conta só as que pontuaram a partir daquele dia — mas
    as três regras rodam sobre o histórico inteiro, **antes** do recorte.
    Recortando primeiro, repetir uma pergunta de mês passado contaria como
    "nova" na semana, e a evolução semanal viraria o buraco que as regras
    fecharam.
    """
    filtro, valores = _filtro_de_turmas("p.turma_id", turmas)
    linhas = cursor.execute(
        """
        SELECT p.conteudo,
               substr(p.criado_em, 1, 10),
               (SELECT r.fontes
                  FROM chat_mensagens r
                 WHERE r.aluno_id = p.aluno_id
                   AND r.turma_id = p.turma_id
                   AND r.papel = 'assistant'
                   AND r.id > p.id
                 ORDER BY r.id
                 LIMIT 1)
          FROM chat_mensagens p
         WHERE p.aluno_id = ? AND p.papel = 'user'
        """ + filtro + """
         ORDER BY p.id
        """,
        [aluno_id] + valores,
    ).fetchall()

    ja_contadas = set()
    por_dia = {}
    total = 0

    for conteudo, dia, fontes in linhas:
        # `fontes` é NULL quando o assistente não citou nada (ver chat_ia).
        if not fontes or fontes.strip() in ("", "[]"):
            continue

        chave = _normalizar_pergunta(conteudo)
        if not chave or chave in ja_contadas:
            continue

        if por_dia.get(dia, 0) >= MAX_PERGUNTAS_QUE_PONTUAM_POR_DIA:
            continue

        ja_contadas.add(chave)
        por_dia[dia] = por_dia.get(dia, 0) + 1
        if desde is None or dia >= desde:
            total += 1

    return total


def _pontos_de_atividades(cursor, aluno_id: int, turmas=None, desde: str | None = None) -> tuple:
    """(entregues, corrigidas, XP vindo das notas).

    A nota vira XP proporcional aos pontos da atividade, então uma atividade
    de 10 e uma de 100 valem o mesmo esforço em XP — o que pesa é o acerto,
    não o tamanho da escala que o professor escolheu.
    """
    filtro, valores = _filtro_de_turmas("a.turma_id", turmas)
    if desde:
        filtro += " AND substr(e.enviado_em, 1, 10) >= ?"
        valores = valores + [desde]
    linhas = cursor.execute(
        """
        SELECT e.nota, a.pontos
          FROM entregas e
          JOIN atividades a ON a.id = e.atividade_id
         WHERE e.aluno_id = ? AND e.enviado_em IS NOT NULL
        """ + filtro,
        [aluno_id] + valores,
    ).fetchall()

    corrigidas = 0
    xp_das_notas = 0

    for nota, pontos in linhas:
        if nota is None or not pontos:
            continue
        corrigidas += 1
        proporcao = max(0.0, min(1.0, nota / pontos))
        xp_das_notas += round(XP_MAXIMO_POR_NOTA * proporcao)

    return len(linhas), corrigidas, xp_das_notas


def _dias_com_atividade(cursor, aluno_id: int, turmas=None) -> set:
    """Dias (AAAA-MM-DD) em que o aluno perguntou, abriu material ou entregou.

    Com `turmas`, só conta o dia em que a atividade foi numa dessas
    disciplinas — senão abrir material antigo no histórico daria dia ativo no
    semestre novo.
    """
    f_chat, v_chat = _filtro_de_turmas("turma_id", turmas)
    f_mat, v_mat = _filtro_de_turmas("m.turma_id", turmas)
    f_ent, v_ent = _filtro_de_turmas("a.turma_id", turmas)

    consulta = (
        "SELECT DISTINCT substr(criado_em, 1, 10) FROM chat_mensagens "
        "WHERE aluno_id = ? AND papel = 'user'" + f_chat + " "
        "UNION "
        "SELECT DISTINCT substr(ac.criado_em, 1, 10) FROM acessos_material ac "
        "JOIN materiais m ON m.id = ac.material_id "
        "WHERE ac.aluno_id = ?" + f_mat + " "
        "UNION "
        "SELECT DISTINCT substr(e.enviado_em, 1, 10) FROM entregas e "
        "JOIN atividades a ON a.id = e.atividade_id "
        "WHERE e.aluno_id = ? AND e.enviado_em IS NOT NULL" + f_ent
    )
    parametros = [aluno_id] + v_chat + [aluno_id] + v_mat + [aluno_id] + v_ent
    return {
        linha[0]
        for linha in cursor.execute(consulta, parametros).fetchall()
        if linha[0]
    }


def xp_no_periodo(cursor, aluno_id: int, turmas=None, desde: str | None = None) -> int:
    """XP do aluno nas disciplinas dadas, a partir de um dia (AAAA-MM-DD).

    Para o ranking: "quem mais evoluiu na semana". As regras que impedem
    farmar XP continuam valendo por inteiro, porque o recorte por data vem
    **depois** delas:

    - pergunta repetida de mês passado não vira nova na semana
      (ver `_perguntas_que_pontuam`);
    - material conta pela **primeira** abertura. Reabrir um PDF antigo nesta
      semana não é estudo novo, e sem isto bastaria reabrir tudo toda
      segunda-feira para liderar a evolução.
    """
    perguntas = _perguntas_que_pontuam(cursor, aluno_id, turmas, desde)

    filtro, valores = _filtro_de_turmas("m.turma_id", turmas)
    consulta = (
        "SELECT COUNT(*) FROM ("
        "  SELECT ac.material_id, MIN(ac.criado_em) AS primeira"
        "    FROM acessos_material ac JOIN materiais m ON m.id = ac.material_id"
        "   WHERE ac.aluno_id = ?" + filtro +
        "   GROUP BY ac.material_id"
        ")"
    )
    parametros = [aluno_id] + valores
    if desde:
        consulta += " WHERE substr(primeira, 1, 10) >= ?"
        parametros.append(desde)
    materiais = cursor.execute(consulta, parametros).fetchone()[0]

    entregas, _, xp_das_notas = _pontos_de_atividades(cursor, aluno_id, turmas, desde)
    dias = [dia for dia in _dias_com_atividade(cursor, aluno_id, turmas) if not desde or dia >= desde]

    return (
        perguntas * XP_POR_PERGUNTA
        + materiais * XP_POR_MATERIAL_ACESSADO
        + len(dias) * XP_POR_DIA_ATIVO
        + entregas * XP_POR_ATIVIDADE_ENTREGUE
        + xp_das_notas
    )


def _xp_de_todos_os_semestres(cursor, aluno_id: int) -> int:
    """O XP acumulado desde a primeira matrícula, sem recorte de semestre."""
    perguntas = _perguntas_que_pontuam(cursor, aluno_id)
    materiais = cursor.execute(
        "SELECT COUNT(DISTINCT material_id) FROM acessos_material WHERE aluno_id = ?",
        (aluno_id,),
    ).fetchone()[0]
    entregas, _, xp_das_notas = _pontos_de_atividades(cursor, aluno_id)
    dias = _dias_com_atividade(cursor, aluno_id)

    return (
        perguntas * XP_POR_PERGUNTA
        + materiais * XP_POR_MATERIAL_ACESSADO
        + len(dias) * XP_POR_DIA_ATIVO
        + entregas * XP_POR_ATIVIDADE_ENTREGUE
        + xp_das_notas
    )


def _calcular_progresso(aluno_id: int) -> dict:
    """XP e frequência de estudo, a partir do que o sistema registrou de fato.

    Nada aqui é estimado. Cada parcela tem um limite natural, de propósito:

    - **materiais** conta `DISTINCT`, então reabrir o mesmo PDF não acumula;
    - **dias** conta dia do calendário, então não dá para forçar;
    - **perguntas** passa pelos três filtros de `_perguntas_que_pontuam`;
    - **atividades** dependem do professor propor e corrigir.

    Um XP que sobe só porque o aluno clicou muito não mede estudo nenhum.

    **O nível e a faixa são do semestre vigente.** Somando a vida inteira,
    veterano era Platina para sempre e quem parasse de estudar continuava lá:
    a faixa premiava tempo de matrícula, não estudo. Cada fonte de XP aponta
    para uma disciplina, e a disciplina tem semestre, então o recorte não
    precisa de data nenhuma. O acumulado de todos os semestres continua
    calculado e vai junto (`xp_total`) — nada que o aluno fez some.
    """
    from regras.semestres import semestre_vigente

    vigente = semestre_vigente()

    conexao = conectar()
    cursor = conexao.cursor()

    turmas_do_semestre = {
        linha[0]
        for linha in cursor.execute(
            """
            SELECT t.id FROM matriculas m JOIN turmas t ON t.id = m.turma_id
             WHERE m.aluno_id = ? AND t.semestre = ?
            """,
            (aluno_id, vigente),
        ).fetchall()
    }

    perguntas = _perguntas_que_pontuam(cursor, aluno_id, turmas_do_semestre)

    # DISTINCT: reabrir o mesmo PDF cinco vezes não são cinco materiais
    # estudados.
    filtro, valores = _filtro_de_turmas("m.turma_id", turmas_do_semestre)
    materiais_acessados = cursor.execute(
        "SELECT COUNT(DISTINCT ac.material_id) FROM acessos_material ac"
        " JOIN materiais m ON m.id = ac.material_id WHERE ac.aluno_id = ?" + filtro,
        [aluno_id] + valores,
    ).fetchone()[0]

    entregas, corrigidas, xp_das_notas = _pontos_de_atividades(
        cursor, aluno_id, turmas_do_semestre
    )
    dias_ativos = _dias_com_atividade(cursor, aluno_id, turmas_do_semestre)
    xp_total = _xp_de_todos_os_semestres(cursor, aluno_id)
    conexao.close()

    xp = (
        perguntas * XP_POR_PERGUNTA
        + materiais_acessados * XP_POR_MATERIAL_ACESSADO
        + len(dias_ativos) * XP_POR_DIA_ATIVO
        + entregas * XP_POR_ATIVIDADE_ENTREGUE
        + xp_das_notas
    )

    hoje = datetime.now(timezone.utc).date()

    # Últimos dias para o gráfico, do mais antigo para o mais recente.
    acompanhamento = []
    for recuo in range(DIAS_ACOMPANHAMENTO - 1, -1, -1):
        dia = hoje - timedelta(days=recuo)
        acompanhamento.append({"dia": dia.isoformat(), "ativo": dia.isoformat() in dias_ativos})

    # Sequência de dias consecutivos. Começa de ontem quando hoje ainda não
    # teve atividade, senão a sequência zeraria toda manhã.
    sequencia = 0
    referencia = hoje if hoje.isoformat() in dias_ativos else hoje - timedelta(days=1)

    while referencia.isoformat() in dias_ativos:
        sequencia += 1
        referencia -= timedelta(days=1)

    nivel = 1 + xp // XP_POR_NIVEL

    return {
        "xp": xp,
        # O que o aluno juntou em todos os semestres. Não decide nível nem
        # faixa, mas aparece: zerar o número na virada sem mostrar o acumulado
        # pareceria que o sistema perdeu o histórico dele.
        "xp_total": xp_total,
        "semestre": vigente,
        "nivel": nivel,
        "xp_no_nivel": xp % XP_POR_NIVEL,
        "xp_para_proximo_nivel": XP_POR_NIVEL,
        # A faixa é calculada aqui, e não na tela: é regra de produto, e duas
        # telas decidindo sozinhas divergiriam na primeira vez que os limites
        # mudassem.
        "faixa": faixa_do_nivel(nivel),
        "perguntas": perguntas,
        "materiais_acessados": materiais_acessados,
        "atividades_entregues": entregas,
        "atividades_corrigidas": corrigidas,
        "dias_ativos": len(dias_ativos),
        "sequencia": sequencia,
        "acompanhamento": acompanhamento,
        # A composição vai para a tela: o aluno consegue ver de onde veio cada
        # ponto, em vez de receber um total sem explicação.
        "composicao": [
            {
                "rotulo": "Atividades entregues",
                "quantidade": entregas,
                "xp": entregas * XP_POR_ATIVIDADE_ENTREGUE,
            },
            {
                "rotulo": "Desempenho nas atividades",
                "quantidade": corrigidas,
                "xp": xp_das_notas,
            },
            {
                # "que contaram" e não "feitas": o aluno pode ter perguntado
                # mais. A tela precisa dizer a verdade sobre o que pontuou,
                # senão a conta não fecha para quem olha.
                "rotulo": "Perguntas que contaram",
                "quantidade": perguntas,
                "xp": perguntas * XP_POR_PERGUNTA,
            },
            {
                "rotulo": "Materiais consultados",
                "quantidade": materiais_acessados,
                "xp": materiais_acessados * XP_POR_MATERIAL_ACESSADO,
            },
            {
                "rotulo": "Dias de estudo",
                "quantidade": len(dias_ativos),
                "xp": len(dias_ativos) * XP_POR_DIA_ATIVO,
            },
        ],
    }


def resumo_do_aluno(aluno_email: str) -> dict:
    """Números e destaques da tela inicial do aluno.

    Tudo vem do banco: nada nesta tela é exemplo fixo.
    """
    from regras.matriculas import listar_turmas_do_aluno

    conexao = conectar()
    aluno = _buscar_aluno(conexao, aluno_email)

    if not aluno:
        conexao.close()
        return {"sucesso": False, "mensagem": "Aluno não encontrado."}

    aluno_id = aluno[0]

    cursor = conexao.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM chat_mensagens WHERE aluno_id = ? AND papel = 'user'",
        (aluno_id,),
    )
    perguntas_feitas = cursor.fetchone()[0]
    conexao.close()

    # A tela inicial é do semestre de agora. As disciplinas antigas continuam
    # acessíveis em Semestres anteriores e no seletor do chat; aqui, contá-las
    # faria o "8 disciplinas" de um aluno do 1º ano virar 32 no 4º.
    turmas = [
        t for t in listar_turmas_do_aluno(aluno_email).get("turmas", []) if t.get("vigente")
    ]
    ids_vigentes = {t["id"] for t in turmas}
    materiais = [
        m for m in listar_materiais_do_aluno(aluno_email).get("materiais", [])
        if m["turma_id"] in ids_vigentes
    ]

    # Quantos materiais por turma, para os cartões da tela inicial.
    por_turma = {}
    for material in materiais:
        por_turma[material["turma_id"]] = por_turma.get(material["turma_id"], 0) + 1

    for turma in turmas:
        turma["total_materiais"] = por_turma.get(turma["id"], 0)

    return {
        "sucesso": True,
        "total_turmas": len(turmas),
        "total_materiais": len(materiais),
        "perguntas_feitas": perguntas_feitas,
        "turmas": turmas,
        "materiais_recentes": materiais[:5],
        "progresso": _calcular_progresso(aluno_id),
    }
