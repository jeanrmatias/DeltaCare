"""Semestre vigente e o histórico de semestres anteriores.

Até aqui o sistema não sabia em que semestre estava. Tudo aparecia junto para
sempre: depois de quatro semestres o aluno teria trinta e tantas disciplinas no
seletor do chat, as antigas misturadas com as de agora. E o XP, que alimenta o
nível e a faixa, somava a vida inteira — veterano era Platina para sempre, e
quem parasse de estudar continuava lá.

Três peças:

1. **Um formato só.** O semestre era texto livre, e o banco tinha `2026.2`
   enquanto os formulários sugeriam `2026/2`. Comparados como texto, são
   semestres diferentes. Tudo passa por `normalizar_semestre` na entrada, e o
   que já estava gravado é convertido na migração (infra/database.py).

2. **O semestre vigente**, definido pela administração. Sem definição, vale o
   calendário (janeiro a junho é o 1º, julho a dezembro o 2º). O calendário é
   só o padrão porque a virada de verdade não cai no dia 1º de julho: há prova
   final, recuperação e lançamento de nota atravessando o mês, e virar sozinho
   tiraria as disciplinas da frente do aluno no meio disso.

3. **O histórico**: as disciplinas de semestres passados, com o material
   publicado, e busca por palavra — inclusive dentro do texto dos PDFs, que já
   está extraído para o chat de IA. Para quem vai prestar residência, é
   justamente o conteúdo antigo que importa.

Nada é apagado ao virar o semestre. Matrícula, material, entrega e nota
continuam no banco; o que muda é o que aparece na frente.
"""

import re
from datetime import date, datetime, timezone

from regras.turmas import _eh_admin, buscar_usuario, conectar

_FORMATO = re.compile(r"^\s*(\d{4})\s*[./\-\s]\s*([12])\s*$")


def normalizar_semestre(texto) -> str | None:
    """`2026.2`, `2026/2`, `2026-2` e `2026 2` viram `2026/2`. Resto: None.

    Aceita os separadores que as pessoas de fato digitam, em vez de recusar e
    fazer o admin adivinhar qual o sistema quer. O que sai é sempre o mesmo, e
    é isso que importa para comparar.
    """
    if texto is None:
        return None

    achado = _FORMATO.match(str(texto))
    if not achado:
        return None

    ano, periodo = achado.groups()
    if not 2000 <= int(ano) <= 2100:
        return None

    return f"{ano}/{periodo}"


def chave_de_ordem(semestre: str) -> tuple:
    """Para ordenar: (2026, 2). Semestre fora do formato vai para o começo."""
    normalizado = normalizar_semestre(semestre)
    if not normalizado:
        return (0, 0)
    ano, periodo = normalizado.split("/")
    return (int(ano), int(periodo))


def semestre_do_calendario(dia: date | None = None) -> str:
    dia = dia or datetime.now(timezone.utc).date()
    return f"{dia.year}/{1 if dia.month <= 6 else 2}"


def semestre_vigente() -> str:
    """O semestre que a administração definiu; sem definição, o do calendário."""
    conexao = conectar()
    linha = conexao.execute(
        "SELECT valor FROM configuracoes WHERE chave = 'semestre_vigente'"
    ).fetchone()
    conexao.close()

    if linha and normalizar_semestre(linha[0]):
        return normalizar_semestre(linha[0])
    return semestre_do_calendario()


def obter_semestre_vigente() -> dict:
    """Para a tela: o semestre e de onde ele veio."""
    conexao = conectar()
    linha = conexao.execute(
        "SELECT valor, atualizado_em FROM configuracoes WHERE chave = 'semestre_vigente'"
    ).fetchone()
    conexao.close()

    definido = bool(linha and normalizar_semestre(linha[0]))
    return {
        "sucesso": True,
        "semestre": normalizar_semestre(linha[0]) if definido else semestre_do_calendario(),
        # A tela mostra "pelo calendário" quando ninguém definiu: o admin
        # precisa saber que a virada vai acontecer sozinha em julho/janeiro
        # se ele não fizer nada.
        "definido_pela_administracao": definido,
        "atualizado_em": linha[1] if definido else None,
    }


def definir_semestre_vigente(admin_email: str, semestre: str) -> dict:
    normalizado = normalizar_semestre(semestre)
    if not normalizado:
        return {"sucesso": False, "mensagem": "Semestre inválido. Use o formato 2026/2."}

    conexao = conectar()

    if not _eh_admin(conexao, admin_email):
        conexao.close()
        return {"sucesso": False, "mensagem": "Só um administrador pode virar o semestre."}

    conexao.execute(
        """
        INSERT INTO configuracoes (chave, valor, atualizado_em)
        VALUES ('semestre_vigente', ?, ?)
        ON CONFLICT (chave) DO UPDATE SET valor = excluded.valor,
                                          atualizado_em = excluded.atualizado_em
        """,
        (normalizado, datetime.now(timezone.utc).isoformat()),
    )
    conexao.commit()
    conexao.close()

    return {"sucesso": True, "mensagem": f"Semestre vigente: {normalizado}.", "semestre": normalizado}


# =========================================================================
# Histórico
# =========================================================================

# Mesma regra de publicado de regras/aluno.py: rascunho nunca, agendado só
# depois da data. Repetida em SQL aqui porque o histórico filtra no banco, e
# a data de liberação de um semestre passado já passou de qualquer jeito.
_PUBLICADO = "m.rascunho = 0 AND (m.data_liberacao IS NULL OR m.data_liberacao <= ?)"


