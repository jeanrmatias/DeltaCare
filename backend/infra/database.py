import contextvars
import os
import sqlite3

from infra.security import hash_senha

# Caminho único do banco. Os outros módulos importam daqui em vez de repetir
# a string — já esteve duplicado em três arquivos, e bastaria mudar um deles
# para o sistema passar a gravar em dois bancos diferentes sem avisar.
# DELTACARE_DB permite apontar para outro arquivo (é o que os testes usam,
# para não tocar no banco de demonstração).
CAMINHO_DB = os.environ.get("DELTACARE_DB", "deltacare.db")


# Segundos que uma escrita espera pela trava antes de desistir.
#
# O SQLite aceita **um escritor por vez**, sempre. Medido com 60 alunos
# entregando ao mesmo tempo: as escritas se enfileiram e a última espera ~2s.
# O padrão do módulo é 5s, e com ele nenhuma falhou. 10s dá folga para o dobro
# desse pico, e é aqui que se ajusta se um dia "database is locked" aparecer no
# log — o que seria o sinal de que SQLite deixou de servir.
TIMEOUT_ESCRITA = 10.0


def abrir_conexao(caminho: str = None):
    """Abre conexão com o banco. **Todo módulo passa por aqui.**

    Antes cada módulo chamava `sqlite3.connect` por conta própria, em quatro
    lugares, e configurar qualquer coisa significava lembrar dos quatro. Dois
    motivos para centralizar:

    1. **Chave estrangeira.** O SQLite não cobra por padrão, e a configuração é
       por conexão — não dá para ligar uma vez no arquivo. Sem centralizar, cada
       módulo teria que lembrar, e o que um esquecesse gravaria órfão em
       silêncio.

       (O WAL **não** está aqui: ele fica gravado no arquivo, então basta ligar
       uma vez, em `configurar_banco`. Rodar o PRAGMA a cada abertura custava
       3x no tempo de `resumo_do_aluno`, que abre várias conexões.)

    2. **O dia da migração.** Se algum dia sair de SQLite, o ponto de troca é
       esta função, e não 245 chamadas de `execute` espalhadas. Não resolve a
       migração — os `?` continuam sendo sintaxe do SQLite — mas tira a parte
       que não precisa doer.

    **`synchronous` fica no padrão (FULL), e isso é escolha.** NORMAL é 17,9x
    mais rápido por commit — e isso é 0,51ms contra 0,03ms, ou 96 milissegundos
    somados em 200 entregas, ao lado de uma busca de material de 219ms e de uma
    resposta da IA de 10 segundos. O que NORMAL custa é a última transação numa
    queda de energia, e a última transação aqui é a entrega de um trabalho ou a
    nota de uma prova. Não vale 96ms.
    """
    # check_same_thread=False: quem fecha as sobras de uma requisição (ver
    # FecharConexoesDaRequisicao) roda na thread do servidor, não na que abriu.
    # Ninguém usa a mesma conexão em duas threads ao mesmo tempo: a sobra só é
    # fechada depois que a rota terminou.
    conexao = sqlite3.connect(
        caminho or CAMINHO_DB, timeout=TIMEOUT_ESCRITA, check_same_thread=False
    )
    # O SQLite não cobra chave estrangeira por padrão. O esquema declara todas,
    # e sem isto elas são documentação.
    conexao.execute("PRAGMA foreign_keys=ON")

    abertas = _CONEXOES_DA_REQUISICAO.get()
    if abertas is not None:
        abertas.append(conexao)
    return conexao


# As conexões abertas durante a requisição em curso; None fora de requisição
# (scripts, seed, testes de regra).
_CONEXOES_DA_REQUISICAO = contextvars.ContextVar("conexoes_da_requisicao", default=None)


