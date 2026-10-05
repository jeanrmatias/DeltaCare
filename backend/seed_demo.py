"""Cria os dados de demonstração do Delta Care do zero.

    python seed_demo.py

O banco (deltacare.db) não é versionado, então este script é o que torna a
demonstração reproduzível em qualquer máquina: contas dos três perfis, uma
turma com professor e aluno matriculado, e um PDF de exemplo já indexado para
o chat de IA.

Pode rodar mais de uma vez — o que já existe é reaproveitado, nada é duplicado.

A indexação do PDF precisa do Ollama no ar. Se ele não estiver, o resto do
seed é criado normalmente e o script avisa o que faltou.
"""

import os
import sqlite3
import sys

from infra.database import CAMINHO_DB, configurar_banco
from regras.autenticacao import criar_conta_staff
from regras.materiais import criar_material
from regras.matriculas import matricular_aluno
from regras.turmas import criar_turma
from infra.security import hash_senha
from material_demo import IC_AGUDA

SENHA_PADRAO = "demo123"

ADMIN = "adm@deltacare.com"
PROFESSOR = "professor@deltacare.com"
ALUNO = "aluno@deltacare.com"

NOME_ADMIN = "Helena Prado"
NOME_PROFESSOR = "Ricardo Salles"
NOME_ALUNO = "Marina Duarte"

DISCIPLINAS_PROFESSOR = "Cardiologia; Clínica Médica"
MATRICULA_ALUNO = "2026001234"

TURMA_NOME = "Cardiologia I"


def _semestre_vigente() -> str:
    """O semestre vem do sistema, e não fixo aqui.

    Era "2026.2" escrito à mão. Depois que o formato virou um só (2026/2), a
    busca por "2026.2" deixou de achar a disciplina, o seed tentava criar de
    novo, levava "já existe" e saía com erro — e a partir de 2027 a disciplina
    de demonstração viraria "semestre anterior" sozinha.
    """
    from regras.semestres import semestre_vigente

    return semestre_vigente()


TURMA_SEMESTRE = None  # resolvido em main(), depois de o banco existir

# Conteúdo médico real (material_demo.py): o primeiro PDF da demonstração.
MATERIAL_TITULO = IC_AGUDA["titulo"]
TEXTO_PDF = IC_AGUDA["texto"]


# =========================================================================
# Geração do PDF em Python puro
# =========================================================================
# Escrito à mão para o projeto não ganhar uma dependência (reportlab, fpdf) que
# só serviria para gerar um arquivo de exemplo.

def _escapar(texto: str) -> bytes:
    texto = texto.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
    return texto.encode("cp1252", errors="replace")


def gerar_pdf(texto: str, caminho: str, linhas_por_pagina: int = 46) -> None:
    linhas = texto.split("\n")
    paginas = [
        linhas[i:i + linhas_por_pagina]
        for i in range(0, len(linhas), linhas_por_pagina)
    ]

    id_fonte, id_catalogo, id_pages = 1, 2, 3
    ids_paginas = [4 + i * 2 for i in range(len(paginas))]

    objetos = [
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        f"<< /Type /Catalog /Pages {id_pages} 0 R >>".encode(),
        (
            f"<< /Type /Pages /Count {len(paginas)} "
            f"/Kids [{' '.join(f'{pid} 0 R' for pid in ids_paginas)}] >>"
        ).encode(),
    ]

    for indice, linhas_pagina in enumerate(paginas):
        id_conteudo = ids_paginas[indice] + 1
        objetos.append(
            f"<< /Type /Page /Parent {id_pages} 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 {id_fonte} 0 R >> >> "
            f"/Contents {id_conteudo} 0 R >>".encode()
        )

        fluxo = bytearray(b"BT\n/F1 11 Tf\n16 TL\n50 792 Td\n")
        for linha in linhas_pagina:
            fluxo += b"(" + _escapar(linha) + b") Tj T*\n"
        fluxo += b"ET"

        objetos.append(
            f"<< /Length {len(fluxo)} >>\nstream\n".encode() + bytes(fluxo) + b"\nendstream"
        )

    saida = bytearray(b"%PDF-1.4\n")
    deslocamentos = []

    for numero, corpo in enumerate(objetos, start=1):
        deslocamentos.append(len(saida))
        saida += f"{numero} 0 obj\n".encode() + corpo + b"\nendobj\n"

    inicio_xref = len(saida)
    saida += f"xref\n0 {len(objetos) + 1}\n".encode() + b"0000000000 65535 f \n"
    for deslocamento in deslocamentos:
        saida += f"{deslocamento:010d} 00000 n \n".encode()

    saida += (
        f"trailer\n<< /Size {len(objetos) + 1} /Root {id_catalogo} 0 R >>\n"
        f"startxref\n{inicio_xref}\n%%EOF\n"
    ).encode()

    with open(caminho, "wb") as arquivo:
        arquivo.write(bytes(saida))


