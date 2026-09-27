import os
import sqlite3

from infra.security import hash_senha

# Caminho único do banco. Os outros módulos importam daqui em vez de repetir
# a string — já esteve duplicado em três arquivos, e bastaria mudar um deles
# para o sistema passar a gravar em dois bancos diferentes sem avisar.
# DELTACARE_DB permite apontar para outro arquivo (é o que os testes usam,
# para não tocar no banco de demonstração).
CAMINHO_DB = os.environ.get("DELTACARE_DB", "deltacare.db")


def configurar_banco(silencioso: bool = False):
    """Cria as tabelas que ainda não existem. Seguro chamar várias vezes.

    `silencioso` existe para os testes: eles recriam o banco a cada caso, e as
    mensagens de conexão afogariam o resultado da suíte.
    """
    if not silencioso:
        print("Python está procurando o banco em:", os.path.abspath(CAMINHO_DB))

    conexao = sqlite3.connect(CAMINHO_DB)
    cursor = conexao.cursor()

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

    conexao.commit()
    conexao.close()


if __name__ == "__main__":
    configurar_banco()
