"""O resto do semestre de demonstração: chamado pelo seed_demo.py.

Com só uma disciplina e um aluno, metade das telas abria vazia: turma de
alunos, ranking, avisos, semestres anteriores, o "para corrigir" do professor.
Isto monta um semestre plausível de uma faculdade de medicina:

- a turma MED 3A, com Cardiologia I, Anatomia e Fisiologia, três professores
  e oito alunos — um deles fora de Fisiologia por aproveitamento de estudos;
- atividades com prazo, entregas de vários alunos (umas corrigidas, outras
  esperando o professor), material aberto em quantidades diferentes, o que
  dá um ranking com gente em posições diferentes;
- mensagens, avisos (um urgente da disciplina, um geral da coordenação),
  uma denúncia aberta, favoritos, uma anotação e um pedido de correção de
  dados esperando a administração;
- PDFs de verdade em todas as disciplinas (material_demo.py), indexados para
  o chat e para a busca dentro do PDF;
- o semestre anterior, com Histologia, para Semestres anteriores ter o que
  mostrar.

**Tudo passa pelas funções reais do sistema** — as mesmas que as telas
chamam —, então os dados obedecem às mesmas regras e disparam as mesmas
notificações. Nada é escrito direto no banco, com uma exceção comentada.

Pode rodar de novo: cada passo confere se já existe antes de criar.

O conteúdo médico é real: as perguntas dos quizzes e as respostas das
mensagens saem do material_demo.py.
"""

import base64
import os
from datetime import datetime, timedelta, timezone

from infra.database import abrir_conexao
from material_demo import POR_DISCIPLINA
from regras.anotacoes import criar_anotacao
from regras.aluno import registrar_acesso_material
from regras.atividades import corrigir_entrega, criar_atividade_em_turmas, enviar_entrega, listar_entregas
from regras.autenticacao import criar_conta_staff
from regras.avisos import publicar_aviso
from regras.coortes import criar_coorte, criar_excecao, matricular_na_coorte, sincronizar_disciplina
from regras.denuncias import criar_denuncia
from regras.favoritos import marcar_favorito
from regras.materiais import criar_material
from regras.mensagens import abrir_conversa, enviar_mensagem
from regras.privacidade import solicitar as solicitar_privacidade
from regras.ranking import definir_visibilidade
from regras.semestres import normalizar_semestre, semestre_vigente
from regras.turmas import criar_turma
from seed_demo import ADMIN, ALUNO, PROFESSOR, SENHA_PADRAO, gerar_pdf

PROFESSORES = {
    "beatriz.lemos@deltacare.com": ("Beatriz Lemos", "Anatomia; Histologia"),
    "paulo.nogueira@deltacare.com": ("Paulo Nogueira", "Fisiologia"),
}
ANATOMIA_PROF = "beatriz.lemos@deltacare.com"
FISIOLOGIA_PROF = "paulo.nogueira@deltacare.com"

ALUNOS = {
    ALUNO: "Marina Duarte",
    "lucas.martins@deltacare.com": "Lucas Martins",
    "ana.rocha@deltacare.com": "Ana Beatriz Rocha",
    "gabriel.teixeira@deltacare.com": "Gabriel Teixeira",
    "julia.fernandes@deltacare.com": "Júlia Fernandes",
    "rafael.moreira@deltacare.com": "Rafael Moreira",
    "camila.ribeiro@deltacare.com": "Camila Ribeiro",
    "pedro.albuquerque@deltacare.com": "Pedro Albuquerque",
}