# =========================================================================
# Seed
# =========================================================================

def _conectar():
    return sqlite3.connect(CAMINHO_DB)


def _usuario_existe(email: str) -> bool:
    conexao = _conectar()
    cursor = conexao.cursor()
    cursor.execute("SELECT 1 FROM users WHERE email = ?", (email.lower(),))
    existe = cursor.fetchone() is not None
    conexao.close()
    return existe


def criar_admin_inicial() -> None:
    """Insere o primeiro admin direto no banco.

    Não dá para usar nenhuma rota aqui: não existe cadastro público, e
    criar_conta_staff exige um admin já existente. Este e o criar_admin.py são
    os únicos pontos do sistema em que uma conta de confiança nasce fora das
    regras de permissão — por isso moram em scripts, e não numa rota da API.
    """
    conexao = _conectar()
    cursor = conexao.cursor()
    if _usuario_existe(ADMIN):
        # Criado antes do segundo fator: a migração ligou o código para ele.
        cursor.execute("UPDATE users SET segundo_fator = 0 WHERE email = ?", (ADMIN,))
        conexao.commit()
        conexao.close()
        print(f"  admin ja existe: {ADMIN}")
        return

    # Sem código por e-mail: na demonstração não há caixa de entrada de verdade.
    cursor.execute(
        "INSERT INTO users (email, senha, tipo, nome, segundo_fator) VALUES (?, ?, ?, ?, 0)",
        (ADMIN, hash_senha(SENHA_PADRAO), "adm", NOME_ADMIN),
    )
    conexao.commit()
    conexao.close()
    print(f"  admin criado: {ADMIN}")


def criar_contas() -> None:
    if _usuario_existe(PROFESSOR):
        conexao = _conectar()
        conexao.execute("UPDATE users SET segundo_fator = 0 WHERE email = ?", (PROFESSOR,))
        conexao.commit()
        conexao.close()
        print(f"  professor ja existe: {PROFESSOR}")
    else:
        resultado = criar_conta_staff(
            ADMIN, PROFESSOR, SENHA_PADRAO, "professor",
            nome=NOME_PROFESSOR, disciplinas=DISCIPLINAS_PROFESSOR,
            provisoria=False,  # demonstração: entra com demo123 sem trocar
            conferir_senha=False,  # demo123 é fraca de propósito: é a senha que todos conhecem
            segundo_fator=False,  # demonstração: não há caixa de e-mail para receber o código
        )
        print(f"  professor: {resultado['mensagem']}")

    if _usuario_existe(ALUNO):
        print(f"  aluno ja existe: {ALUNO}")
    else:
        resultado = criar_conta_staff(
            ADMIN, ALUNO, SENHA_PADRAO, "aluno",
            nome=NOME_ALUNO, matricula=MATRICULA_ALUNO,
            provisoria=False, conferir_senha=False,
        )
        print(f"  aluno: {resultado['mensagem']}")


