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
from regras.autenticacao import cadastrar_usuario, criar_conta_staff
from regras.materiais import criar_material
from regras.matriculas import matricular_aluno
from regras.turmas import criar_turma
from infra.security import hash_senha

SENHA_PADRAO = "demo123"

ADMIN = "adm@deltacare.com"
PROFESSOR = "professor@deltacare.com"
ALUNO = "aluno@deltacare.com"

TURMA_NOME = "Cardiologia I"
TURMA_SEMESTRE = "2026.2"

MATERIAL_TITULO = "Aula 3 - Insuficiencia Cardiaca Aguda"

# Conteúdo fictício de propósito: o protocolo, a escala e o medicamento não
# existem. Isso torna a demonstração honesta — se o assistente responder a dose
# do "Cardiolex" corretamente, foi porque leu o material, e não porque o modelo
# já sabia o assunto.
TEXTO_PDF = """Cardiologia I - Aula 3
Manejo Inicial da Insuficiencia Cardiaca Aguda
Prof. responsavel: Delta Care / Semestre 2026.2

1. INTRODUCAO

Este material apresenta o Protocolo Delta-7, adotado nesta disciplina para
o manejo inicial do paciente com insuficiencia cardiaca aguda descompensada.

2. A ESCALA DCM-4

Estagio DCM-1: paciente quente e seco. Perfusao preservada, sem congestao.
Conduta: ajuste de medicacao oral e alta precoce com reavaliacao em 72 horas.

Estagio DCM-2: paciente quente e umido. Perfusao preservada, com congestao
pulmonar. Conduta: diuretico intravenoso e monitorizacao de diurese horaria.

Estagio DCM-3: paciente frio e umido. Baixa perfusao associada a congestao.
Conduta: suporte inotropico e avaliacao para internacao em unidade coronariana.

Estagio DCM-4: paciente frio e seco. Baixa perfusao sem congestao evidente.
Conduta: reposicao volemica cautelosa antes de qualquer inotropico.

3. O MEDICAMENTO CARDIOLEX

O Cardiolex e o agente de primeira linha previsto no Protocolo Delta-7 para
os estagios DCM-2 e DCM-3. A dose inicial recomendada e de 12,5 mg por via
intravenosa, administrada em bolus lento ao longo de 10 minutos.

A dose pode ser repetida uma unica vez apos 30 minutos, caso nao haja
resposta clinica adequada. A dose maxima acumulada nas primeiras 24 horas
nao deve ultrapassar 37,5 mg.

4. CRITERIOS DE INTERRUPCAO

A administracao de Cardiolex deve ser imediatamente interrompida se a pressao
arterial sistolica cair abaixo de 92 mmHg, ou se a frequencia cardiaca
ultrapassar 130 batimentos por minuto de forma sustentada.

Nesses casos, o Protocolo Delta-7 orienta a transicao para o esquema de
resgate descrito na aula 5, com reavaliacao da Escala DCM-4 a cada 15 minutos.

5. MONITORIZACAO

Durante as primeiras 6 horas apos a administracao, recomenda-se:
- Afericao de pressao arterial a cada 15 minutos na primeira hora.
- Controle de diurese horaria, com meta minima de 0,5 mL por quilo por hora.
- Reavaliacao do estagio na Escala DCM-4 a cada 2 horas.
- Registro de peso corporal diario, sempre no mesmo horario.

6. CONSIDERACOES FINAIS

O Protocolo Delta-7 nao substitui o julgamento clinico individualizado. Os
valores apresentados sao referencias didaticas desta disciplina.
"""


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

    Não dá para usar nenhuma rota aqui: o cadastro público só cria aluno, e
    criar_conta_staff exige um admin já existente. Esse é o único ponto do
    sistema em que uma conta de confiança nasce fora das regras de permissão —
    por isso ele mora num script de seed, e não numa rota da API.
    """
    if _usuario_existe(ADMIN):
        print(f"  admin ja existe: {ADMIN}")
        return

    conexao = _conectar()
    cursor = conexao.cursor()
    cursor.execute(
        "INSERT INTO users (email, senha, tipo) VALUES (?, ?, ?)",
        (ADMIN, hash_senha(SENHA_PADRAO), "adm"),
    )
    conexao.commit()
    conexao.close()
    print(f"  admin criado: {ADMIN}")


def criar_contas() -> None:
    if _usuario_existe(PROFESSOR):
        print(f"  professor ja existe: {PROFESSOR}")
    else:
        resultado = criar_conta_staff(ADMIN, PROFESSOR, SENHA_PADRAO, "professor")
        print(f"  professor: {resultado['mensagem']}")

    if _usuario_existe(ALUNO):
        print(f"  aluno ja existe: {ALUNO}")
    else:
        resultado = cadastrar_usuario(ALUNO, SENHA_PADRAO, "aluno")
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
            descricao="Protocolo Delta-7 e Escala DCM-4 (conteudo ficticio para demonstracao)",
            assunto="Cardiologia",
            topico="Insuficiencia cardiaca",
            aula="Aula 3",
            semestre=TURMA_SEMESTRE,
            rascunho=False,
            arquivo_base64=conteudo,
            arquivo_nome="cardiologia_aula3.pdf",
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
    print(f"Banco: {CAMINHO_DB}\n")

    configurar_banco()

    print("Contas:")
    criar_admin_inicial()
    criar_contas()

    print("\nTurma:")
    turma_id = criar_turma_com_aluno()

    if turma_id is None:
        sys.exit(1)

    print("\nMaterial:")
    criar_material_indexado(turma_id)

    print("\n" + "=" * 58)
    print("Pronto. Contas de demonstracao (senha unica):")
    print(f"  admin     {ADMIN}")
    print(f"  professor {PROFESSOR}")
    print(f"  aluno     {ALUNO}")
    print(f"  senha     {SENHA_PADRAO}")
    print("=" * 58)


if __name__ == "__main__":
    main()