def _termo_de_busca(busca: str) -> str | None:
    busca = (busca or "").strip()
    if len(busca) < 3:
        # Duas letras casam com quase todo trecho de PDF e devolvem o arquivo
        # inteiro — não é busca, é listagem lenta.
        return None
    # O % e o _ digitados são texto, não curinga do LIKE.
    escapado = busca.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escapado}%"


def _montar_historico(linhas: list, trechos: dict, vigente: str) -> list:
    """Agrupa por semestre (mais recente primeiro) e, dentro, por disciplina."""
    semestres = {}

    for (turma_id, turma_nome, semestre, professor, material_id, titulo,
         tipo, descricao, assunto, topico, link_url, arquivo_nome) in linhas:
        normalizado = normalizar_semestre(semestre) or semestre

        grupo = semestres.setdefault(normalizado, {})
        disciplina = grupo.setdefault(turma_id, {
            "id": turma_id,
            "nome": turma_nome,
            "professor_nome": professor,
            "materiais": [],
        })

        if material_id is not None:
            disciplina["materiais"].append({
                "id": material_id,
                "titulo": titulo,
                "tipo": tipo,
                "descricao": descricao,
                "classificacao": " · ".join(p for p in (assunto, topico) if p),
                # Para a tela abrir o material pelo mesmo caminho da lista de
                # materiais: link abre direto, arquivo passa pela rota
                # autenticada (que confere a matrícula de novo).
                "link_url": link_url,
                "arquivo_nome": arquivo_nome,
                # O trecho do PDF onde a palavra apareceu: sem ele, o aluno
                # teria que abrir o arquivo para descobrir por que veio.
                "trecho": trechos.get(material_id),
            })

    return [
        {
            "semestre": semestre,
            "disciplinas": sorted(grupo.values(), key=lambda d: d["nome"]),
        }
        for semestre, grupo in sorted(
            semestres.items(), key=lambda par: chave_de_ordem(par[0]), reverse=True
        )
        if chave_de_ordem(semestre) < chave_de_ordem(vigente)
    ]


def _recorte(texto: str, busca: str, largura: int = 90) -> str:
    """O pedaço do texto em volta da palavra encontrada."""
    posicao = texto.lower().find(busca.strip().lower())
    if posicao < 0:
        return texto[: largura * 2].strip() + "…"
    inicio = max(posicao - largura, 0)
    fim = min(posicao + len(busca) + largura, len(texto))
    return ("…" if inicio else "") + texto[inicio:fim].strip() + ("…" if fim < len(texto) else "")


def _historico(filtro_sql: str, parametro_dono: int, busca: str) -> dict:
    vigente = semestre_vigente()
    agora = datetime.now(timezone.utc).isoformat()
    termo = _termo_de_busca(busca)

    conexao = conectar()

    consulta = f"""
        SELECT t.id, t.nome, t.semestre, COALESCE(u.nome, u.email),
               m.id, m.titulo, m.tipo, m.descricao, m.assunto, m.topico,
               m.link_url, m.arquivo_nome
          FROM turmas t
          JOIN users u ON u.id = t.professor_id
          LEFT JOIN materiais m ON m.turma_id = t.id AND {_PUBLICADO}
         WHERE {filtro_sql}
    """
    parametros = [agora, parametro_dono]

    trechos = {}
    if termo:
        # Casa no título, na descrição, na classificação **ou no texto do PDF**.
        # O texto já está extraído em material_chunks para o chat de IA; a busca
        # aproveita em vez de ler os arquivos de novo.
        consulta += """
           AND m.id IN (
                SELECT id FROM materiais
                 WHERE titulo LIKE ? ESCAPE '\\' OR descricao LIKE ? ESCAPE '\\'
                    OR assunto LIKE ? ESCAPE '\\' OR topico LIKE ? ESCAPE '\\'
                UNION
                SELECT material_id FROM material_chunks WHERE texto LIKE ? ESCAPE '\\'
           )
        """
        parametros += [termo] * 5

        for material_id, texto in conexao.execute(
            """
            SELECT c.material_id, c.texto FROM material_chunks c
             WHERE c.texto LIKE ? ESCAPE '\\'
             ORDER BY c.material_id, c.indice
            """,
            (termo,),
        ).fetchall():
            trechos.setdefault(material_id, _recorte(texto, busca))

    consulta += " ORDER BY t.semestre DESC, t.nome, m.titulo"
    linhas = conexao.execute(consulta, parametros).fetchall()
    conexao.close()

    semestres = _montar_historico(linhas, trechos, vigente)
    return {
        "sucesso": True,
        "semestre_vigente": vigente,
        "busca": busca.strip() if termo else "",
        "semestres": semestres,
    }


def historico_do_aluno(aluno_email: str, busca: str = "") -> dict:
    """Disciplinas que o aluno cursou em semestres anteriores ao vigente.

    Parte da matrícula, como o resto do sistema: quem não cursou a disciplina
    não vê o material dela, nem no histórico.
    """
    conexao = conectar()
    aluno = buscar_usuario(conexao, aluno_email)
    conexao.close()

    if not aluno or aluno[1] != "aluno":
        return {"sucesso": False, "mensagem": "Aluno não encontrado.", "semestres": []}

    return _historico(
        "t.id IN (SELECT turma_id FROM matriculas WHERE aluno_id = ?)", aluno[0], busca
    )


def historico_do_professor(professor_email: str, busca: str = "") -> dict:
    """Disciplinas que o professor deu em semestres anteriores ao vigente."""
    conexao = conectar()
    professor = buscar_usuario(conexao, professor_email)
    conexao.close()

    if not professor or professor[1] != "professor":
        return {"sucesso": False, "mensagem": "Professor não encontrado.", "semestres": []}

    return _historico("t.professor_id = ?", professor[0], busca)