class FecharConexoesDaRequisicao:
    """Fecha, ao fim de cada requisição, toda conexão que ficou aberta.

    O projeto inteiro faz `conectar()` ... `close()` sem try/finally. No
    caminho feliz fecha; se algo levanta exceção no meio, a conexão fica presa
    ao rastro do erro até o coletor de lixo passar — e, se havia escrita sem
    commit, **segura a trava do banco** esse tempo todo. Medido: uma rota que
    quebrou no meio de um UPDATE deixou a escrita seguinte, de qualquer
    usuário, falhando com "database is locked".

    Corrigir as ~120 aberturas uma a uma era trocar um esquecimento por 120
    chances de esquecer. Aqui é um ponto só, o mesmo por onde toda conexão
    já passa. `close()` sem commit descarta a escrita pela metade, que é o
    certo para uma requisição que falhou; fechar o que já está fechado não
    faz nada.

    Middleware ASGI puro, e não BaseHTTPMiddleware: este roda a rota na mesma
    tarefa, então a lista é vista pela rota e pelas threads que ela usa (o
    contexto é copiado para a thread, a lista é a mesma).
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        abertas = []
        marca = _CONEXOES_DA_REQUISICAO.set(abertas)
        try:
            await self.app(scope, receive, send)
        finally:
            _CONEXOES_DA_REQUISICAO.reset(marca)
            for conexao in abertas:
                conexao.close()


def configurar_banco(silencioso: bool = False):
    """Cria as tabelas que ainda não existem. Seguro chamar várias vezes.

    `silencioso` existe para os testes: eles recriam o banco a cada caso, e as
    mensagens de conexão afogariam o resultado da suíte.
    """
    if not silencioso:
        print("Python está procurando o banco em:", os.path.abspath(CAMINHO_DB))

    conexao = abrir_conexao()
    cursor = conexao.cursor()

    # WAL: a maior diferença de desempenho disponível por uma linha neste
    # projeto. Sem ele, leitura e escrita se excluem — medido com um professor
    # salvando material e 20 alunos lendo, **as 20 leituras falharam** com
    # "database is locked". Com WAL, nenhuma falhou e as 20 levaram 67ms. E
    # leitura é a esmagadora maioria do tráfego.
    #
    # Fica aqui, e não em `abrir_conexao`, porque o modo é gravado no arquivo:
    # uma vez basta, e banco antigo se converte na primeira abertura.
    cursor.execute("PRAGMA journal_mode=WAL")

    if not silencioso:
        print("Conexão com o banco de dados estabelecida com sucesso!")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            senha TEXT NOT NULL,
            tipo TEXT NOT NULL
        )
    ''')
    conexao.commit()

    # Migração: adiciona as colunas usadas na recuperação de senha, para
    # bancos criados antes dessa funcionalidade existir.
    cursor.execute("PRAGMA table_info(users)")
    colunas = {linha[1] for linha in cursor.fetchall()}

    if "reset_token" not in colunas:
        cursor.execute("ALTER TABLE users ADD COLUMN reset_token TEXT")
    if "reset_expira" not in colunas:
        cursor.execute("ALTER TABLE users ADD COLUMN reset_expira TEXT")
    # Quantas vezes o código de recuperação já foi errado.
    #
    # O código tem 6 dígitos — 900 mil combinações. Sem contar tentativa, e sem
    # limite de requisição por IP, isso se percorre em minutos. O contador
    # limita o ataque a 5 palpites: na sexta, o código morre e a pessoa pede
    # outro. Quem esqueceu a senha erra o código uma ou duas vezes, não cinco.
    if "reset_tentativas" not in colunas:
        cursor.execute("ALTER TABLE users ADD COLUMN reset_tentativas INTEGER NOT NULL DEFAULT 0")

    # Migração: identificação e dados acadêmicos.
    #
    # `nome` entra como NULL em vez de NOT NULL porque as contas que já existem
    # não têm esse dado — exigir agora quebraria o banco em uso. A obrigação
    # fica na criação da conta (regras/autenticacao.py), onde dá para pedir.
    # Para as contas antigas, o sistema mostra o e-mail até alguém preencher.
    if "nome" not in colunas:
        cursor.execute("ALTER TABLE users ADD COLUMN nome TEXT")

    # Só faz sentido para professor: disciplinas que ele está habilitado a
    # lecionar, separadas por ponto e vírgula.
    if "disciplinas" not in colunas:
        cursor.execute("ALTER TABLE users ADD COLUMN disciplinas TEXT")

    # Só faz sentido para aluno: número de registro acadêmico.
    if "matricula" not in colunas:
        cursor.execute("ALTER TABLE users ADD COLUMN matricula TEXT")

    conexao.commit()

    # Migração: senhas antigas gravadas em texto puro (de antes do hash)
    # são convertidas automaticamente na primeira execução. Um hash gerado
    # por hash_senha() sempre tem o formato "salt_hex$hash_hex".
    cursor.execute("SELECT id, senha FROM users")
    for id_usuario, senha in cursor.fetchall():
        if "$" not in senha:
            cursor.execute(
                "UPDATE users SET senha = ? WHERE id = ?",
                (hash_senha(senha), id_usuario)
            )
    conexao.commit()

    # A turma de alunos — MED 3A, a coorte que cursa o semestre junto.
    #
    # **Atenção ao vocabulário, porque as duas coisas se chamam "turma" em
    # lugares diferentes:** a tabela `turmas` logo abaixo é na verdade uma
    # *disciplina* (um professor, um corpo de material, e o chat de IA busca só
    # dentro dela). Renomear as 412 ocorrências de `turma_id` seria um diff
    # enorme sem ganho funcional, então o código manteve o nome antigo e a
    # coorte entrou com nome próprio. Na interface:
    #
    #     coortes  -> "Turma"       (MED 3A)
    #     turmas   -> "Disciplina"  (Cardiologia I, ministrada pela Marina)
    #
    # A chave única é (nome, semestre): a MED 3A de 2026/2 não é a de 2027/1.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS coortes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            semestre TEXT NOT NULL,
            criado_em TEXT NOT NULL,
            UNIQUE (nome, semestre)
        )
    ''')

    # A qual coorte o aluno pertence.
    #
    # Separada de `matriculas` de propósito: pertencer à MED 3A e cursar
    # Anatomia são fatos diferentes, e é a diferença entre eles que permite a
    # exceção.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS matriculas_coorte (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aluno_id INTEGER NOT NULL,
            coorte_id INTEGER NOT NULL,
            criado_em TEXT NOT NULL,
            FOREIGN KEY (aluno_id) REFERENCES users (id),
            FOREIGN KEY (coorte_id) REFERENCES coortes (id),
            UNIQUE (aluno_id, coorte_id)
        )
    ''')

    # Exceção: aluno da coorte que **não** cursa esta disciplina.
    #
    # Guardada como fato próprio, e não só apagando a linha de `matriculas`,
    # porque a exceção precisa **sobreviver** à criação de disciplina nova e a
    # uma rematrícula na coorte. Sem ela, o próximo espalhamento colocaria o
    # aluno de volta em Anatomia e o admin teria que tirar outra vez.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS excecoes_coorte (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aluno_id INTEGER NOT NULL,
            turma_id INTEGER NOT NULL,
            criado_em TEXT NOT NULL,
            FOREIGN KEY (aluno_id) REFERENCES users (id),
            FOREIGN KEY (turma_id) REFERENCES turmas (id),
            UNIQUE (aluno_id, turma_id)
        )
    ''')

    # Turmas do professor (ver a nota de vocabulário acima: isto é disciplina).
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS turmas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            semestre TEXT NOT NULL,
            professor_id INTEGER NOT NULL,
            criado_em TEXT NOT NULL,
            FOREIGN KEY (professor_id) REFERENCES users (id)
        )
    ''')

    # Migração: a qual coorte a disciplina pertence.
    #
    # Anulável, e vai continuar anulável. As disciplinas que já existem não têm
    # coorte, e uma disciplina solta é caso legítimo: optativa, curso de
    # extensão, ou o admin que prefere matricular na mão. Sem coorte, nada
    # espalha e tudo funciona como antes.
    cursor.execute("PRAGMA table_info(turmas)")
    colunas_turmas = {linha[1] for linha in cursor.fetchall()}
    if "coorte_id" not in colunas_turmas:
        cursor.execute("ALTER TABLE turmas ADD COLUMN coorte_id INTEGER REFERENCES coortes (id)")

    # Materiais publicados pelo professor em uma turma.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS materiais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            professor_id INTEGER NOT NULL,
            turma_id INTEGER NOT NULL,
            titulo TEXT NOT NULL,
            descricao TEXT,
            tipo TEXT NOT NULL,
            link_url TEXT,
            arquivo_nome TEXT,
            arquivo_caminho TEXT,
            assunto TEXT,
            topico TEXT,
            aula TEXT,
            semestre TEXT,
            rascunho INTEGER NOT NULL DEFAULT 0,
            data_liberacao TEXT,
            criado_em TEXT NOT NULL,
            atualizado_em TEXT NOT NULL,
            FOREIGN KEY (professor_id) REFERENCES users (id),
            FOREIGN KEY (turma_id) REFERENCES turmas (id)
        )
    ''')

    # Matrícula: quais alunos estão em quais turmas. Só o admin faz a
    # matrícula (mesmo padrão de permissão das turmas).
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS matriculas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aluno_id INTEGER NOT NULL,
            turma_id INTEGER NOT NULL,
            criado_em TEXT NOT NULL,
            FOREIGN KEY (aluno_id) REFERENCES users (id),
            FOREIGN KEY (turma_id) REFERENCES turmas (id),
            UNIQUE (aluno_id, turma_id)
        )
    ''')

    # Pedaços de texto extraídos dos PDFs de material, com embedding, pra
    # alimentar a busca do chat de IA do aluno (RAG restrito ao material
    # liberado pelo professor).
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS material_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_id INTEGER NOT NULL,
            indice INTEGER NOT NULL,
            texto TEXT NOT NULL,
            embedding TEXT NOT NULL,
            FOREIGN KEY (material_id) REFERENCES materiais (id)
        )
    ''')

    # Histórico de conversas do aluno com o chat de IA, por turma.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_mensagens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aluno_id INTEGER NOT NULL,
            turma_id INTEGER NOT NULL,
            papel TEXT NOT NULL,
            conteudo TEXT NOT NULL,
            fontes TEXT,
            criado_em TEXT NOT NULL,
            FOREIGN KEY (aluno_id) REFERENCES users (id),
            FOREIGN KEY (turma_id) REFERENCES turmas (id)
        )
    ''')

    # Sessões de login. O token é a prova de identidade que as rotas exigem —
    # ver infra/sessoes.py. Fica no banco (e não em memória) para a sessão sobreviver
    # a um restart do servidor e para poder ser revogada.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessoes (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            criado_em TEXT NOT NULL,
            expira_em TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessoes_user ON sessoes (user_id)")

    # Configurações da instituição que a administração muda pela tela. Hoje
    # só o semestre vigente (regras/semestres.py); chave e valor para a
    # próxima não exigir tabela nova.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS configuracoes (
            chave TEXT PRIMARY KEY,
            valor TEXT NOT NULL,
            atualizado_em TEXT NOT NULL
        )
    ''')

    # Migração: semestre num formato só.
    #
    # Era texto livre, e o banco tinha `2026.2` enquanto os formulários
    # sugeriam `2026/2` — comparados como texto, semestres diferentes. A
    # entrada agora passa por regras/semestres.normalizar_semestre; isto
    # converte o que já estava gravado. Em SQL puro para infra/ não depender de
    # regras/. Idempotente: o que já está em `2026/2` não casa com o padrão.
    #
    # Uma linha por vez, e não um UPDATE só, por causa do UNIQUE de coortes:
    # se existirem "MED 3A · 2026.2" e "MED 3A · 2026/2", converter a primeira
    # colidiria com a segunda. Nesse caso ela fica como está, em vez de a
    # migração derrubar a subida do servidor.
    for tabela in ("turmas", "coortes"):
        linhas = cursor.execute(
            f"SELECT id, semestre FROM {tabela}"
            " WHERE semestre GLOB '[0-9][0-9][0-9][0-9][.-][12]'"
        ).fetchall()
        for linha_id, semestre in linhas:
            try:
                cursor.execute(
                    f"UPDATE {tabela} SET semestre = ? WHERE id = ?",
                    (f"{semestre[:4]}/{semestre[5]}", linha_id),
                )
            except sqlite3.IntegrityError:
                pass

    # Avisos: uma pessoa escrevendo para outras (regras/avisos.py). Diferente
    # das notificações, que nascem sozinhas de eventos do sistema.
    #
    # `geral` = para a instituição inteira (só a administração). Os demais vão
    # para as disciplinas de avisos_turmas. Tabela à parte em vez de uma linha
    # por disciplina: "para todas as minhas disciplinas" é um aviso só no
    # histórico de quem escreveu, e não oito cópias do mesmo texto.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS avisos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            autor_id INTEGER NOT NULL,
            titulo TEXT NOT NULL,
            conteudo TEXT NOT NULL,
            urgente INTEGER NOT NULL DEFAULT 0,
            geral INTEGER NOT NULL DEFAULT 0,
            criado_em TEXT NOT NULL,
            FOREIGN KEY (autor_id) REFERENCES users (id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS avisos_turmas (
            aviso_id INTEGER NOT NULL,
            turma_id INTEGER NOT NULL,
            PRIMARY KEY (aviso_id, turma_id),
            FOREIGN KEY (aviso_id) REFERENCES avisos (id),
            FOREIGN KEY (turma_id) REFERENCES turmas (id)
        )
    ''')
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_avisos_turmas_turma ON avisos_turmas (turma_id)")

    # Favoritos do aluno (regras/favoritos.py). Valem entre semestres: o
    # material marcado no 3º período continua à mão no 6º, quando a matéria
    # volta na revisão para a residência.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS favoritos (
            aluno_id INTEGER NOT NULL,
            material_id INTEGER NOT NULL,
            criado_em TEXT NOT NULL,
            PRIMARY KEY (aluno_id, material_id),
            FOREIGN KEY (aluno_id) REFERENCES users (id),
            FOREIGN KEY (material_id) REFERENCES materiais (id)
        )
    ''')

    # Anotações do aluno (regras/anotacoes.py). **Privadas**: nenhuma rota as
    # entrega a professor ou administração.
    #
    # `material_id` é anulável e `material_titulo` guarda o título do momento:
    # a anotação é trabalho do aluno, e não some porque o professor apagou ou
    # reorganizou o material. Ela fica, dizendo de que material era.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS anotacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aluno_id INTEGER NOT NULL,
            material_id INTEGER,
            material_titulo TEXT NOT NULL,
            trecho TEXT,
            texto TEXT NOT NULL,
            criado_em TEXT NOT NULL,
            atualizado_em TEXT NOT NULL,
            FOREIGN KEY (aluno_id) REFERENCES users (id),
            FOREIGN KEY (material_id) REFERENCES materiais (id)
        )
    ''')
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_anotacoes_aluno ON anotacoes (aluno_id, material_id)"
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_favoritos_material ON favoritos (material_id)")

    # Migração: o aluno pode não aparecer no ranking (regras/ranking.py).
    #
    # Guardado como "oculto" e não como "aparece" para que o padrão da coluna
    # (0) seja o padrão do produto: aparecer, com a opção de sair — como o
    # backlog definiu. Mesmo aparecendo, ninguém é exposto no fundo da lista:
    # o ranking público só mostra o topo.
    cursor.execute("PRAGMA table_info(users)")
    if "ranking_oculto" not in {linha[1] for linha in cursor.fetchall()}:
        cursor.execute("ALTER TABLE users ADD COLUMN ranking_oculto INTEGER NOT NULL DEFAULT 0")

    # Tentativas de login que falharam, para o limite em regras/autenticacao.py.
    #
    # Numa tabela, e não em memória: um contador em memória zera a cada restart
    # do servidor — e reiniciar é justamente o que acontece quando alguém
    # percebe o ataque. Também não depende de haver um processo só.
    #
    # Guarda o e-mail **digitado**, exista a conta ou não. Contar só as contas
    # que existem faria o bloqueio aparecer apenas para elas, e a mensagem de
    # "bloqueado" viraria um verificador de cadastro.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tentativas_login (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            criado_em TEXT NOT NULL
        )
    ''')
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_tentativas_email ON tentativas_login (email, criado_em)"
    )

    # Indices medidos, nao adivinhados.
    #
    # Com 360 alunos e 9.600 trechos de material, EXPLAIN QUERY PLAN mostrava
    # SCAN (varredura da tabela inteira) em seis consultas destes caminhos. Em
    # milissegundos isso ainda nao aparecia, porque a tabela e pequena; a conta
    # muda quando a base cresce, e a busca do chat de IA e a mais exposta, ja
    # que percorre todos os trechos da disciplina a cada pergunta.
    #
    # `matriculas` e `matriculas_coorte` ja tem UNIQUE, mas com o aluno na
    # frente: da para buscar por aluno, nao por turma. E "quem esta nesta
    # disciplina" e exatamente a pergunta mais feita no sistema.
    for indice, tabela, colunas in [
        ("idx_materiais_turma", "materiais", "turma_id"),
        ("idx_chunks_material", "material_chunks", "material_id"),
        ("idx_matriculas_turma", "matriculas", "turma_id"),
        ("idx_turmas_coorte", "turmas", "coorte_id"),
        ("idx_matriculas_coorte_coorte", "matriculas_coorte", "coorte_id"),
        ("idx_excecoes_turma", "excecoes_coorte", "turma_id"),
        ("idx_chat_aluno_turma", "chat_mensagens", "aluno_id, turma_id"),
    ]:
        cursor.execute(f"CREATE INDEX IF NOT EXISTS {indice} ON {tabela} ({colunas})")

    # Notificações geradas por eventos reais (ver regras/notificacoes.py).
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notificacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            titulo TEXT NOT NULL,
            mensagem TEXT NOT NULL,
            link TEXT,
            lida INTEGER NOT NULL DEFAULT 0,
            criado_em TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_notificacoes_user ON notificacoes (user_id, lida)"
    )

    # Registro de acesso do aluno ao material. Alimenta o acompanhamento de
    # estudo da tela inicial — sem ele, "materiais consultados" seria um número
    # inventado, e a regra do projeto é não exibir dado que não existe.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS acessos_material (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aluno_id INTEGER NOT NULL,
            material_id INTEGER NOT NULL,
            criado_em TEXT NOT NULL,
            FOREIGN KEY (aluno_id) REFERENCES users (id),
            FOREIGN KEY (material_id) REFERENCES materiais (id)
        )
    ''')
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_acessos_aluno ON acessos_material (aluno_id)"
    )

    # Marca se o aviso de liberação de um material agendado já foi enviado,
    # para não repetir a cada consulta.
    cursor.execute("PRAGMA table_info(materiais)")
    colunas_materiais = {linha[1] for linha in cursor.fetchall()}
    if "notificado" not in colunas_materiais:
        cursor.execute("ALTER TABLE materiais ADD COLUMN notificado INTEGER DEFAULT 0")

    # Atividades propostas pelo professor.
    #
    # Mesmo desenho dos materiais: `turma_id` na própria linha, então publicar
    # em N turmas cria N atividades. E os mesmos três estados — rascunho,
    # agendado (data_liberacao no futuro) e publicado —, para o aluno nunca ver
    # o que ainda não foi liberado.
    #
    # `tipo` decide quem corrige: 'objetiva' o sistema corrige sozinho
    # comparando com o gabarito; 'dissertativa' espera nota e devolutiva do
    # professor.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS atividades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            professor_id INTEGER NOT NULL,
            turma_id INTEGER NOT NULL,
            titulo TEXT NOT NULL,
            enunciado TEXT,
            tipo TEXT NOT NULL,
            assunto TEXT,
            topico TEXT,
            pontos INTEGER NOT NULL DEFAULT 10,
            rascunho INTEGER NOT NULL DEFAULT 0,
            data_liberacao TEXT,
            prazo TEXT,
            criado_em TEXT NOT NULL,
            atualizado_em TEXT NOT NULL,
            notificado INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (professor_id) REFERENCES users (id),
            FOREIGN KEY (turma_id) REFERENCES turmas (id)
        )
    ''')
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_atividades_turma ON atividades (turma_id)"
    )

    # Questões de uma atividade objetiva.
    #
    # `alternativas` guarda uma lista JSON em vez de virar uma quarta tabela:
    # alternativa não é consultada sozinha, só existe dentro da questão e
    # sempre é lida inteira. `correta` é o índice na lista — o gabarito nunca
    # sai do servidor para o aluno (ver regras/atividades.py).
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            atividade_id INTEGER NOT NULL,
            ordem INTEGER NOT NULL,
            enunciado TEXT NOT NULL,
            alternativas TEXT NOT NULL,
            correta INTEGER NOT NULL,
            FOREIGN KEY (atividade_id) REFERENCES atividades (id)
        )
    ''')
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_questoes_atividade ON questoes (atividade_id)"
    )

    # O que o aluno respondeu.
    #
    # Uma linha por aluno por atividade (daí o UNIQUE), criada já no primeiro
    # rascunho. **`enviado_em NULL` é o progresso salvo e ainda não entregue** —
    # é assim que o aluno fecha a aba e retoma de onde parou, sem precisar de
    # uma coluna de estado que poderia discordar da data.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS entregas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            atividade_id INTEGER NOT NULL,
            aluno_id INTEGER NOT NULL,
            respostas TEXT,
            enviado_em TEXT,
            nota REAL,
            devolutiva TEXT,
            corrigido_em TEXT,
            atualizado_em TEXT NOT NULL,
            FOREIGN KEY (atividade_id) REFERENCES atividades (id),
            FOREIGN KEY (aluno_id) REFERENCES users (id),
            UNIQUE (atividade_id, aluno_id)
        )
    ''')
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_entregas_atividade ON entregas (atividade_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_entregas_aluno ON entregas (aluno_id)"
    )

    # Migração: entrega em documento.
    #
    # Nem toda atividade cabe numa caixa de texto — relatório de caso clínico,
    # foto de peça anatômica, traçado de ECG. O anexo é propriedade da
    # **atividade**, e não um terceiro tipo: "entregue o PDF e escreva um
    # resumo" é uma atividade só, e `dissertativa` já quer dizer "quem corrige
    # é gente". Valores: 'nenhum' (padrão), 'opcional', 'obrigatorio'.
    cursor.execute("PRAGMA table_info(atividades)")
    colunas_atividades = {linha[1] for linha in cursor.fetchall()}
    if "anexo" not in colunas_atividades:
        cursor.execute(
            "ALTER TABLE atividades ADD COLUMN anexo TEXT NOT NULL DEFAULT 'nenhum'"
        )

    # O nome original fica no banco e o arquivo no disco com nome de uuid: nome
    # vindo do cliente traz "../" e colide entre dois alunos que chamaram o
    # trabalho de "relatorio.pdf".
    cursor.execute("PRAGMA table_info(entregas)")
    colunas_entregas = {linha[1] for linha in cursor.fetchall()}
    if "arquivo_nome" not in colunas_entregas:
        cursor.execute("ALTER TABLE entregas ADD COLUMN arquivo_nome TEXT")
    if "arquivo_caminho" not in colunas_entregas:
        cursor.execute("ALTER TABLE entregas ADD COLUMN arquivo_caminho TEXT")

    # Conteúdo reportado por aluno ou professor.
    #
    # `material_id` aceita NULL porque o material pode ser excluído depois da
    # denúncia — e apagar a denúncia junto esconderia justamente o histórico
    # que a administração precisa para justificar a exclusão. O título fica
    # copiado em `material_titulo` pelo mesmo motivo: sem ele, a denúncia de um
    # material excluído viraria uma linha sem assunto.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS denuncias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            autor_id INTEGER NOT NULL,
            material_id INTEGER,
            material_titulo TEXT,
            turma_id INTEGER,
            motivo TEXT NOT NULL,
            descricao TEXT,
            status TEXT NOT NULL DEFAULT 'aberta',
            acao TEXT,
            criado_em TEXT NOT NULL,
            atualizado_em TEXT NOT NULL,
            FOREIGN KEY (autor_id) REFERENCES users (id)
        )
    ''')
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_denuncias_status ON denuncias (status)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_denuncias_autor ON denuncias (autor_id)"
    )

    # Conversa entre professor e aluno.
    #
    # Nome `mensagens` para não confundir com `chat_mensagens`, que é o
    # histórico do assistente de IA. São coisas diferentes: lá o aluno fala com
    # o material; aqui, com uma pessoa.
    #
    # A conversa é identificada por (turma_id, aluno_id) — o professor é o dono
    # da turma. Guardar `autor_id` em vez de um campo "de/para" deixa claro
    # quem escreveu sem duplicar a identidade dos dois lados.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mensagens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            turma_id INTEGER NOT NULL,
            aluno_id INTEGER NOT NULL,
            autor_id INTEGER NOT NULL,
            conteudo TEXT NOT NULL,
            lida INTEGER NOT NULL DEFAULT 0,
            criado_em TEXT NOT NULL,
            FOREIGN KEY (turma_id) REFERENCES turmas (id),
            FOREIGN KEY (aluno_id) REFERENCES users (id),
            FOREIGN KEY (autor_id) REFERENCES users (id)
        )
    ''')
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_mensagens_conversa"
        "  ON mensagens (turma_id, aluno_id, criado_em)"
    )

    # Privacidade (regras/privacidade.py). A conta excluída passa por dois
    # estados: **desativada** (não entra, mas os dados continuam, para a
    # administração poder voltar atrás) e, 45 dias depois, **anonimizada**
    # (nome e e-mail somem; notas e entregas ficam, sem dono identificável).
    cursor.execute("PRAGMA table_info(users)")
    colunas_users = {linha[1] for linha in cursor.fetchall()}
    if "desativado_em" not in colunas_users:
        cursor.execute("ALTER TABLE users ADD COLUMN desativado_em TEXT")
    if "anonimizado_em" not in colunas_users:
        cursor.execute("ALTER TABLE users ADD COLUMN anonimizado_em TEXT")

    # Os pedidos que o titular faz sobre os próprios dados. Ficam guardados
    # depois de atendidos, inclusive a exportação (que é automática): provar
    # que o pedido foi atendido, e quando, também é obrigação da LGPD.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS solicitacoes_privacidade (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aluno_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            status TEXT NOT NULL,
            campo TEXT,
            valor_novo TEXT,
            motivo TEXT,
            resposta TEXT,
            criado_em TEXT NOT NULL,
            decidido_em TEXT,
            decidido_por INTEGER,
            anonimizar_em TEXT,
            concluido_em TEXT,
            FOREIGN KEY (aluno_id) REFERENCES users (id),
            FOREIGN KEY (decidido_por) REFERENCES users (id)
        )
    ''')
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_solicitacoes_privacidade_status"
        "  ON solicitacoes_privacidade (status, criado_em)"
    )

    conexao.commit()
    conexao.close()


if __name__ == "__main__":
    configurar_banco()