# O que o seed escreve sobre a Aula 3 de Cardiologia (material_demo.IC_AGUDA).
# A resposta certa de cada questão fica na mesma posição da versão anterior,
# que era sobre um remédio inventado: as entregas já feitas continuam com a
# nota certa no banco que for atualizado.
QUIZ_IC = [
    {"enunciado": "Qual fração de ejeção define a insuficiência cardíaca com fração de ejeção reduzida?",
     "alternativas": ["50% ou mais", "40% ou menos", "De 41% a 49%", "60% ou mais"], "correta": 1},
    {"enunciado": "Baixa perfusão sem congestão corresponde a qual perfil de Stevenson?",
     "alternativas": ["A (quente e seco)", "B (quente e úmido)", "C (frio e úmido)", "L (frio e seco)"], "correta": 3},
    {"enunciado": "Qual diurético é a base do tratamento da congestão na insuficiência cardíaca aguda?",
     "alternativas": ["Hidroclorotiazida", "Furosemida intravenosa", "Espironolactona", "Acetazolamida"], "correta": 1},
]
CASO_ENUNCIADO = ("Descreva a conduta inicial para um paciente com insuficiência cardíaca aguda "
                  "no perfil frio e úmido (C) de Stevenson.")
CASO_MARINA = ("Perfil frio e úmido: diurético de alça intravenoso para a congestão e dobutamina para a "
               "baixa perfusão, com internação em unidade de terapia intensiva.")
CASO_LUCAS = "Inicio furosemida intravenosa e reavalio a perfusão e a diurese nas primeiras horas."
CASO_DEVOLUTIVA = "Boa conduta. Faltou citar a monitorização da diurese, da função renal e do potássio."
MENSAGEM_MARINA = "Professor, no perfil quente e úmido precisa de inotrópico?"
RESPOSTA_A_MARINA = ("Em geral não: a perfusão está preservada. A base é o diurético intravenoso; "
                     "o vasodilatador entra se a pressão estiver alta.")
ANOTACAO_TEXTO = "Revisar os quatro perfis de Stevenson antes da prova."
ANOTACAO_TRECHO = "Perfil C (frio e úmido)"


def _agora():
    return datetime.now(timezone.utc)


def _semestre_anterior(semestre: str) -> str:
    ano, periodo = (int(parte) for parte in normalizar_semestre(semestre).split("/"))
    return f"{ano - 1}/2" if periodo == 1 else f"{ano}/1"


def _um(sql: str, parametros=()):
    conexao = abrir_conexao()
    linha = conexao.execute(sql, parametros).fetchone()
    conexao.close()
    return linha


def _conta(email: str, nome: str, tipo: str, disciplinas: str = ""):
    if _um("SELECT 1 FROM users WHERE email = ?", (email,)):
        _sem_codigo(email)
        return
    # Não provisória e sem código por e-mail: na demonstração, todas entram
    # com demo123 direto (não há e-mail de verdade para receber o código).
    criar_conta_staff(ADMIN, email, SENHA_PADRAO, tipo, nome=nome, disciplinas=disciplinas,
                      provisoria=False, conferir_senha=False, segundo_fator=False)
    print(f"  {tipo}: {nome}")


def _sem_codigo(email: str) -> None:
    """Conta de demonstração criada antes do segundo fator: passa a entrar sem
    o código também (a migração liga o código para toda conta existente)."""
    conexao = abrir_conexao()
    conexao.execute("UPDATE users SET segundo_fator = 0 WHERE email = ?", (email,))
    conexao.commit()
    conexao.close()


def _coorte(nome: str, semestre: str) -> int:
    linha = _um("SELECT id FROM coortes WHERE nome = ? AND semestre = ?", (nome, semestre))
    if linha:
        return linha[0]
    coorte_id = criar_coorte(ADMIN, nome, semestre)["coorte"]["id"]
    print(f"  turma de alunos: {nome} · {semestre}")
    return coorte_id


def _disciplina(nome: str, semestre: str, professor: str, coorte_id: int) -> int:
    linha = _um("SELECT id FROM turmas WHERE nome = ? AND semestre = ?", (nome, semestre))
    if linha:
        return linha[0]
    turma_id = criar_turma(ADMIN, professor, nome, semestre, coorte_id)["turma"]["id"]
    print(f"  disciplina: {nome} · {semestre}")
    return turma_id


def _material(turma_id, professor, titulo, **campos) -> int:
    linha = _um("SELECT id FROM materiais WHERE titulo = ? AND turma_id = ?", (titulo, turma_id))
    if linha:
        return linha[0]
    resultado = criar_material(professor_email=professor, turma_id=turma_id, titulo=titulo, **campos)
    print(f"  material: {titulo}")
    return resultado["material_id"]


