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

    # Turmas do professor.
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

    conexao.commit()
    conexao.close()


if __name__ == "__main__":
    configurar_banco()