def criar_turma_com_aluno() -> int | None:
    conexao = _conectar()
    cursor = conexao.cursor()
    cursor.execute(
        "SELECT id FROM turmas WHERE nome = ? AND semestre = ?",
        (TURMA_NOME, TURMA_SEMESTRE),
    )
    linha = cursor.fetchone()
    conexao.close()

    if linha:
        turma_id = linha[0]
        print(f"  turma ja existe: {TURMA_NOME} (id {turma_id})")
    else:
        resultado = criar_turma(ADMIN, PROFESSOR, TURMA_NOME, TURMA_SEMESTRE)
        if not resultado.get("sucesso"):
            print(f"  ERRO ao criar turma: {resultado.get('mensagem')}")
            return None
        turma_id = resultado["turma"]["id"]
        print(f"  turma criada: {TURMA_NOME} (id {turma_id})")

    resultado = matricular_aluno(ADMIN, ALUNO, turma_id)
    print(f"  matricula: {resultado['mensagem']}")
    return turma_id


def criar_material_indexado(turma_id: int) -> None:
    import base64

    conexao = _conectar()
    cursor = conexao.cursor()
    cursor.execute(
        "SELECT id FROM materiais WHERE titulo = ? AND turma_id = ?",
        (MATERIAL_TITULO, turma_id),
    )
    linha = cursor.fetchone()
    conexao.close()

    if linha:
        print(f"  material ja existe: {MATERIAL_TITULO} (id {linha[0]})")
        material_id = linha[0]
    else:
        caminho_pdf = os.path.join(os.path.dirname(__file__), "_seed_material.pdf")
        gerar_pdf(TEXTO_PDF, caminho_pdf)

        with open(caminho_pdf, "rb") as arquivo:
            conteudo = base64.b64encode(arquivo.read()).decode()

        resultado = criar_material(
            professor_email=PROFESSOR,
            turma_id=turma_id,
            titulo=MATERIAL_TITULO,
            tipo="pdf",
            descricao="Perfis de Stevenson, classes da NYHA e tratamento inicial",
            assunto=IC_AGUDA["assunto"],
            topico=IC_AGUDA["topico"],
            aula="Aula 3",
            semestre=TURMA_SEMESTRE,
            rascunho=False,
            arquivo_base64=conteudo,
            arquivo_nome=IC_AGUDA["arquivo"],
        )

        os.remove(caminho_pdf)

        if not resultado.get("sucesso"):
            print(f"  ERRO ao criar material: {resultado.get('mensagem')}")
            return

        material_id = resultado["material_id"]
        print(f"  material criado: {MATERIAL_TITULO} (id {material_id})")

    # A indexação depende do Ollama; sem ele o resto do seed continua válido.
    from regras.chat_ia import indexar_material

    try:
        resultado = indexar_material(material_id)
        print(f"  indexacao: {resultado['mensagem']}")
    except RuntimeError as erro:
        print(f"  AVISO: material nao indexado ({erro})")
        print("         suba o Ollama e rode este script de novo para habilitar o chat.")


def main() -> None:
    global TURMA_SEMESTRE

    print(f"Banco: {CAMINHO_DB}\n")

    configurar_banco()
    TURMA_SEMESTRE = _semestre_vigente()

    print("Contas:")
    criar_admin_inicial()
    criar_contas()

    print("\nTurma:")
    turma_id = criar_turma_com_aluno()

    if turma_id is None:
        sys.exit(1)

    print("\nMaterial:")
    criar_material_indexado(turma_id)

    # O resto do semestre: turma de alunos, mais disciplinas e professores,
    # atividades com entregas, avisos, mensagens e um semestre anterior. Sem
    # isso, metade das telas abre vazia na demonstração.
    from seed_semestre import popular_semestre

    popular_semestre(turma_id)

    print("\n" + "=" * 58)
    print("Pronto. Contas de demonstracao (senha unica):")
    print(f"  admin     {ADMIN}")
    print(f"  professor {PROFESSOR}")
    print(f"  aluno     {ALUNO}")
    print(f"  senha     {SENHA_PADRAO}")
    print("=" * 58)


if __name__ == "__main__":
    main()