def _material_pdf(turma_id, professor, titulo, texto, arquivo_nome, **campos) -> int:
    linha = _um("SELECT id FROM materiais WHERE titulo = ? AND turma_id = ?", (titulo, turma_id))
    if linha:
        # Já existe, mas pode ter ficado sem índice (o Ollama estava fora na
        # primeira vez): é o "rode o seed de novo" do aviso abaixo.
        if not _um("SELECT 1 FROM material_chunks WHERE material_id = ?", (linha[0],)):
            _indexar(linha[0])
        return linha[0]
    caminho = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_seed_temporario.pdf")
    gerar_pdf(texto, caminho)
    with open(caminho, "rb") as arquivo:
        conteudo = base64.b64encode(arquivo.read()).decode()
    os.remove(caminho)

    material_id = _material(turma_id, professor, titulo, tipo="pdf", rascunho=False,
                            arquivo_base64=conteudo, arquivo_nome=arquivo_nome, **campos)

    _indexar(material_id)
    return material_id


def _indexar(material_id: int) -> None:
    from regras.chat_ia import indexar_material

    try:
        indexar_material(material_id)
        print("    indexado para o chat e para a busca")
    except RuntimeError as erro:
        print(f"    AVISO: não indexado ({erro}). Suba o Ollama e rode o seed de novo.")


def _pdfs_da_disciplina(nome: str, turma_id: int, professor: str) -> list:
    """Os PDFs de material_demo.POR_DISCIPLINA[nome], criados e indexados."""
    return [
        _material_pdf(turma_id, professor, material["titulo"], material["texto"], material["arquivo"],
                      assunto=material["assunto"], topico=material["topico"])
        for material in POR_DISCIPLINA[nome]
    ]


def _atividade(turma_id, professor, titulo, **campos) -> int:
    linha = _um("SELECT id FROM atividades WHERE titulo = ? AND turma_id = ?", (titulo, turma_id))
    if linha:
        return linha[0]
    atividade_id = criar_atividade_em_turmas(professor, [turma_id], titulo=titulo, rascunho=False,
                                             **campos)["atividade_ids"][0]
    print(f"  atividade: {titulo}")
    return atividade_id


def _abrir(aluno: str, material_id: int):
    """Registra que o aluno abriu o material — uma vez só por par."""
    if _um(
        "SELECT 1 FROM acessos_material a JOIN users u ON u.id = a.aluno_id"
        " WHERE u.email = ? AND a.material_id = ?",
        (aluno, material_id),
    ):
        return
    registrar_acesso_material(aluno, material_id)


