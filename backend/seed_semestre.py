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
- o semestre anterior, com Histologia e um PDF indexado, para Semestres
  anteriores e a busca dentro do PDF terem o que mostrar.

**Tudo passa pelas funções reais do sistema** — as mesmas que as telas
chamam —, então os dados obedecem às mesmas regras e disparam as mesmas
notificações. Nada é escrito direto no banco, com uma exceção comentada.

Pode rodar de novo: cada passo confere se já existe antes de criar.

O conteúdo médico é fictício de propósito, como o do PDF de Cardiologia: se o
assistente responder certo, foi porque leu o material.
"""

import base64
import os
from datetime import datetime, timedelta, timezone

from infra.database import abrir_conexao
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

TEXTO_HISTOLOGIA = """Histologia - Aula 4
Tecido Epitelial de Revestimento
Material do semestre anterior

1. CLASSIFICACAO

Nesta disciplina adotamos a Classificacao Lemos-3 para o epitelio de
revestimento, que considera o numero de camadas, a forma das celulas da
camada superficial e a presenca de especializacoes apicais.

2. O EPITELIO ESTRATIFICADO LEMOS-B

O epitelio Lemos-B reveste a mucosa do canal palatino posterior. Tem entre
quatro e seis camadas de celulas, com superficie de celulas cubicas ciliadas.

3. CRITERIO DE IDENTIFICACAO

Na pratica de microscopia, o Lemos-B e reconhecido pela faixa basal escura
de 3 a 4 micrometros, visivel na coloracao padrao da disciplina.
"""


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
        return
    # Não provisória: na demonstração, todas entram com demo123 sem trocar.
    criar_conta_staff(ADMIN, email, SENHA_PADRAO, tipo, nome=nome, disciplinas=disciplinas, provisoria=False)
    print(f"  {tipo}: {nome}")


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
        return linha[0]
    caminho = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_seed_temporario.pdf")
    gerar_pdf(texto, caminho)
    with open(caminho, "rb") as arquivo:
        conteudo = base64.b64encode(arquivo.read()).decode()
    os.remove(caminho)

    material_id = _material(turma_id, professor, titulo, tipo="pdf", rascunho=False,
                            arquivo_base64=conteudo, arquivo_nome=arquivo_nome, **campos)

    from regras.chat_ia import indexar_material

    try:
        indexar_material(material_id)
        print("    indexado para o chat e para a busca")
    except RuntimeError as erro:
        print(f"    AVISO: não indexado ({erro}). Suba o Ollama e rode o seed de novo.")
    return material_id


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

    print("\nAtividades:")
    quiz = _atividade(
        cardiologia_id, PROFESSOR, "Quiz - Insuficiência cardíaca", tipo="objetiva", pontos=10,
        prazo=(_agora() + timedelta(days=5)).isoformat(), assunto="Cardiologia",
        topico="Insuficiencia cardiaca",
        questoes=[
            {"enunciado": "Qual a dose inicial de Cardiolex no Protocolo Delta-7?",
             "alternativas": ["5 mg", "12,5 mg", "25 mg", "37,5 mg"], "correta": 1},
            {"enunciado": "Paciente frio e seco corresponde a qual estágio?",
             "alternativas": ["DCM-1", "DCM-2", "DCM-3", "DCM-4"], "correta": 3},
            {"enunciado": "Abaixo de qual pressão sistólica o Cardiolex é suspenso?",
             "alternativas": ["80 mmHg", "92 mmHg", "100 mmHg", "110 mmHg"], "correta": 1},
        ],
    )
    caso = _atividade(
        cardiologia_id, PROFESSOR, "Relatório de caso clínico", tipo="dissertativa", pontos=10,
        prazo=(_agora() + timedelta(days=10)).isoformat(), anexo="opcional",
        enunciado="Descreva a conduta para um paciente DCM-3 segundo o Protocolo Delta-7.",
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

    enviar_entrega(ALUNO, caso, "Paciente DCM-3: suporte inotrópico e avaliação para unidade coronariana.")
    enviar_entrega("lucas.martins@deltacare.com", caso,
                   "Inicio Cardiolex 12,5 mg em bolus lento e reavalio a Escala DCM-4 em 15 minutos.")

    # A da Marina já corrigida; a do Lucas fica esperando: é ela que aparece
    # em "Para corrigir" na tela inicial do professor.
    for entrega in listar_entregas(caso, PROFESSOR)["entregas"]:
        if entrega["aluno_email"] == ALUNO and entrega["entregue"] and entrega["nota"] is None:
            corrigir_entrega(entrega["entrega_id"], PROFESSOR, 8,
                             "Boa conduta. Faltou citar a internação em unidade coronariana.")

    print("\nMensagens, avisos, denúncia:")
    # A última fica sem resposta: é a que aparece como não lida para o professor.
    for autor, texto, aluno in (
        (ALUNO, "Professor, o Cardiolex pode ser repetido no estágio DCM-2?", None),
        (PROFESSOR, "Pode, uma única vez após 30 minutos, respeitando a dose máxima de 37,5 mg.", ALUNO),
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
        criar_anotacao(ALUNO, aula_cardio, "Revisar os critérios de interrupção antes da prova.",
                       "pressao arterial sistolica cair abaixo de 92 mmHg")
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
    _material_pdf(histologia, ANATOMIA_PROF, "Aula 4 - Tecido epitelial", TEXTO_HISTOLOGIA,
                  "histologia_aula4.pdf", assunto="Histologia", topico="Epitelio")