def popular_semestre(cardiologia_id: int) -> None:
    vigente = semestre_vigente()
    anterior = _semestre_anterior(vigente)
    amanha = (_agora() + timedelta(days=1)).isoformat()

    print("\nProfessores e alunos:")
    for email, (nome, disciplinas) in PROFESSORES.items():
        _conta(email, nome, "professor", disciplinas)
    for email, nome in ALUNOS.items():
        _conta(email, nome, "aluno")

    print(f"\nTurma de alunos do semestre ({vigente}):")
    med3a = _coorte("MED 3A", vigente)

    # A única escrita direta: a Cardiologia I do seed antigo nasceu antes de
    # existir turma de alunos, e o sistema não tem (ainda) a ação "mover
    # disciplina para uma turma". O resto do vínculo é a função real.
    if not _um("SELECT coorte_id FROM turmas WHERE id = ?", (cardiologia_id,))[0]:
        conexao = abrir_conexao()
        conexao.execute("UPDATE turmas SET coorte_id = ? WHERE id = ?", (med3a, cardiologia_id))
        conexao.commit()
        conexao.close()
        sincronizar_disciplina(cardiologia_id)

    anatomia = _disciplina("Anatomia", vigente, ANATOMIA_PROF, med3a)
    fisiologia = _disciplina("Fisiologia", vigente, FISIOLOGIA_PROF, med3a)

    for email in ALUNOS:
        matricular_na_coorte(ADMIN, email, med3a)
    # Aproveitamento de estudos: Pedro já cursou Fisiologia em outra faculdade.
    criar_excecao(ADMIN, "pedro.albuquerque@deltacare.com", fisiologia)

    print("\nMaterial:")
    aula_cardio = _um("SELECT id FROM materiais WHERE turma_id = ? ORDER BY id LIMIT 1", (cardiologia_id,))[0]
    cranio = _material(anatomia, ANATOMIA_PROF, "Ossos do crânio - roteiro de estudo", tipo="link",
                       link_url="https://pt.wikipedia.org/wiki/Cr%C3%A2nio", rascunho=False,
                       assunto="Anatomia", topico="Crânio")
    _material(anatomia, ANATOMIA_PROF, "Aula 5 - Base do crânio", tipo="link",
              link_url="https://pt.wikipedia.org/wiki/Base_do_cr%C3%A2nio", rascunho=False,
              data_liberacao=amanha, assunto="Anatomia", topico="Crânio")
    ciclo = _material(fisiologia, FISIOLOGIA_PROF, "Ciclo cardíaco - esquema", tipo="link",
                      link_url="https://pt.wikipedia.org/wiki/Ciclo_card%C3%ADaco", rascunho=False,
                      assunto="Fisiologia", topico="Coração")
    # O chat só lê PDF: sem eles, Anatomia e Fisiologia respondiam "a
    # disciplina ainda não tem texto que eu consiga ler" para tudo.
    _pdfs_da_disciplina("Cardiologia I", cardiologia_id, PROFESSOR)
    _pdfs_da_disciplina("Anatomia", anatomia, ANATOMIA_PROF)
    _pdfs_da_disciplina("Fisiologia", fisiologia, FISIOLOGIA_PROF)

    print("\nAtividades:")
    quiz = _atividade(
        cardiologia_id, PROFESSOR, "Quiz - Insuficiência cardíaca", tipo="objetiva", pontos=10,
        prazo=(_agora() + timedelta(days=5)).isoformat(), assunto="Cardiologia",
        topico="Insuficiência cardíaca",
        questoes=QUIZ_IC,
    )
    caso = _atividade(
        cardiologia_id, PROFESSOR, "Relatório de caso clínico", tipo="dissertativa", pontos=10,
        prazo=(_agora() + timedelta(days=10)).isoformat(), anexo="opcional",
        enunciado=CASO_ENUNCIADO,
    )
    quiz_cranio = _atividade(
        anatomia, ANATOMIA_PROF, "Quiz - Crânio", tipo="objetiva", pontos=10,
        prazo=(_agora() - timedelta(days=2)).isoformat(), assunto="Anatomia", topico="Cranio",
        questoes=[
            {"enunciado": "Por onde passa a medula oblonga?",
             "alternativas": ["Forame oval", "Forame magno", "Forame redondo"], "correta": 1},
            {"enunciado": "Quantos ossos formam o neurocrânio?",
             "alternativas": ["Seis", "Oito", "Doze"], "correta": 1},
        ],
    )

    print("\nEstudo dos alunos (abre material, entrega atividade):")
    # Quantidades diferentes de propósito: o ranking precisa de gente em
    # posições diferentes para mostrar alguma coisa.
    estudo = {
        ALUNO: ([aula_cardio, cranio, ciclo], [1, 3, 1], [1, 1]),
        "lucas.martins@deltacare.com": ([aula_cardio, cranio, ciclo], [1, 3, 0], [1, 1]),
        "ana.rocha@deltacare.com": ([aula_cardio, ciclo], [1, 2, 1], [1, 0]),
        "gabriel.teixeira@deltacare.com": ([cranio], [0, 3, 1], [1, 1]),
        "julia.fernandes@deltacare.com": ([aula_cardio], [1, 0, 0], None),
        "rafael.moreira@deltacare.com": ([], None, [0, 1]),
        "camila.ribeiro@deltacare.com": ([ciclo], None, None),
    }
    for aluno, (materiais, respostas_quiz, respostas_cranio) in estudo.items():
        for material_id in materiais:
            _abrir(aluno, material_id)
        if respostas_quiz is not None:
            enviar_entrega(aluno, quiz, respostas_quiz)
        if respostas_cranio is not None:
            enviar_entrega(aluno, quiz_cranio, respostas_cranio)

    enviar_entrega(ALUNO, caso, CASO_MARINA)
    enviar_entrega("lucas.martins@deltacare.com", caso, CASO_LUCAS)

    # A da Marina já corrigida; a do Lucas fica esperando: é ela que aparece
    # em "Para corrigir" na tela inicial do professor.
    for entrega in listar_entregas(caso, PROFESSOR)["entregas"]:
        if entrega["aluno_email"] == ALUNO and entrega["entregue"] and entrega["nota"] is None:
            corrigir_entrega(entrega["entrega_id"], PROFESSOR, 8, CASO_DEVOLUTIVA)

    print("\nMensagens, avisos, denúncia:")
    # A última fica sem resposta: é a que aparece como não lida para o professor.
    for autor, texto, aluno in (
        (ALUNO, MENSAGEM_MARINA, None),
        (PROFESSOR, RESPOSTA_A_MARINA, ALUNO),
        ("ana.rocha@deltacare.com", "Professor, o relatório pode ser entregue em PDF?", None),
    ):
        if not _um("SELECT 1 FROM mensagens WHERE turma_id = ? AND conteudo = ?", (cardiologia_id, texto)):
            if aluno:
                # Quem responde leu antes, como na tela: abrir a conversa marca lida.
                abrir_conversa(autor, cardiologia_id, aluno)
            enviar_mensagem(autor, cardiologia_id, texto, aluno)

    if not _um("SELECT 1 FROM avisos WHERE titulo = 'Prova antecipada'"):
        publicar_aviso(PROFESSOR, "Prova antecipada",
                       "A prova de Cardiologia I passa para a próxima quarta-feira, no mesmo horário.",
                       [cardiologia_id], urgente=True)
    if not _um("SELECT 1 FROM avisos WHERE titulo = 'Semana acadêmica'"):
        publicar_aviso(ADMIN, "Semana acadêmica",
                       "Na semana acadêmica não haverá aula regular. A programação sai na sexta.",
                       geral=True)

    if not _um("SELECT 1 FROM denuncias WHERE material_id = ?", (ciclo,)):
        criar_denuncia("camila.ribeiro@deltacare.com", ciclo, "incorreto",
                       "O esquema troca a ordem das fases isovolumétricas.")

    print("\nFavoritos, anotação e ranking:")
    marcar_favorito(ALUNO, aula_cardio)
    if not _um(
        "SELECT 1 FROM anotacoes a JOIN users u ON u.id = a.aluno_id WHERE u.email = ? AND a.material_id = ?",
        (ALUNO, aula_cardio),
    ):
        criar_anotacao(ALUNO, aula_cardio, ANOTACAO_TEXTO, ANOTACAO_TRECHO)
    # Uma aluna que prefere não aparecer, para a tela mostrar o caso.
    definir_visibilidade("julia.fernandes@deltacare.com", aparecer=False)

    # Um pedido esperando a administração na tela Privacidade. Pedir de novo
    # é recusado pela própria regra (um pedido igual em aberto por vez).
    solicitar_privacidade("rafael.moreira@deltacare.com", "correcao", "nome", "Rafael Moreira Lima",
                          "Meu nome saiu sem o último sobrenome.")

    print(f"\nSemestre anterior ({anterior}):")
    med2a = _coorte("MED 2A", anterior)
    histologia = _disciplina("Histologia", anterior, ANATOMIA_PROF, med2a)
    for email in (ALUNO, "lucas.martins@deltacare.com", "ana.rocha@deltacare.com"):
        matricular_na_coorte(ADMIN, email, med2a)
    _pdfs_da_disciplina("Histologia", histologia, ANATOMIA_PROF)
