"""Testes automatizados das regras de negócio do Delta Care.

    python testes.py

Roda num banco temporário (variável DELTACARE_DB), então não toca nos dados de
demonstração. **Não precisa do Ollama ligado**: as funções que falam com o
modelo entram como parâmetro (`gerar_embedding_fn` / `gerar_resposta_fn`), que
é justamente para isso que elas foram isoladas em regras/chat_ia.py.

O foco é o que dá prejuízo se quebrar em silêncio: permissão, visibilidade de
material e sessão. Interface e formatação não são testadas aqui — um erro de
CSS aparece na tela; um erro de permissão, não.

Usa `unittest`, da biblioteca padrão, para o projeto não ganhar dependência.
"""

import base64
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

# Precisa vir antes de qualquer import do projeto: os módulos leem o caminho
# do banco e da pasta de arquivos no momento em que são importados.
#
# **Um banco e uma pasta por processo** (o pid no nome). Com caminho fixo, duas
# suítes rodando ao mesmo tempo apagavam o banco uma da outra no setUp e davam
# dezenas de erros falsos — e rodar em paralelo passa a ser possível (ver
# rodar_testes.py).
#
# A pasta de arquivos também sai de backend/uploads: os testes de entrega
# apagam a pasta no teardown, e sem isto apagavam as entregas reais do
# servidor de desenvolvimento.
_ARQUIVO_TEMP = os.path.join(tempfile.gettempdir(), f"deltacare_testes_{os.getpid()}.db")
os.environ["DELTACARE_DB"] = _ARQUIVO_TEMP
os.environ["DELTACARE_UPLOADS"] = os.path.join(
    tempfile.gettempdir(), f"deltacare_testes_uploads_{os.getpid()}"
)

import sqlite3  # noqa: E402

from infra.database import CAMINHO_DB, configurar_banco  # noqa: E402
from regras.autenticacao import (  # noqa: E402
    JANELA_LOGIN_MINUTOS,
    MAX_FALHAS_LOGIN,
    MAX_TENTATIVAS_RESET,
    criar_conta_staff,
    realizar_login,
    redefinir_senha,
    solicitar_recuperacao,
)
from regras.aluno import (  # noqa: E402
    MAX_PERGUNTAS_QUE_PONTUAM_POR_DIA,
    XP_POR_ATIVIDADE_ENTREGUE,
    listar_materiais_do_aluno,
    obter_arquivo_material_do_aluno,
    registrar_acesso_material,
    resumo_do_aluno,
    FAIXAS,
    faixa_do_nivel,
)
from regras.atividades import (  # noqa: E402
    obter_arquivo_entrega,
    corrigir_entrega,
    criar_atividade_em_turmas,
    enviar_entrega,
    excluir_atividade,
    listar_atividades,
    listar_atividades_do_aluno,
    listar_entregas,
    obter_atividade,
    obter_atividade_do_aluno,
    salvar_progresso,
)
from regras.calendario import eventos_do_mes  # noqa: E402
from regras.mensagens import (  # noqa: E402
    abrir_conversa,
    enviar_mensagem,
    listar_conversas,
)
from regras.denuncias import (  # noqa: E402
    criar_denuncia,
    listar_minhas,
    listar_todas,
    remover_denuncia,
    tratar_denuncia,
)
from regras.desempenho import desempenho_da_turma, desempenho_do_aluno  # noqa: E402
from regras.importacao import analisar_planilha, importar_alunos  # noqa: E402
from regras.materiais import (  # noqa: E402
    atualizar_material,
    criar_material,
    criar_material_em_turmas,
    excluir_material,
    listar_materiais,
)
from regras.notificacoes import (  # noqa: E402
    listar_notificacoes,
    marcar_como_lida,
    marcar_todas_como_lidas,
)
from regras.matriculas import (  # noqa: E402
    listar_alunos_da_turma,
    listar_turmas_do_aluno,
    matricular_aluno,
)
from regras.turmas import criar_turma, excluir_turma, listar_usuarios  # noqa: E402
from regras.coortes import (  # noqa: E402
    criar_coorte,
    criar_excecao,
    excluir_coorte,
    listar_alunos_da_coorte,
    listar_coortes,
    listar_disciplinas_da_coorte,
    matricular_na_coorte,
    remover_da_coorte,
    remover_excecao,
    sincronizar_coorte,
)
from infra.security import hash_senha, verificar_senha  # noqa: E402
from infra.sessoes import buscar_usuario_da_sessao, criar_sessao, encerrar_sessao  # noqa: E402
from regras import chat_ia  # noqa: E402

from regras.conteudo import (  # noqa: E402
    arquivo_para_supervisao,
    atividade_para_supervisao,
    visao_do_conteudo,
)
from regras.anotacoes import (  # noqa: E402
    criar_anotacao,
    editar_anotacao,
    excluir_anotacao,
    listar_anotacoes,
)
from regras.favoritos import desmarcar_favorito, listar_favoritos, marcar_favorito  # noqa: E402
from regras.avisos import (  # noqa: E402
    DIAS_NO_TOPO,
    excluir_aviso,
    listar_avisos_enviados,
    listar_avisos_recebidos,
    publicar_aviso,
)
from regras.ranking import (  # noqa: E402
    DIAS_DA_EVOLUCAO,
    TAMANHO_DO_TOPO,
    definir_visibilidade,
    ranking_da_turma,
)
from regras.semestres import (  # noqa: E402
    chave_de_ordem,
    definir_semestre_vigente,
    historico_do_aluno,
    historico_do_professor,
    normalizar_semestre,
    obter_semestre_vigente,
    semestre_do_calendario,
    semestre_vigente,
)

SENHA = "teste123"
SEMESTRE_DOS_TESTES = "2026/2"

ADMIN = "admin@teste.com"
PROFESSOR = "prof1@teste.com"
PROFESSOR2 = "prof2@teste.com"
ALUNO = "aluno1@teste.com"
ALUNO_FORA = "aluno2@teste.com"


# =========================================================================
# Dublês do modelo de IA
# =========================================================================

def embedding_falso(texto: str) -> list:
    """Vetor determinístico a partir do texto.

    Não precisa ser um embedding de verdade: o que os testes verificam é
    *quais trechos entram na busca* (permissão e visibilidade), não a
    qualidade semântica do ranking. Textos iguais geram vetores iguais, o que
    basta para o cosseno se comportar de forma previsível.
    """
    vetor = [0.0] * 16
    for posicao, caractere in enumerate(texto.casefold()):
        vetor[posicao % 16] += (ord(caractere) % 13) / 100
    return vetor


def resposta_falsa(mensagens: list, schema: dict | None = None) -> dict:
    """Devolve o material citado no contexto, imitando o structured output."""
    contexto = mensagens[-1]["content"]
    titulos = []

    if schema:
        possiveis = schema["properties"]["fontes_usadas"]["items"].get("enum", [])
        titulos = [t for t in possiveis if t in contexto]

    return {"resposta": "Resposta de teste.", "fontes_usadas": titulos}


class BaseDelta(unittest.TestCase):
    """Cria um banco limpo e os personagens usados pelos testes."""

    def setUp(self):
        if os.path.exists(CAMINHO_DB):
            os.remove(CAMINHO_DB)

        configurar_banco(silencioso=True)

        conexao = sqlite3.connect(CAMINHO_DB)
        conexao.execute(
            "INSERT INTO users (email, senha, tipo, nome) VALUES (?, ?, ?, ?)",
            (ADMIN, hash_senha(SENHA), "adm", "Admin Teste"),
        )
        conexao.commit()
        conexao.close()

        # O semestre vigente fica fixo. Sem isto ele viria do calendário, e a
        # partir de janeiro de 2027 as disciplinas dos testes (2026/2) virariam
        # "semestre anterior" sozinhas — todo teste de XP quebraria numa manhã
        # sem ninguém ter mexido em nada.
        definir_semestre_vigente(ADMIN, SEMESTRE_DOS_TESTES)

        criar_conta_staff(ADMIN, PROFESSOR, SENHA, "professor", nome="Professor Um")
        criar_conta_staff(ADMIN, PROFESSOR2, SENHA, "professor", nome="Professor Dois")
        criar_conta_staff(ADMIN, ALUNO, SENHA, "aluno", nome="Aluno Um")
        criar_conta_staff(ADMIN, ALUNO_FORA, SENHA, "aluno", nome="Aluno Dois")

        self.turma_id = criar_turma(ADMIN, PROFESSOR, "Cardiologia", "2026.2")["turma"]["id"]
        matricular_aluno(ADMIN, ALUNO, self.turma_id)

    def tearDown(self):
        if os.path.exists(CAMINHO_DB):
            os.remove(CAMINHO_DB)

    def criar_material_simples(self, titulo, rascunho=False, data_liberacao=None, professor=PROFESSOR, turma_id=None):
        resultado = criar_material(
            professor_email=professor,
            turma_id=turma_id if turma_id is not None else self.turma_id,
            titulo=titulo,
            tipo="link",
            link_url="https://exemplo.com",
            rascunho=rascunho,
            data_liberacao=data_liberacao,
        )
        return resultado


# =========================================================================
# Senhas e contas
# =========================================================================

class TestesSenha(unittest.TestCase):

    def test_hash_nao_guarda_a_senha(self):
        resultado = hash_senha("minhasenha")
        self.assertNotIn("minhasenha", resultado)

    def test_hashes_diferentes_para_a_mesma_senha(self):
        """Salt individual: dois usuários com a mesma senha têm hashes diferentes."""
        self.assertNotEqual(hash_senha("igual"), hash_senha("igual"))

    def test_verificacao(self):
        armazenado = hash_senha("correta")
        self.assertTrue(verificar_senha("correta", armazenado))
        self.assertFalse(verificar_senha("errada", armazenado))

    def test_hash_corrompido_nao_autentica(self):
        self.assertFalse(verificar_senha("qualquer", "lixo-sem-formato"))


class TestesContas(BaseDelta):

    def test_ninguem_cria_conta_sozinho_pela_internet(self):
        """Toda conta nasce pela administração (ou pela planilha). O cadastro
        público que existia não era usado por nenhuma tela e deixava qualquer
        pessoa criar conta de aluno."""
        from fastapi.testclient import TestClient

        import main

        resposta = TestClient(main.app).post(
            "/cadastro",
            json={"email": "invasor@teste.com", "senha": SENHA, "tipo": "aluno", "nome": "Invasor"},
        )

        self.assertIn(resposta.status_code, (404, 405))
        self.assertFalse(realizar_login("invasor@teste.com", SENHA)["sucesso"])

    def test_so_admin_cria_conta_de_staff(self):
        resultado = criar_conta_staff(PROFESSOR, "novo@teste.com", SENHA, "professor", nome="Novo")
        self.assertFalse(resultado["sucesso"])

    def test_aluno_nao_cria_conta_de_staff(self):
        resultado = criar_conta_staff(ALUNO, "novo@teste.com", SENHA, "adm", nome="Novo")
        self.assertFalse(resultado["sucesso"])

    def test_admin_cria_conta_de_qualquer_perfil(self):
        """A instituição precisa poder cadastrar aluno sem esperar ele se inscrever."""
        for tipo in ("aluno", "professor", "adm"):
            resultado = criar_conta_staff(
                ADMIN, f"criado_{tipo}@teste.com", SENHA, tipo, nome=f"Criado {tipo}"
            )
            self.assertTrue(resultado["sucesso"], f"admin não conseguiu criar {tipo}")

            login = realizar_login(f"criado_{tipo}@teste.com", SENHA)
            self.assertTrue(login["sucesso"], f"conta {tipo} criada não consegue entrar")
            self.assertEqual(login["tipo"], tipo)

    def test_conta_criada_pelo_admin_recusa_senha_curta(self):
        resultado = criar_conta_staff(ADMIN, "curta@teste.com", "123", "professor", nome="Senha Curta")
        self.assertFalse(resultado["sucesso"])

    def test_login_correto_devolve_token(self):
        resultado = realizar_login(ALUNO, SENHA)
        self.assertTrue(resultado["sucesso"])
        self.assertTrue(resultado.get("token"))

    def test_login_com_senha_errada_nao_devolve_token(self):
        resultado = realizar_login(ALUNO, "errada")
        self.assertFalse(resultado["sucesso"])
        self.assertIsNone(resultado.get("token"))


# =========================================================================
# Sessão
# =========================================================================

class TestesSessao(BaseDelta):

    def _id_do_aluno(self):
        conexao = sqlite3.connect(CAMINHO_DB)
        linha = conexao.execute("SELECT id FROM users WHERE email = ?", (ALUNO,)).fetchone()
        conexao.close()
        return linha[0]

    def test_token_valido_identifica_o_dono(self):
        token = criar_sessao(self._id_do_aluno())
        usuario = buscar_usuario_da_sessao(token)
        self.assertEqual(usuario["email"], ALUNO)
        self.assertEqual(usuario["tipo"], "aluno")

    def test_token_inexistente(self):
        self.assertIsNone(buscar_usuario_da_sessao("token-que-nunca-existiu"))

    def test_token_vazio(self):
        self.assertIsNone(buscar_usuario_da_sessao(""))

    def test_logout_invalida(self):
        token = criar_sessao(self._id_do_aluno())
        encerrar_sessao(token)
        self.assertIsNone(buscar_usuario_da_sessao(token))

    def test_token_expirado_nao_vale(self):
        token = criar_sessao(self._id_do_aluno())
        conexao = sqlite3.connect(CAMINHO_DB)
        conexao.execute(
            "UPDATE sessoes SET expira_em = ? WHERE token = ?",
            ("2020-01-01T00:00:00+00:00", token),
        )
        conexao.commit()
        conexao.close()
        self.assertIsNone(buscar_usuario_da_sessao(token))

    def test_tokens_sao_diferentes(self):
        aluno_id = self._id_do_aluno()
        tokens = {criar_sessao(aluno_id) for _ in range(20)}
        self.assertEqual(len(tokens), 20)


# =========================================================================
# Permissões de turma e material
# =========================================================================

class TestesPermissoes(BaseDelta):

    def test_professor_nao_cria_turma(self):
        resultado = criar_turma(PROFESSOR, PROFESSOR, "Turma Pirata", "2026.2")
        self.assertFalse(resultado["sucesso"])

    def test_aluno_nao_cria_turma(self):
        resultado = criar_turma(ALUNO, PROFESSOR, "Turma Pirata", "2026.2")
        self.assertFalse(resultado["sucesso"])

    def test_professor_nao_matricula_aluno(self):
        resultado = matricular_aluno(PROFESSOR, ALUNO_FORA, self.turma_id)
        self.assertFalse(resultado["sucesso"])

    def test_professor_nao_cria_material_em_turma_alheia(self):
        resultado = self.criar_material_simples("Material intruso", professor=PROFESSOR2)
        self.assertFalse(resultado["sucesso"])

    def test_professor_nao_edita_material_de_outro(self):
        """O ataque que existia antes da sessão: agir em nome de outro professor."""
        material_id = self.criar_material_simples("Material do prof1")["material_id"]

        resultado = atualizar_material(material_id, PROFESSOR2, titulo="INVADIDO")
        self.assertFalse(resultado["sucesso"])

        materiais = listar_materiais(PROFESSOR)["materiais"]
        self.assertEqual(materiais[0]["titulo"], "Material do prof1")

    def test_professor_nao_exclui_material_de_outro(self):
        material_id = self.criar_material_simples("Material do prof1")["material_id"]
        self.assertFalse(excluir_material(material_id, PROFESSOR2)["sucesso"])
        self.assertEqual(len(listar_materiais(PROFESSOR)["materiais"]), 1)

    def test_professor_so_lista_os_proprios_materiais(self):
        self.criar_material_simples("Material do prof1")
        self.assertEqual(len(listar_materiais(PROFESSOR2)["materiais"]), 0)


# =========================================================================
# Visibilidade do material para o aluno
# =========================================================================

class TestesVisibilidadeAluno(BaseDelta):

    def test_aluno_ve_material_publicado(self):
        self.criar_material_simples("Aula publicada")
        titulos = [m["titulo"] for m in listar_materiais_do_aluno(ALUNO)["materiais"]]
        self.assertIn("Aula publicada", titulos)

    def test_aluno_nao_ve_rascunho(self):
        self.criar_material_simples("Rascunho secreto", rascunho=True)
        titulos = [m["titulo"] for m in listar_materiais_do_aluno(ALUNO)["materiais"]]
        self.assertNotIn("Rascunho secreto", titulos)

    def test_aluno_nao_ve_material_agendado_para_o_futuro(self):
        self.criar_material_simples("Agendado", rascunho=False, data_liberacao="2090-01-01T00:00:00+00:00")
        titulos = [m["titulo"] for m in listar_materiais_do_aluno(ALUNO)["materiais"]]
        self.assertNotIn("Agendado", titulos)

    def test_aluno_ve_agendado_cuja_data_ja_passou(self):
        """Material agendado vira publicado sozinho quando a data chega."""
        self.criar_material_simples("Liberado ontem", rascunho=False, data_liberacao="2020-01-01T00:00:00+00:00")
        titulos = [m["titulo"] for m in listar_materiais_do_aluno(ALUNO)["materiais"]]
        self.assertIn("Liberado ontem", titulos)

    def test_aluno_nao_matriculado_nao_ve_nada(self):
        self.criar_material_simples("Aula publicada")
        self.assertEqual(len(listar_materiais_do_aluno(ALUNO_FORA)["materiais"]), 0)

    def test_professor_ve_rascunho_que_o_aluno_nao_ve(self):
        """As duas visões existem e são diferentes de propósito."""
        self.criar_material_simples("Rascunho secreto", rascunho=True)

        do_professor = [m["titulo"] for m in listar_materiais(PROFESSOR)["materiais"]]
        do_aluno = [m["titulo"] for m in listar_materiais_do_aluno(ALUNO)["materiais"]]

        self.assertIn("Rascunho secreto", do_professor)
        self.assertNotIn("Rascunho secreto", do_aluno)

    def test_download_de_rascunho_pela_url_direta_e_negado(self):
        material_id = self.criar_material_simples("Rascunho secreto", rascunho=True)["material_id"]
        self.assertIsNone(obter_arquivo_material_do_aluno(ALUNO, material_id))

    def test_resumo_conta_so_o_que_o_aluno_pode_ver(self):
        self.criar_material_simples("Publicado 1")
        self.criar_material_simples("Publicado 2")
        self.criar_material_simples("Rascunho", rascunho=True)

        resumo = resumo_do_aluno(ALUNO)
        self.assertEqual(resumo["total_materiais"], 2)
        self.assertEqual(resumo["total_turmas"], 1)


# =========================================================================
# Chat de IA (sem Ollama, usando os dublês)
# =========================================================================

class TestesChat(BaseDelta):

    def test_aluno_nao_matriculado_nao_pergunta(self):
        resultado = chat_ia.responder_pergunta(
            ALUNO_FORA, self.turma_id, "Qualquer pergunta?",
            gerar_embedding_fn=embedding_falso, gerar_resposta_fn=resposta_falsa,
        )
        self.assertFalse(resultado["sucesso"])
        self.assertIn("matriculado", resultado["mensagem"])

    def test_pergunta_vazia(self):
        resultado = chat_ia.responder_pergunta(
            ALUNO, self.turma_id, "   ",
            gerar_embedding_fn=embedding_falso, gerar_resposta_fn=resposta_falsa,
        )
        self.assertFalse(resultado["sucesso"])

    def test_busca_ignora_material_nao_publicado(self):
        """A regra de visibilidade vale também para o que a IA lê."""
        publicado = criar_material(
            professor_email=PROFESSOR, turma_id=self.turma_id,
            titulo="Publicado", tipo="link", link_url="https://exemplo.com", rascunho=False,
        )["material_id"]
        rascunho = criar_material(
            professor_email=PROFESSOR, turma_id=self.turma_id,
            titulo="Rascunho", tipo="link", link_url="https://exemplo.com", rascunho=True,
        )["material_id"]

        # Indexa os dois à mão (criar_material só indexa PDF).
        conexao = sqlite3.connect(CAMINHO_DB)
        for material_id, texto in ((publicado, "conteudo liberado"), (rascunho, "conteudo secreto")):
            import json
            conexao.execute(
                "INSERT INTO material_chunks (material_id, indice, texto, embedding) VALUES (?, ?, ?, ?)",
                (material_id, 0, texto, json.dumps(embedding_falso(texto))),
            )
        conexao.commit()
        conexao.close()

        trechos = chat_ia.buscar_trechos_relevantes(
            self.turma_id, "conteudo", gerar_embedding_fn=embedding_falso, top_k=10,
        )
        textos = [t["texto"] for t in trechos]

        self.assertIn("conteudo liberado", textos)
        self.assertNotIn("conteudo secreto", textos)

    def test_schema_restringe_as_fontes_aos_materiais_reais(self):
        schema = chat_ia.montar_schema_resposta(["Aula 1", "Aula 2"])
        enum = schema["properties"]["fontes_usadas"]["items"]["enum"]
        self.assertEqual(enum, ["Aula 1", "Aula 2"])

    def test_schema_sem_materiais_nao_tem_enum_vazio(self):
        """enum vazio é JSON Schema inválido e quebraria a chamada."""
        schema = chat_ia.montar_schema_resposta([])
        self.assertNotIn("enum", schema["properties"]["fontes_usadas"]["items"])

    def test_termos_distintivos_ignoram_palavras_comuns(self):
        termos = chat_ia._termos_distintivos("Qual a dose inicial de Cardiolex?")
        self.assertIn("cardiolex", termos)
        self.assertNotIn("qual", termos)

    def test_bonus_literal_favorece_trecho_com_o_termo(self):
        termos = chat_ia._termos_distintivos("O que e o escore ARR-7?")
        com = chat_ia._pontuar_trecho("o escore ARR-7 soma idade", 0.50, termos)
        sem = chat_ia._pontuar_trecho("texto generico de cardiologia", 0.50, termos)
        self.assertGreater(com, sem)

    def test_chunking_cobre_o_texto_inteiro(self):
        texto = "palavra " * 500
        chunks = chat_ia.dividir_em_chunks(texto)
        self.assertGreater(len(chunks), 1)
        # a sobreposição não pode deixar buraco entre os pedaços
        self.assertIn(chunks[0][-20:], texto)


# =========================================================================
# Integridade do banco ao excluir
# =========================================================================

class TestesExclusao(BaseDelta):

    def _contar(self, tabela):
        conexao = sqlite3.connect(CAMINHO_DB)
        total = conexao.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]
        conexao.close()
        return total

    def test_excluir_material_remove_os_trechos_indexados(self):
        material_id = self.criar_material_simples("Para excluir")["material_id"]

        conexao = sqlite3.connect(CAMINHO_DB)
        conexao.execute(
            "INSERT INTO material_chunks (material_id, indice, texto, embedding) VALUES (?, ?, ?, ?)",
            (material_id, 0, "texto", "[0.1]"),
        )
        conexao.commit()
        conexao.close()

        self.assertEqual(self._contar("material_chunks"), 1)
        excluir_material(material_id, PROFESSOR)
        self.assertEqual(self._contar("material_chunks"), 0, "sobraram trechos órfãos")

    def test_excluir_turma_leva_junto_material_matricula_e_trechos(self):
        material_id = self.criar_material_simples("Material da turma")["material_id"]

        conexao = sqlite3.connect(CAMINHO_DB)
        conexao.execute(
            "INSERT INTO material_chunks (material_id, indice, texto, embedding) VALUES (?, ?, ?, ?)",
            (material_id, 0, "texto", "[0.1]"),
        )
        conexao.commit()
        conexao.close()

        excluir_turma(ADMIN, self.turma_id)

        self.assertEqual(self._contar("turmas"), 0)
        self.assertEqual(self._contar("materiais"), 0)
        self.assertEqual(self._contar("matriculas"), 0)
        self.assertEqual(self._contar("material_chunks"), 0)

    def test_professor_nao_exclui_turma(self):
        self.assertFalse(excluir_turma(PROFESSOR, self.turma_id)["sucesso"])
        self.assertEqual(self._contar("turmas"), 1)


# =========================================================================
# Cadastro: nome e campos por perfil
# =========================================================================

class TestesCadastroCompleto(BaseDelta):

    def test_nome_e_obrigatorio(self):
        resultado = criar_conta_staff(ADMIN, "semnome@teste.com", SENHA, "aluno")
        self.assertFalse(resultado["sucesso"])
        self.assertIn("nome", resultado["mensagem"].lower())

    def test_nome_aparece_no_login(self):
        criar_conta_staff(ADMIN, "comnome@teste.com", SENHA, "professor", nome="Ana Ribeiro")
        self.assertEqual(realizar_login("comnome@teste.com", SENHA)["nome"], "Ana Ribeiro")

    def test_disciplinas_so_para_professor(self):
        criar_conta_staff(ADMIN, "prof3@teste.com", SENHA, "professor",
                          nome="Prof Tres", disciplinas="Neurologia")
        criar_conta_staff(ADMIN, "aluno3@teste.com", SENHA, "aluno",
                          nome="Aluno Tres", disciplinas="Neurologia")

        por_email = {u["email"]: u for u in listar_usuarios(ADMIN)["usuarios"]}
        self.assertEqual(por_email["prof3@teste.com"]["disciplinas"], "Neurologia")
        self.assertEqual(por_email["aluno3@teste.com"]["disciplinas"], "")

    def test_matricula_so_para_aluno(self):
        criar_conta_staff(ADMIN, "aluno4@teste.com", SENHA, "aluno",
                          nome="Aluno Quatro", matricula="2026999")
        criar_conta_staff(ADMIN, "prof4@teste.com", SENHA, "professor",
                          nome="Prof Quatro", matricula="2026999")

        por_email = {u["email"]: u for u in listar_usuarios(ADMIN)["usuarios"]}
        self.assertEqual(por_email["aluno4@teste.com"]["matricula"], "2026999")
        self.assertEqual(por_email["prof4@teste.com"]["matricula"], "")

    def test_criar_aluno_ja_matriculando_na_turma(self):
        """Evita cadastrar a turma inteira e depois matricular um a um."""
        resultado = criar_conta_staff(
            ADMIN, "novo.aluno@teste.com", SENHA, "aluno",
            nome="Novo Aluno", turma_id=self.turma_id,
        )
        self.assertTrue(resultado["sucesso"])

        alunos = listar_alunos_da_turma(ADMIN, self.turma_id)["alunos"]
        self.assertIn("novo.aluno@teste.com", alunos)


# =========================================================================
# Publicacao em varias turmas
# =========================================================================

class TestesMultiplasTurmas(BaseDelta):

    def setUp(self):
        super().setUp()
        self.turma2 = criar_turma(ADMIN, PROFESSOR, "Cardiologia II", "2026.2")["turma"]["id"]

    def test_publica_nas_duas_turmas(self):
        resultado = criar_material_em_turmas(
            PROFESSOR, [self.turma_id, self.turma2],
            titulo="Compartilhado", tipo="link",
            link_url="https://exemplo.com", rascunho=False,
        )
        self.assertTrue(resultado["sucesso"])
        self.assertEqual(len(resultado["material_ids"]), 2)

        for turma in (self.turma_id, self.turma2):
            titulos = [m["titulo"] for m in listar_materiais(PROFESSOR, turma)["materiais"]]
            self.assertIn("Compartilhado", titulos)

    def test_turma_de_outro_professor_derruba_tudo(self):
        """Valida antes de criar: publicacao parcial deixaria o professor sem
        saber em quais turmas o material entrou."""
        turma_alheia = criar_turma(ADMIN, PROFESSOR2, "De outro", "2026.2")["turma"]["id"]

        resultado = criar_material_em_turmas(
            PROFESSOR, [self.turma_id, turma_alheia],
            titulo="Nao deve existir", tipo="link",
            link_url="https://exemplo.com", rascunho=False,
        )

        self.assertFalse(resultado["sucesso"])
        self.assertEqual(len(listar_materiais(PROFESSOR, self.turma_id)["materiais"]), 0)

    def test_lista_de_turmas_vazia(self):
        resultado = criar_material_em_turmas(
            PROFESSOR, [], titulo="Sem turma", tipo="link",
            link_url="https://exemplo.com",
        )
        self.assertFalse(resultado["sucesso"])

    def test_arquivo_compartilhado_sobrevive_a_exclusao_parcial(self):
        """O arquivo e gravado uma vez e compartilhado; excluir de uma turma
        nao pode apagar o arquivo que a outra ainda usa."""
        import base64

        conteudo = base64.b64encode(b"%PDF-1.4 conteudo de teste").decode()
        resultado = criar_material_em_turmas(
            PROFESSOR, [self.turma_id, self.turma2],
            titulo="Com arquivo", tipo="documento", rascunho=False,
            arquivo_base64=conteudo, arquivo_nome="doc.pdf",
        )
        self.assertTrue(resultado["sucesso"])

        primeiro, segundo = resultado["material_ids"]

        conexao = sqlite3.connect(CAMINHO_DB)
        caminho = conexao.execute(
            "SELECT arquivo_caminho FROM materiais WHERE id = ?", (segundo,)
        ).fetchone()[0]
        conexao.close()

        self.assertTrue(os.path.exists(caminho), "arquivo nao foi gravado")

        excluir_material(primeiro, PROFESSOR)
        self.assertTrue(os.path.exists(caminho), "arquivo sumiu com a outra turma ainda usando")

        excluir_material(segundo, PROFESSOR)
        self.assertFalse(os.path.exists(caminho), "arquivo ficou orfao no disco")


# =========================================================================
# Notificacoes
# =========================================================================

class TestesNotificacoes(BaseDelta):

    def test_matricula_avisa_o_professor(self):
        antes = listar_notificacoes(PROFESSOR)["nao_lidas"]
        matricular_aluno(ADMIN, ALUNO_FORA, self.turma_id)
        depois = listar_notificacoes(PROFESSOR)
        self.assertEqual(depois["nao_lidas"], antes + 1)

    def test_material_publicado_avisa_os_alunos(self):
        self.criar_material_simples("Aula nova", rascunho=False)
        self.assertGreaterEqual(listar_notificacoes(ALUNO)["nao_lidas"], 1)

    def test_rascunho_nao_avisa_ninguem(self):
        antes = listar_notificacoes(ALUNO)["nao_lidas"]
        self.criar_material_simples("Rascunho silencioso", rascunho=True)
        self.assertEqual(listar_notificacoes(ALUNO)["nao_lidas"], antes)

    def test_aluno_de_outra_turma_nao_recebe(self):
        self.criar_material_simples("So da turma 1", rascunho=False)
        self.assertEqual(listar_notificacoes(ALUNO_FORA)["nao_lidas"], 0)

    def test_marcar_como_lida(self):
        self.criar_material_simples("Aula nova", rascunho=False)
        notificacao = listar_notificacoes(ALUNO)["notificacoes"][0]

        self.assertTrue(marcar_como_lida(ALUNO, notificacao["id"])["sucesso"])
        self.assertEqual(listar_notificacoes(ALUNO)["nao_lidas"], 0)

    def test_nao_marca_notificacao_de_outro(self):
        """Sem o user_id no WHERE, bastaria saber o id para marcar a de outra
        pessoa como lida."""
        self.criar_material_simples("Aula nova", rascunho=False)
        notificacao = listar_notificacoes(ALUNO)["notificacoes"][0]

        self.assertFalse(marcar_como_lida(ALUNO_FORA, notificacao["id"])["sucesso"])
        self.assertEqual(listar_notificacoes(ALUNO)["nao_lidas"], 1)

    def test_marcar_todas(self):
        self.criar_material_simples("Aula A", rascunho=False)
        self.criar_material_simples("Aula B", rascunho=False)

        self.assertGreaterEqual(listar_notificacoes(ALUNO)["nao_lidas"], 2)
        marcar_todas_como_lidas(ALUNO)
        self.assertEqual(listar_notificacoes(ALUNO)["nao_lidas"], 0)


# =========================================================================
# Progresso do aluno (XP e frequencia)
# =========================================================================

class TestesProgresso(BaseDelta):

    def _id_aluno(self):
        conexao = sqlite3.connect(CAMINHO_DB)
        linha = conexao.execute("SELECT id FROM users WHERE email = ?", (ALUNO,)).fetchone()
        conexao.close()
        return linha[0]

    def test_aluno_novo_comeca_zerado(self):
        progresso = resumo_do_aluno(ALUNO)["progresso"]
        self.assertEqual(progresso["xp"], 0)
        self.assertEqual(progresso["nivel"], 1)
        self.assertEqual(progresso["sequencia"], 0)

    def test_acesso_a_material_gera_xp(self):
        material_id = self.criar_material_simples("Aula com arquivo")["material_id"]
        registrar_acesso_material(ALUNO, material_id)

        progresso = resumo_do_aluno(ALUNO)["progresso"]
        # 15 pelo material + 25 pelo dia de estudo
        self.assertEqual(progresso["xp"], 40)
        self.assertEqual(progresso["materiais_acessados"], 1)

    def test_reabrir_o_mesmo_material_nao_conta_de_novo(self):
        """Cinco aberturas do mesmo PDF nao sao cinco materiais estudados."""
        material_id = self.criar_material_simples("Aula")["material_id"]

        for _ in range(5):
            registrar_acesso_material(ALUNO, material_id)

        self.assertEqual(resumo_do_aluno(ALUNO)["progresso"]["materiais_acessados"], 1)

    def test_composicao_bate_com_o_total(self):
        material_id = self.criar_material_simples("Aula")["material_id"]
        registrar_acesso_material(ALUNO, material_id)

        progresso = resumo_do_aluno(ALUNO)["progresso"]
        soma = sum(item["xp"] for item in progresso["composicao"])
        self.assertEqual(soma, progresso["xp"])

    def test_acompanhamento_tem_a_janela_completa(self):
        progresso = resumo_do_aluno(ALUNO)["progresso"]
        self.assertEqual(len(progresso["acompanhamento"]), 14)

    def test_acesso_de_quem_nao_e_aluno_e_ignorado(self):
        material_id = self.criar_material_simples("Aula")["material_id"]
        registrar_acesso_material(PROFESSOR, material_id)

        conexao = sqlite3.connect(CAMINHO_DB)
        total = conexao.execute("SELECT COUNT(*) FROM acessos_material").fetchone()[0]
        conexao.close()
        self.assertEqual(total, 0)


# =========================================================================
# Importacao em massa
# =========================================================================

class TestesImportacao(BaseDelta):

    def _planilha(self, texto):
        return base64.b64encode(texto.encode("utf-8")).decode()

    def test_le_csv_com_ponto_e_virgula(self):
        """Excel em portugues salva CSV com ponto e virgula."""
        csv = "Nome;E-mail\nAna Costa;ana@teste.com\n"
        resultado = analisar_planilha(self._planilha(csv), "alunos.csv")

        self.assertTrue(resultado["sucesso"])
        self.assertEqual(len(resultado["validos"]), 1)
        self.assertEqual(resultado["validos"][0]["nome"], "Ana Costa")

    def test_le_csv_com_virgula(self):
        csv = "Nome,E-mail\nAna Costa,ana@teste.com\n"
        resultado = analisar_planilha(self._planilha(csv), "alunos.csv")
        self.assertEqual(len(resultado["validos"]), 1)

    def test_aceita_cabecalho_alternativo(self):
        """A secretaria nao deveria ter que renomear as colunas."""
        csv = "Aluno;Correio;RA\nBruno Dias;bruno@teste.com;2026\n"
        resultado = analisar_planilha(self._planilha(csv), "alunos.csv")

        self.assertTrue(resultado["sucesso"])
        self.assertEqual(resultado["validos"][0]["matricula"], "2026")

    def test_rejeita_linha_sem_nome(self):
        csv = "Nome;E-mail\n;semnome@teste.com\n"
        resultado = analisar_planilha(self._planilha(csv), "alunos.csv")

        self.assertEqual(len(resultado["validos"]), 0)
        self.assertEqual(len(resultado["rejeitados"]), 1)
        self.assertIn("nome", resultado["rejeitados"][0]["motivo"].lower())

    def test_rejeita_email_invalido(self):
        csv = "Nome;E-mail\nAna;nao-eh-email\n"
        resultado = analisar_planilha(self._planilha(csv), "alunos.csv")
        self.assertEqual(len(resultado["rejeitados"]), 1)

    def test_rejeita_email_repetido_na_planilha(self):
        csv = "Nome;E-mail\nAna;a@teste.com\nAna de novo;a@teste.com\n"
        resultado = analisar_planilha(self._planilha(csv), "alunos.csv")

        self.assertEqual(len(resultado["validos"]), 1)
        self.assertEqual(len(resultado["rejeitados"]), 1)

    def test_exige_colunas_obrigatorias(self):
        csv = "Telefone;Cidade\n1199;Sao Paulo\n"
        resultado = analisar_planilha(self._planilha(csv), "alunos.csv")

        self.assertFalse(resultado["sucesso"])
        self.assertIn("nome", resultado["mensagem"].lower())

    def test_formato_nao_suportado(self):
        resultado = analisar_planilha(self._planilha("qualquer"), "alunos.pdf")
        self.assertFalse(resultado["sucesso"])

    def test_analisar_nao_grava_nada(self):
        """Conferir e importar sao etapas separadas de proposito."""
        antes = len(listar_usuarios(ADMIN)["usuarios"])

        csv = "Nome;E-mail\nAna Costa;ana@teste.com\n"
        analisar_planilha(self._planilha(csv), "alunos.csv")

        self.assertEqual(len(listar_usuarios(ADMIN)["usuarios"]), antes)

    def test_importa_e_matricula_na_turma(self):
        csv = "Nome;E-mail;Matricula\nAna Costa;ana@teste.com;2026\nBruno Dias;bruno@teste.com;2027\n"
        resultado = importar_alunos(
            ADMIN, self._planilha(csv), "alunos.csv",
            turma_id=self.turma_id, senha_padrao=SENHA,
        )

        self.assertTrue(resultado["sucesso"])
        self.assertEqual(resultado["total_criados"], 2)

        alunos = listar_alunos_da_turma(ADMIN, self.turma_id)["alunos"]
        self.assertIn("ana@teste.com", alunos)
        self.assertIn("bruno@teste.com", alunos)

    def test_importado_consegue_entrar(self):
        csv = "Nome;E-mail\nAna Costa;ana@teste.com\n"
        importar_alunos(ADMIN, self._planilha(csv), "alunos.csv", senha_padrao=SENHA)

        login = realizar_login("ana@teste.com", SENHA)
        self.assertTrue(login["sucesso"])
        self.assertEqual(login["nome"], "Ana Costa")

    def test_linha_invalida_nao_impede_as_outras(self):
        csv = "Nome;E-mail\nAna Costa;ana@teste.com\n;sem@teste.com\nBruno Dias;bruno@teste.com\n"
        resultado = importar_alunos(ADMIN, self._planilha(csv), "alunos.csv", senha_padrao=SENHA)

        self.assertEqual(resultado["total_criados"], 2)
        self.assertEqual(resultado["total_rejeitados"], 1)

    def test_reimportar_rejeita_duplicados(self):
        csv = "Nome;E-mail\nAna Costa;ana@teste.com\n"
        importar_alunos(ADMIN, self._planilha(csv), "alunos.csv", senha_padrao=SENHA)

        segunda = importar_alunos(ADMIN, self._planilha(csv), "alunos.csv", senha_padrao=SENHA)
        self.assertEqual(segunda["total_criados"], 0)
        self.assertEqual(segunda["total_rejeitados"], 1)

    def test_senha_curta_nao_importa(self):
        csv = "Nome;E-mail\nAna Costa;ana@teste.com\n"
        resultado = importar_alunos(ADMIN, self._planilha(csv), "alunos.csv", senha_padrao="123")
        self.assertFalse(resultado["sucesso"])

    def test_so_admin_importa(self):
        csv = "Nome;E-mail\nAna Costa;ana@teste.com\n"
        resultado = importar_alunos(PROFESSOR, self._planilha(csv), "alunos.csv", senha_padrao=SENHA)
        self.assertEqual(resultado["total_criados"], 0)



# =========================================================================
# Atividades — professor
# =========================================================================

class BaseAtividades(BaseDelta):
    """Base com atalhos para montar atividades nos testes."""

    QUESTOES = [
        {"enunciado": "Qual a dose inicial?", "alternativas": ["2 mg", "5 mg", "8 mg"], "correta": 1},
        {"enunciado": "Quantas fases tem o protocolo?", "alternativas": ["2", "3"], "correta": 1},
    ]

    def criar_objetiva(self, titulo="Quiz", rascunho=False, data_liberacao=None,
                       prazo=None, professor=PROFESSOR, turma_id=None, pontos=10):
        return criar_atividade_em_turmas(
            professor,
            [turma_id if turma_id is not None else self.turma_id],
            titulo=titulo,
            tipo="objetiva",
            pontos=pontos,
            rascunho=rascunho,
            data_liberacao=data_liberacao,
            prazo=prazo,
            questoes=[dict(q) for q in self.QUESTOES],
        )

    def criar_dissertativa(self, titulo="Resumo", rascunho=False, prazo=None, pontos=10):
        return criar_atividade_em_turmas(
            PROFESSOR,
            [self.turma_id],
            titulo=titulo,
            tipo="dissertativa",
            enunciado="Escreva um resumo da aula.",
            pontos=pontos,
            rascunho=rascunho,
            prazo=prazo,
        )

    def id_aluno(self):
        conexao = sqlite3.connect(CAMINHO_DB)
        linha = conexao.execute("SELECT id FROM users WHERE email = ?", (ALUNO,)).fetchone()
        conexao.close()
        return linha[0]


class TestesAtividadeProfessor(BaseAtividades):

    def test_cria_objetiva_com_questoes(self):
        resultado = self.criar_objetiva()
        self.assertTrue(resultado["sucesso"])

        atividade_id = resultado["atividade_ids"][0]
        detalhe = obter_atividade(atividade_id, PROFESSOR)
        self.assertEqual(len(detalhe["questoes"]), 2)
        self.assertEqual(detalhe["questoes"][0]["correta"], 1)

    def test_objetiva_sem_questao_e_recusada(self):
        resultado = criar_atividade_em_turmas(
            PROFESSOR, [self.turma_id], titulo="Vazia", tipo="objetiva", questoes=[]
        )
        self.assertFalse(resultado["sucesso"])

    def test_questao_sem_gabarito_e_recusada(self):
        resultado = criar_atividade_em_turmas(
            PROFESSOR, [self.turma_id], titulo="Torta", tipo="objetiva",
            questoes=[{"enunciado": "E?", "alternativas": ["a", "b"], "correta": None}],
        )
        self.assertFalse(resultado["sucesso"])

    def test_tipo_invalido_e_recusado(self):
        resultado = criar_atividade_em_turmas(
            PROFESSOR, [self.turma_id], titulo="X", tipo="adivinhacao"
        )
        self.assertFalse(resultado["sucesso"])

    def test_professor_nao_cria_em_turma_alheia(self):
        """E, como nos materiais, publicacao parcial nao pode acontecer."""
        outra = criar_turma(ADMIN, PROFESSOR2, "Clinica", "2026.2")["turma"]["id"]

        resultado = criar_atividade_em_turmas(
            PROFESSOR, [self.turma_id, outra], titulo="Invasao", tipo="dissertativa"
        )

        self.assertFalse(resultado["sucesso"])
        conexao = sqlite3.connect(CAMINHO_DB)
        total = conexao.execute("SELECT COUNT(*) FROM atividades").fetchone()[0]
        conexao.close()
        self.assertEqual(total, 0, "criou atividade mesmo com turma invalida")

    def test_status_reflete_rascunho_e_agendamento(self):
        self.criar_objetiva(titulo="Publicada")
        self.criar_objetiva(titulo="Rascunho", rascunho=True)
        futuro = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        self.criar_objetiva(titulo="Agendada", data_liberacao=futuro)

        por_titulo = {
            a["titulo"]: a["status"]
            for a in listar_atividades(PROFESSOR)["atividades"]
        }

        self.assertEqual(por_titulo["Publicada"], "publicado")
        self.assertEqual(por_titulo["Rascunho"], "rascunho")
        self.assertEqual(por_titulo["Agendada"], "agendado")

    def test_excluir_leva_questoes_e_entregas_junto(self):
        atividade_id = self.criar_objetiva()["atividade_ids"][0]
        enviar_entrega(ALUNO, atividade_id, [1, 1])

        excluir_atividade(atividade_id, PROFESSOR)

        conexao = sqlite3.connect(CAMINHO_DB)
        questoes = conexao.execute(
            "SELECT COUNT(*) FROM questoes WHERE atividade_id = ?", (atividade_id,)
        ).fetchone()[0]
        entregas = conexao.execute(
            "SELECT COUNT(*) FROM entregas WHERE atividade_id = ?", (atividade_id,)
        ).fetchone()[0]
        conexao.close()

        self.assertEqual(questoes, 0, "sobraram questoes orfas")
        self.assertEqual(entregas, 0, "sobraram entregas orfas")

    def test_outro_professor_nao_exclui(self):
        atividade_id = self.criar_objetiva()["atividade_ids"][0]
        self.assertFalse(excluir_atividade(atividade_id, PROFESSOR2)["sucesso"])

    def test_listagem_mostra_entregues_e_pendentes(self):
        atividade_id = self.criar_dissertativa()["atividade_ids"][0]
        enviar_entrega(ALUNO, atividade_id, "meu resumo")

        atividade = listar_atividades(PROFESSOR)["atividades"][0]
        self.assertEqual(atividade["entregues"], 1)
        self.assertEqual(atividade["a_corrigir"], 1)
        self.assertEqual(atividade["pendentes"], 0)


class TestesCorrecao(BaseAtividades):

    def _entrega_id(self, atividade_id):
        return listar_entregas(atividade_id, PROFESSOR)["entregas"][0]["entrega_id"]

    def test_professor_corrige_e_o_aluno_ve_a_nota(self):
        atividade_id = self.criar_dissertativa()["atividade_ids"][0]
        enviar_entrega(ALUNO, atividade_id, "resposta do aluno")

        entrega_id = self._entrega_id(atividade_id)
        self.assertTrue(corrigir_entrega(entrega_id, PROFESSOR, 8, "Bom, mas faltou citar o protocolo.")["sucesso"])

        atividade = listar_atividades_do_aluno(ALUNO)["atividades"][0]
        self.assertEqual(atividade["nota"], 8)
        self.assertEqual(atividade["situacao"], "corrigida")
        self.assertIn("protocolo", atividade["devolutiva"])

    def test_nota_acima_do_maximo_e_recusada(self):
        atividade_id = self.criar_dissertativa(pontos=10)["atividade_ids"][0]
        enviar_entrega(ALUNO, atividade_id, "resposta")
        entrega_id = self._entrega_id(atividade_id)

        self.assertFalse(corrigir_entrega(entrega_id, PROFESSOR, 50)["sucesso"])

    def test_outro_professor_nao_corrige(self):
        """Sem o JOIN com atividades, bastaria conhecer o id da entrega."""
        atividade_id = self.criar_dissertativa()["atividade_ids"][0]
        enviar_entrega(ALUNO, atividade_id, "resposta")
        entrega_id = self._entrega_id(atividade_id)

        self.assertFalse(corrigir_entrega(entrega_id, PROFESSOR2, 10)["sucesso"])

    def test_correcao_avisa_o_aluno(self):
        atividade_id = self.criar_dissertativa()["atividade_ids"][0]
        enviar_entrega(ALUNO, atividade_id, "resposta")
        corrigir_entrega(self._entrega_id(atividade_id), PROFESSOR, 9)

        tipos = [n["tipo"] for n in listar_notificacoes(ALUNO)["notificacoes"]]
        self.assertIn("correcao", tipos)


# =========================================================================
# Atividades — aluno
# =========================================================================

class TestesAtividadeAluno(BaseAtividades):

    def test_aluno_nao_ve_rascunho_nem_agendada(self):
        self.criar_objetiva(titulo="Liberada")
        self.criar_objetiva(titulo="Rascunho", rascunho=True)
        futuro = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
        self.criar_objetiva(titulo="Agendada", data_liberacao=futuro)

        titulos = [a["titulo"] for a in listar_atividades_do_aluno(ALUNO)["atividades"]]

        self.assertIn("Liberada", titulos)
        self.assertNotIn("Rascunho", titulos)
        self.assertNotIn("Agendada", titulos)

    def test_aluno_de_fora_da_turma_nao_ve(self):
        self.criar_objetiva()
        self.assertEqual(listar_atividades_do_aluno(ALUNO_FORA)["atividades"], [])

    def test_gabarito_nao_vai_para_o_aluno(self):
        """Esconder na interface nao adianta: estaria no DevTools."""
        atividade_id = self.criar_objetiva()["atividade_ids"][0]

        visao = obter_atividade_do_aluno(ALUNO, atividade_id)

        for questao in visao["questoes"]:
            self.assertNotIn("correta", questao)

    def test_aluno_de_fora_nao_abre_a_atividade(self):
        atividade_id = self.criar_objetiva()["atividade_ids"][0]
        self.assertFalse(obter_atividade_do_aluno(ALUNO_FORA, atividade_id)["sucesso"])

    def test_progresso_salvo_e_retomado(self):
        atividade_id = self.criar_objetiva()["atividade_ids"][0]

        salvar_progresso(ALUNO, atividade_id, [1, None])
        visao = obter_atividade_do_aluno(ALUNO, atividade_id)

        self.assertEqual(visao["entrega"]["respostas"], [1, None])
        self.assertIsNone(visao["entrega"]["enviado_em"], "progresso salvo virou entrega")
        self.assertEqual(
            listar_atividades_do_aluno(ALUNO)["atividades"][0]["situacao"],
            "em andamento",
        )

    def test_objetiva_e_corrigida_na_hora(self):
        atividade_id = self.criar_objetiva(pontos=10)["atividade_ids"][0]

        resultado = enviar_entrega(ALUNO, atividade_id, [1, 1])

        self.assertTrue(resultado["sucesso"])
        self.assertEqual(resultado["acertos"], 2)
        self.assertEqual(resultado["nota"], 10)

    def test_objetiva_com_metade_certa_da_metade_da_nota(self):
        atividade_id = self.criar_objetiva(pontos=10)["atividade_ids"][0]

        resultado = enviar_entrega(ALUNO, atividade_id, [1, 0])

        self.assertEqual(resultado["acertos"], 1)
        self.assertEqual(resultado["nota"], 5.0)

    def test_nao_entrega_duas_vezes(self):
        atividade_id = self.criar_objetiva()["atividade_ids"][0]
        enviar_entrega(ALUNO, atividade_id, [1, 1])

        segunda = enviar_entrega(ALUNO, atividade_id, [0, 0])
        self.assertFalse(segunda["sucesso"])

    def test_nao_salva_progresso_depois_de_entregar(self):
        atividade_id = self.criar_objetiva()["atividade_ids"][0]
        enviar_entrega(ALUNO, atividade_id, [1, 1])

        self.assertFalse(salvar_progresso(ALUNO, atividade_id, [0, 0])["sucesso"])

    def test_dissertativa_vazia_e_recusada(self):
        atividade_id = self.criar_dissertativa()["atividade_ids"][0]
        self.assertFalse(enviar_entrega(ALUNO, atividade_id, "   ")["sucesso"])

    def test_entrega_atrasada_e_aceita_e_marcada(self):
        """Recusar jogaria fora o trabalho; marcar deixa o professor decidir."""
        passado = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        atividade_id = self.criar_dissertativa(prazo=passado)["atividade_ids"][0]

        resultado = enviar_entrega(ALUNO, atividade_id, "entreguei atrasado")

        self.assertTrue(resultado["sucesso"])
        self.assertTrue(resultado["atrasada"])
        self.assertTrue(listar_atividades_do_aluno(ALUNO)["atividades"][0]["atrasada"])


# =========================================================================
# XP: o que pontua e o que nao pontua
# =========================================================================

class TestesXPNaoFarmavel(BaseAtividades):
    """O XP de pergunta era farmavel: qualquer texto no chat dava 10 pontos."""

    def _perguntar(self, texto, com_fonte=True, dia=None):
        """Simula uma ida ao chat, sem precisar do modelo ligado."""
        quando = dia or datetime.now(timezone.utc).isoformat()
        aluno_id = self.id_aluno()

        conexao = sqlite3.connect(CAMINHO_DB)
        conexao.execute(
            "INSERT INTO chat_mensagens (aluno_id, turma_id, papel, conteudo, fontes, criado_em)"
            " VALUES (?, ?, 'user', ?, NULL, ?)",
            (aluno_id, self.turma_id, texto, quando),
        )
        conexao.execute(
            "INSERT INTO chat_mensagens (aluno_id, turma_id, papel, conteudo, fontes, criado_em)"
            " VALUES (?, ?, 'assistant', ?, ?, ?)",
            (
                aluno_id,
                self.turma_id,
                "resposta",
                json.dumps(["Aula 3"]) if com_fonte else None,
                quando,
            ),
        )
        conexao.commit()
        conexao.close()

    def test_pergunta_respondida_pelo_material_pontua(self):
        self._perguntar("Qual a dose inicial do Cardiolex?")
        progresso = resumo_do_aluno(ALUNO)["progresso"]
        self.assertEqual(progresso["perguntas"], 1)

    def test_pergunta_recusada_nao_pontua(self):
        """Sem fonte, o assistente disse que o material nao cobre. Nao e estudo."""
        self._perguntar("Qual o escore XYZ-99?", com_fonte=False)
        self.assertEqual(resumo_do_aluno(ALUNO)["progresso"]["perguntas"], 0)

    def test_lixo_repetido_nao_vira_xp(self):
        """Era este o buraco: 'aaa' cinquenta vezes valia 500 XP."""
        for _ in range(50):
            self._perguntar("aaa", com_fonte=False)

        progresso = resumo_do_aluno(ALUNO)["progresso"]
        self.assertEqual(progresso["perguntas"], 0)

    def test_mesma_pergunta_repetida_conta_uma_vez(self):
        for _ in range(10):
            self._perguntar("Qual a dose inicial?")

        self.assertEqual(resumo_do_aluno(ALUNO)["progresso"]["perguntas"], 1)

    def test_variacao_de_caixa_e_pontuacao_nao_burla(self):
        self._perguntar("Qual a dose inicial?")
        self._perguntar("QUAL A DOSE INICIAL")
        self._perguntar("qual   a dose inicial!!!")

        self.assertEqual(resumo_do_aluno(ALUNO)["progresso"]["perguntas"], 1)

    def test_teto_diario_de_perguntas(self):
        for numero in range(12):
            self._perguntar(f"Pergunta distinta numero {numero}")

        progresso = resumo_do_aluno(ALUNO)["progresso"]
        self.assertEqual(progresso["perguntas"], MAX_PERGUNTAS_QUE_PONTUAM_POR_DIA)

    def test_teto_e_por_dia_nao_total(self):
        ontem = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        for numero in range(8):
            self._perguntar(f"Hoje {numero}")
        for numero in range(8):
            self._perguntar(f"Ontem {numero}", dia=ontem)

        progresso = resumo_do_aluno(ALUNO)["progresso"]
        self.assertEqual(progresso["perguntas"], MAX_PERGUNTAS_QUE_PONTUAM_POR_DIA * 2)

    def test_entrega_e_nota_viram_xp(self):
        atividade_id = self.criar_objetiva(pontos=10)["atividade_ids"][0]
        enviar_entrega(ALUNO, atividade_id, [1, 1])

        progresso = resumo_do_aluno(ALUNO)["progresso"]

        self.assertEqual(progresso["atividades_entregues"], 1)
        self.assertEqual(progresso["atividades_corrigidas"], 1)
        # 20 pela entrega + 30 pela nota cheia + 25 pelo dia de estudo
        self.assertEqual(progresso["xp"], 75)

    def test_nota_baixa_vale_menos_xp_que_nota_alta(self):
        certa = self.criar_objetiva(titulo="Certa", pontos=10)["atividade_ids"][0]
        enviar_entrega(ALUNO, certa, [1, 1])
        xp_com_nota_cheia = resumo_do_aluno(ALUNO)["progresso"]["xp"]

        errada = self.criar_objetiva(titulo="Errada", pontos=10)["atividade_ids"][0]
        enviar_entrega(ALUNO, errada, [0, 0])
        xp_total = resumo_do_aluno(ALUNO)["progresso"]["xp"]

        ganho_da_errada = xp_total - xp_com_nota_cheia
        # So os 20 da entrega: zero acerto nao rende XP de desempenho.
        self.assertEqual(ganho_da_errada, XP_POR_ATIVIDADE_ENTREGUE)

    def test_composicao_continua_batendo_com_o_total(self):
        atividade_id = self.criar_objetiva()["atividade_ids"][0]
        enviar_entrega(ALUNO, atividade_id, [1, 0])
        self._perguntar("Uma duvida real")

        progresso = resumo_do_aluno(ALUNO)["progresso"]
        soma = sum(item["xp"] for item in progresso["composicao"])
        self.assertEqual(soma, progresso["xp"])


# =========================================================================
# Desempenho
# =========================================================================

class TestesDesempenho(BaseAtividades):
    """O numero que interessa aqui e o erro por topico.

    Media de turma diz que foi mal; erro por topico diz **onde** foi mal, que e
    o que muda a aula seguinte. Se essa conta estiver errada, o professor
    retrabalha o assunto errado e ninguem percebe.
    """

    def criar_quiz(self, titulo, topico, gabarito, pontos=10):
        """Cria uma objetiva com uma questao por item do gabarito."""
        questoes = [
            {
                "enunciado": "Questao %d de %s" % (i + 1, titulo),
                "alternativas": ["A", "B", "C"],
                "correta": correta,
            }
            for i, correta in enumerate(gabarito)
        ]
        return criar_atividade_em_turmas(
            PROFESSOR, [self.turma_id], titulo=titulo, tipo="objetiva",
            topico=topico, pontos=pontos, rascunho=False, questoes=questoes,
        )["atividade_ids"][0]

    # ------------------------------------------------------------- aluno

    def test_aluno_sem_entrega_nao_inventa_numero(self):
        resultado = desempenho_do_aluno(ALUNO)
        self.assertTrue(resultado["sucesso"])
        self.assertEqual(resultado["notas"], [])
        self.assertEqual(resultado["topicos"], [])
        self.assertIsNone(resultado["resumo"]["aproveitamento"])

    def test_aproveitamento_e_ponderado_pelos_pontos(self):
        """Uma atividade que vale 30 pesa mais que uma que vale 10."""
        pequena = self.criar_quiz("Pequena", "Arritmias", [0, 0], pontos=10)
        grande = self.criar_quiz("Grande", "Arritmias", [0, 0], pontos=30)

        enviar_entrega(ALUNO, pequena, [0, 0])   # 10 de 10
        enviar_entrega(ALUNO, grande, [0, 1])    # 15 de 30

        resumo = desempenho_do_aluno(ALUNO)["resumo"]

        self.assertEqual(resumo["pontos_obtidos"], 25.0)
        self.assertEqual(resumo["pontos_possiveis"], 40.0)
        # Media simples daria 75%; ponderada da 62.5%.
        self.assertEqual(resumo["aproveitamento"], 62.5)

    def test_topico_com_mais_erro_vem_primeiro(self):
        # Os nomes sao escolhidos para a ordem alfabetica ser o CONTRARIO da
        # ordem por erro. Com "Arritmias" dificil e "Valvopatias" facil, um
        # sort por nome passaria no teste sem ordenar por erro nenhum.
        facil = self.criar_quiz("Facil", "Arritmias", [0, 0])
        dificil = self.criar_quiz("Dificil", "Valvopatias", [0, 0])

        enviar_entrega(ALUNO, facil, [0, 0])      # 2 acertos
        enviar_entrega(ALUNO, dificil, [1, 1])    # 2 erros

        topicos = desempenho_do_aluno(ALUNO)["topicos"]

        self.assertEqual(topicos[0]["topico"], "Valvopatias")
        self.assertEqual(topicos[0]["percentual_erro"], 100.0)
        self.assertEqual(topicos[1]["topico"], "Arritmias")
        self.assertEqual(topicos[1]["percentual_erro"], 0.0)

    def test_questao_em_branco_conta_como_erro(self):
        """Para saber o que revisar, nao respondida e errada dizem o mesmo."""
        quiz = self.criar_quiz("Quiz", "Valvopatias", [0, 0])
        enviar_entrega(ALUNO, quiz, [0])  # respondeu so a primeira

        topicos = desempenho_do_aluno(ALUNO)["topicos"]
        self.assertEqual(topicos[0]["acertos"], 1)
        self.assertEqual(topicos[0]["erros"], 1)

    def test_dissertativa_nao_entra_na_conta_de_topico(self):
        """Sem gabarito nao da para dizer em que questao ele errou."""
        quiz = self.criar_quiz("Quiz", "Arritmias", [0])
        enviar_entrega(ALUNO, quiz, [0])

        dissertativa = self.criar_dissertativa("Resumo")["atividade_ids"][0]
        enviar_entrega(ALUNO, dissertativa, "meu texto")

        resultado = desempenho_do_aluno(ALUNO)

        self.assertEqual(len(resultado["notas"]), 2, "a dissertativa sumiu das notas")
        self.assertEqual(len(resultado["topicos"]), 1, "dissertativa entrou nos topicos")

    def test_aluno_nao_ve_desempenho_de_outro(self):
        quiz = self.criar_quiz("Quiz", "Arritmias", [0])
        enviar_entrega(ALUNO, quiz, [0])

        # O outro aluno nem esta na turma; o dele tem que vir vazio.
        self.assertEqual(desempenho_do_aluno(ALUNO_FORA)["notas"], [])

    def test_atividade_aguardando_correcao_aparece_sem_nota(self):
        dissertativa = self.criar_dissertativa("Resumo")["atividade_ids"][0]
        enviar_entrega(ALUNO, dissertativa, "texto")

        resumo = desempenho_do_aluno(ALUNO)["resumo"]
        self.assertEqual(resumo["entregues"], 1)
        self.assertEqual(resumo["corrigidas"], 0)
        self.assertEqual(resumo["aguardando"], 1)

    # ------------------------------------------------------------- professor

    def test_professor_so_ve_a_propria_turma(self):
        outra = criar_turma(ADMIN, PROFESSOR2, "Clinica", "2026.2")["turma"]["id"]
        self.assertFalse(desempenho_da_turma(PROFESSOR, outra)["sucesso"])

    def test_turma_sem_atividade_devolve_vazio(self):
        resultado = desempenho_da_turma(PROFESSOR, self.turma_id)

        self.assertTrue(resultado["sucesso"])
        self.assertEqual(resultado["atividades"], [])
        self.assertIsNone(resultado["resumo"]["media_percentual"])

    def test_media_e_taxa_de_entrega_da_turma(self):
        criar_conta_staff(ADMIN, "aluno3@teste.com", SENHA, "aluno", nome="Aluno Tres")
        matricular_aluno(ADMIN, "aluno3@teste.com", self.turma_id)

        quiz = self.criar_quiz("Quiz", "Arritmias", [0, 0])
        enviar_entrega(ALUNO, quiz, [0, 0])              # 100%
        enviar_entrega("aluno3@teste.com", quiz, [0, 1])  # 50%

        resultado = desempenho_da_turma(PROFESSOR, self.turma_id)

        self.assertEqual(resultado["resumo"]["total_alunos"], 2)
        self.assertEqual(resultado["resumo"]["media_percentual"], 75.0)
        self.assertEqual(resultado["resumo"]["taxa_entrega"], 100.0)
        self.assertEqual(resultado["atividades"][0]["menor"], 5.0)
        self.assertEqual(resultado["atividades"][0]["maior"], 10.0)

    def test_pendencia_aparece_quando_aluno_nao_entrega(self):
        criar_conta_staff(ADMIN, "aluno3@teste.com", SENHA, "aluno", nome="Aluno Tres")
        matricular_aluno(ADMIN, "aluno3@teste.com", self.turma_id)

        quiz = self.criar_quiz("Quiz", "Arritmias", [0])
        enviar_entrega(ALUNO, quiz, [0])

        atividade = desempenho_da_turma(PROFESSOR, self.turma_id)["atividades"][0]
        self.assertEqual(atividade["entregues"], 1)
        self.assertEqual(atividade["pendentes"], 1)

    def test_topico_da_turma_soma_os_erros_de_todos(self):
        criar_conta_staff(ADMIN, "aluno3@teste.com", SENHA, "aluno", nome="Aluno Tres")
        matricular_aluno(ADMIN, "aluno3@teste.com", self.turma_id)

        quiz = self.criar_quiz("Quiz", "Arritmias", [0, 0])
        enviar_entrega(ALUNO, quiz, [1, 1])               # 2 erros
        enviar_entrega("aluno3@teste.com", quiz, [0, 1])   # 1 acerto, 1 erro

        topicos = desempenho_da_turma(PROFESSOR, self.turma_id)["topicos"]

        self.assertEqual(topicos[0]["topico"], "Arritmias")
        self.assertEqual(topicos[0]["erros"], 3)
        self.assertEqual(topicos[0]["acertos"], 1)
        self.assertEqual(topicos[0]["percentual_erro"], 75.0)

    def test_rascunho_e_agendada_ficam_fora_da_conta(self):
        self.criar_quiz("Publicada", "Arritmias", [0])

        criar_atividade_em_turmas(
            PROFESSOR, [self.turma_id], titulo="Rascunho", tipo="objetiva",
            topico="Arritmias", rascunho=True,
            questoes=[{"enunciado": "E?", "alternativas": ["A", "B"], "correta": 0}],
        )
        futuro = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
        criar_atividade_em_turmas(
            PROFESSOR, [self.turma_id], titulo="Agendada", tipo="objetiva",
            topico="Arritmias", rascunho=False, data_liberacao=futuro,
            questoes=[{"enunciado": "E?", "alternativas": ["A", "B"], "correta": 0}],
        )

        atividades = desempenho_da_turma(PROFESSOR, self.turma_id)["atividades"]
        titulos = [a["titulo"] for a in atividades]

        self.assertEqual(titulos, ["Publicada"])

    def test_lista_de_alunos_traz_quem_nao_entregou(self):
        criar_conta_staff(ADMIN, "aluno3@teste.com", SENHA, "aluno", nome="Aluno Tres")
        matricular_aluno(ADMIN, "aluno3@teste.com", self.turma_id)

        quiz = self.criar_quiz("Quiz", "Arritmias", [0])
        enviar_entrega(ALUNO, quiz, [0])

        alunos = {a["aluno_email"]: a for a in desempenho_da_turma(PROFESSOR, self.turma_id)["alunos"]}

        self.assertEqual(alunos[ALUNO]["entregues"], 1)
        self.assertEqual(alunos[ALUNO]["aproveitamento"], 100.0)
        self.assertEqual(alunos["aluno3@teste.com"]["entregues"], 0)
        self.assertIsNone(alunos["aluno3@teste.com"]["aproveitamento"])


# =========================================================================
# Denuncias
# =========================================================================

class TestesDenuncias(BaseDelta):
    """Os dois lados: quem reporta e quem trata.

    O risco aqui nao e calculo, e visibilidade: denuncia de um usuario nao pode
    aparecer para outro, e ninguem pode reportar material que nao enxerga --
    senao da para descobrir o titulo de material de outra turma chutando id.
    """

    def setUp(self):
        super().setUp()
        self.material_id = self.criar_material_simples("Aula publicada")["material_id"]

    def test_aluno_reporta_material_da_turma_dele(self):
        resultado = criar_denuncia(ALUNO, self.material_id, "incorreto", "A dose esta errada.")
        self.assertTrue(resultado["sucesso"], resultado.get("mensagem"))

        minhas = listar_minhas(ALUNO)["denuncias"]
        self.assertEqual(len(minhas), 1)
        self.assertEqual(minhas[0]["status"], "aberta")
        self.assertEqual(minhas[0]["material_titulo"], "Aula publicada")

    def test_professor_tambem_pode_reportar(self):
        self.assertTrue(criar_denuncia(PROFESSOR, self.material_id, "problema_tecnico")["sucesso"])

    def test_aluno_fora_da_turma_nao_reporta(self):
        """Sem isso, chutar ids revelaria o titulo de material de outra turma."""
        resultado = criar_denuncia(ALUNO_FORA, self.material_id, "incorreto")
        self.assertFalse(resultado["sucesso"])

    def test_nao_reporta_material_nao_publicado(self):
        rascunho = self.criar_material_simples("Rascunho", rascunho=True)["material_id"]
        self.assertFalse(criar_denuncia(ALUNO, rascunho, "incorreto")["sucesso"])

    def test_administracao_nao_reporta(self):
        """Quem trata a fila nao alimenta a fila."""
        resultado = criar_denuncia(ADMIN, self.material_id, "incorreto")
        self.assertFalse(resultado["sucesso"])

    def test_motivo_invalido_e_recusado(self):
        self.assertFalse(criar_denuncia(ALUNO, self.material_id, "nao_gostei")["sucesso"])

    def test_motivo_outro_exige_descricao(self):
        self.assertFalse(criar_denuncia(ALUNO, self.material_id, "outro")["sucesso"])
        self.assertTrue(criar_denuncia(ALUNO, self.material_id, "outro", "Explico aqui.")["sucesso"])

    def test_nao_duplica_denuncia_em_aberto(self):
        criar_denuncia(ALUNO, self.material_id, "incorreto")
        segunda = criar_denuncia(ALUNO, self.material_id, "ofensivo")

        self.assertFalse(segunda["sucesso"])
        self.assertEqual(len(listar_minhas(ALUNO)["denuncias"]), 1)

    def test_pode_reportar_de_novo_depois_de_concluida(self):
        criar_denuncia(ALUNO, self.material_id, "incorreto")
        denuncia = listar_todas(ADMIN)["denuncias"][0]
        tratar_denuncia(ADMIN, denuncia["id"], "concluida", "Material corrigido pelo professor.")

        self.assertTrue(criar_denuncia(ALUNO, self.material_id, "incorreto")["sucesso"])

    def test_cada_um_so_ve_as_proprias(self):
        criar_denuncia(ALUNO, self.material_id, "incorreto")
        criar_denuncia(PROFESSOR, self.material_id, "problema_tecnico")

        self.assertEqual(len(listar_minhas(ALUNO)["denuncias"]), 1)
        self.assertEqual(listar_minhas(ALUNO)["denuncias"][0]["motivo"], "incorreto")
        self.assertEqual(len(listar_minhas(PROFESSOR)["denuncias"]), 1)
        self.assertEqual(listar_minhas(PROFESSOR)["denuncias"][0]["motivo"], "problema_tecnico")

    # ------------------------------------------------------------- admin

    def test_so_admin_ve_a_fila(self):
        criar_denuncia(ALUNO, self.material_id, "incorreto")

        self.assertFalse(listar_todas(ALUNO)["sucesso"])
        self.assertFalse(listar_todas(PROFESSOR)["sucesso"])
        self.assertTrue(listar_todas(ADMIN)["sucesso"])

    def test_so_admin_trata(self):
        criar_denuncia(ALUNO, self.material_id, "incorreto")
        denuncia = listar_todas(ADMIN)["denuncias"][0]

        self.assertFalse(tratar_denuncia(PROFESSOR, denuncia["id"], "concluida", "resolvido")["sucesso"])
        self.assertFalse(tratar_denuncia(ALUNO, denuncia["id"], "concluida", "resolvido")["sucesso"])

    def test_encerrar_sem_dizer_a_acao_e_recusado(self):
        """Concluir sem acao devolve 'concluida' e nenhuma informacao."""
        criar_denuncia(ALUNO, self.material_id, "incorreto")
        denuncia = listar_todas(ADMIN)["denuncias"][0]

        self.assertFalse(tratar_denuncia(ADMIN, denuncia["id"], "concluida")["sucesso"])
        self.assertTrue(tratar_denuncia(ADMIN, denuncia["id"], "em_analise")["sucesso"])

    def test_quem_reportou_e_avisado_do_desfecho(self):
        criar_denuncia(ALUNO, self.material_id, "incorreto")
        denuncia = listar_todas(ADMIN)["denuncias"][0]
        tratar_denuncia(ADMIN, denuncia["id"], "concluida", "Material substituido.")

        tipos = [n["tipo"] for n in listar_notificacoes(ALUNO)["notificacoes"]]
        self.assertIn("denuncia", tipos)

    def test_admin_e_avisado_da_denuncia_nova(self):
        criar_denuncia(ALUNO, self.material_id, "ofensivo")

        avisos = [n for n in listar_notificacoes(ADMIN)["notificacoes"] if n["tipo"] == "denuncia"]
        self.assertEqual(len(avisos), 1)

    def test_fila_traz_as_abertas_primeiro(self):
        criar_denuncia(ALUNO, self.material_id, "incorreto")
        primeira = listar_todas(ADMIN)["denuncias"][0]
        tratar_denuncia(ADMIN, primeira["id"], "concluida", "Resolvido.")

        outro = self.criar_material_simples("Outra aula")["material_id"]
        criar_denuncia(ALUNO, outro, "ofensivo")

        fila = listar_todas(ADMIN)["denuncias"]
        self.assertEqual(fila[0]["status"], "aberta", "a concluida veio antes da aberta")

    def test_resumo_conta_por_status(self):
        criar_denuncia(ALUNO, self.material_id, "incorreto")
        criar_denuncia(PROFESSOR, self.material_id, "ofensivo")
        denuncia = listar_todas(ADMIN)["denuncias"][0]
        tratar_denuncia(ADMIN, denuncia["id"], "concluida", "Resolvido.")

        resumo = listar_todas(ADMIN)["resumo"]
        self.assertEqual(resumo["abertas"], 1)
        self.assertEqual(resumo["concluidas"], 1)

    def test_denuncia_sobrevive_a_exclusao_do_material(self):
        """O historico e o que justifica a exclusao; some-lo seria apagar a prova."""
        criar_denuncia(ALUNO, self.material_id, "ofensivo", "Conteudo impróprio.")
        excluir_material(self.material_id, PROFESSOR)

        fila = listar_todas(ADMIN)["denuncias"]
        self.assertEqual(len(fila), 1)
        self.assertEqual(fila[0]["material_titulo"], "Aula publicada")


class TestesRetiradaDeDenuncia(BaseDelta):
    """Quem reportou volta atras.

    Tres casos diferentes de proposito, conforme o trabalho ja gasto: aberta
    some, em analise vira 'retirada' com aviso, encerrada nao se mexe.
    """

    def setUp(self):
        super().setUp()
        self.material_id = self.criar_material_simples("Aula publicada")["material_id"]

    def _denuncia_do_aluno(self):
        criar_denuncia(ALUNO, self.material_id, "incorreto", "Reportei sem querer.")
        return listar_minhas(ALUNO)["denuncias"][0]

    def test_aberta_e_apagada_de_vez(self):
        """Ninguem leu ainda; deixar a acusacao registrada seria injusto."""
        denuncia = self._denuncia_do_aluno()

        resultado = remover_denuncia(ALUNO, denuncia["id"])

        self.assertTrue(resultado["sucesso"])
        self.assertTrue(resultado["apagada"])
        self.assertEqual(listar_minhas(ALUNO)["denuncias"], [])
        self.assertEqual(listar_todas(ADMIN)["denuncias"], [])

    def test_em_analise_vira_retirada_e_fica_no_historico(self):
        """A administracao ja trabalhou nela; apagar esconderia o porque da parada."""
        denuncia = self._denuncia_do_aluno()
        tratar_denuncia(ADMIN, denuncia["id"], "em_analise")

        resultado = remover_denuncia(ALUNO, denuncia["id"])

        self.assertTrue(resultado["sucesso"])
        self.assertFalse(resultado["apagada"])

        fila = listar_todas(ADMIN)["denuncias"]
        self.assertEqual(len(fila), 1)
        self.assertEqual(fila[0]["status"], "retirada")

    def test_administracao_e_avisada_da_retirada_em_analise(self):
        denuncia = self._denuncia_do_aluno()
        tratar_denuncia(ADMIN, denuncia["id"], "em_analise")
        remover_denuncia(ALUNO, denuncia["id"])

        avisos = [n["titulo"] for n in listar_notificacoes(ADMIN)["notificacoes"]]
        self.assertIn("Denúncia retirada", avisos)

    def test_concluida_nao_pode_ser_retirada(self):
        denuncia = self._denuncia_do_aluno()
        tratar_denuncia(ADMIN, denuncia["id"], "concluida", "Material corrigido.")

        resultado = remover_denuncia(ALUNO, denuncia["id"])

        self.assertFalse(resultado["sucesso"])
        self.assertEqual(len(listar_todas(ADMIN)["denuncias"]), 1)

    def test_arquivada_nao_pode_ser_retirada(self):
        denuncia = self._denuncia_do_aluno()
        tratar_denuncia(ADMIN, denuncia["id"], "arquivada", "Sem procedencia.")

        self.assertFalse(remover_denuncia(ALUNO, denuncia["id"])["sucesso"])

    def test_nao_retira_a_denuncia_de_outra_pessoa(self):
        """Sem o filtro por autor, bastaria conhecer o id da denuncia alheia."""
        denuncia = self._denuncia_do_aluno()

        self.assertFalse(remover_denuncia(PROFESSOR, denuncia["id"])["sucesso"])
        self.assertFalse(remover_denuncia(ALUNO_FORA, denuncia["id"])["sucesso"])
        self.assertEqual(len(listar_minhas(ALUNO)["denuncias"]), 1)

    def test_admin_nao_retira_pelo_caminho_do_autor(self):
        """A administracao arquiva; retirar e do autor. Sao acoes diferentes."""
        denuncia = self._denuncia_do_aluno()
        self.assertFalse(remover_denuncia(ADMIN, denuncia["id"])["sucesso"])

    def test_nao_retira_duas_vezes(self):
        denuncia = self._denuncia_do_aluno()
        tratar_denuncia(ADMIN, denuncia["id"], "em_analise")
        remover_denuncia(ALUNO, denuncia["id"])

        self.assertFalse(remover_denuncia(ALUNO, denuncia["id"])["sucesso"])

    def test_depois_de_retirar_pode_reportar_de_novo(self):
        """Retirou por engano; tem de poder reportar de verdade depois."""
        denuncia = self._denuncia_do_aluno()
        remover_denuncia(ALUNO, denuncia["id"])

        self.assertTrue(criar_denuncia(ALUNO, self.material_id, "ofensivo")["sucesso"])

    def test_retirada_em_analise_nao_bloqueia_nova_denuncia(self):
        denuncia = self._denuncia_do_aluno()
        tratar_denuncia(ADMIN, denuncia["id"], "em_analise")
        remover_denuncia(ALUNO, denuncia["id"])

        self.assertTrue(criar_denuncia(ALUNO, self.material_id, "ofensivo")["sucesso"])

    def test_retirada_nao_conta_como_aberta_no_resumo(self):
        denuncia = self._denuncia_do_aluno()
        tratar_denuncia(ADMIN, denuncia["id"], "em_analise")
        remover_denuncia(ALUNO, denuncia["id"])

        resumo = listar_todas(ADMIN)["resumo"]
        self.assertEqual(resumo["abertas"], 0)
        self.assertEqual(resumo["em_analise"], 0)
        # E aparece no proprio contador: denuncia que esta na lista e nao e
        # contada em lugar nenhum faz o admin desconfiar do painel.
        self.assertEqual(resumo["retiradas"], 1)


class TestesCalendario(BaseAtividades):
    """O calendario junta o que ja existe espalhado. O risco e de omissao:
    evento que nao aparece no mes certo, ou que aparece sem dever."""

    def _mes_de_hoje(self):
        hoje = datetime.now(timezone.utc)
        return hoje.year, hoje.month

    def _dias(self, resultado):
        return {e["dia"] for e in resultado["eventos"]}

    def test_mes_vazio_nao_inventa_evento(self):
        ano, mes = self._mes_de_hoje()
        resultado = eventos_do_mes(PROFESSOR, ano, mes)

        self.assertTrue(resultado["sucesso"])
        self.assertEqual(resultado["eventos"], [])

    def test_material_publicado_entra_no_dia(self):
        self.criar_material_simples("Aula de hoje")
        ano, mes = self._mes_de_hoje()

        eventos = eventos_do_mes(PROFESSOR, ano, mes)["eventos"]

        self.assertEqual(len(eventos), 1)
        self.assertEqual(eventos[0]["tipo"], "material")
        self.assertEqual(eventos[0]["titulo"], "Aula de hoje")

    def test_rascunho_nao_aparece(self):
        """Rascunho nao tem data no calendario: nao acontece nada nele."""
        self.criar_material_simples("Rascunho", rascunho=True)
        ano, mes = self._mes_de_hoje()

        self.assertEqual(eventos_do_mes(PROFESSOR, ano, mes)["eventos"], [])

    def test_material_agendado_cai_no_dia_da_liberacao(self):
        """O material pertence ao dia em que o aluno vai ve-lo."""
        futuro = datetime.now(timezone.utc) + timedelta(days=3)
        self.criar_material_simples("Agendado", data_liberacao=futuro.isoformat())

        eventos = eventos_do_mes(PROFESSOR, futuro.year, futuro.month)["eventos"]
        agendados = [e for e in eventos if e["titulo"] == "Agendado"]

        self.assertEqual(len(agendados), 1)
        self.assertEqual(agendados[0]["tipo"], "material_agendado")
        self.assertEqual(agendados[0]["dia"], futuro.date().isoformat())

    def test_atividade_com_prazo_gera_dois_eventos(self):
        """Liberacao e prazo sao coisas diferentes em dias diferentes."""
        prazo = datetime.now(timezone.utc) + timedelta(days=5)
        self.criar_objetiva(titulo="Quiz", prazo=prazo.isoformat())

        ano, mes = self._mes_de_hoje()
        eventos = eventos_do_mes(PROFESSOR, ano, mes)["eventos"]
        tipos = {e["tipo"] for e in eventos}

        # Se o prazo cair no mes seguinte, so a liberacao aparece aqui.
        self.assertIn("atividade", tipos)
        if prazo.month == mes:
            self.assertIn("prazo", tipos)

    def test_prazo_aparece_no_mes_do_prazo(self):
        prazo = datetime.now(timezone.utc) + timedelta(days=40)
        self.criar_objetiva(titulo="Com prazo longe", prazo=prazo.isoformat())

        eventos = eventos_do_mes(PROFESSOR, prazo.year, prazo.month)["eventos"]
        prazos = [e for e in eventos if e["tipo"] == "prazo"]

        self.assertEqual(len(prazos), 1)
        self.assertEqual(prazos[0]["dia"], prazo.date().isoformat())

    def test_evento_de_outro_mes_fica_de_fora(self):
        self.criar_material_simples("Deste mes")
        outro = datetime.now(timezone.utc) + timedelta(days=70)

        eventos = eventos_do_mes(PROFESSOR, outro.year, outro.month)["eventos"]
        self.assertEqual(eventos, [])

    def test_professor_nao_ve_turma_alheia(self):
        outra = criar_turma(ADMIN, PROFESSOR2, "Clinica", "2026.2")["turma"]["id"]
        criar_material(
            professor_email=PROFESSOR2, turma_id=outra, titulo="Da outra turma",
            tipo="link", link_url="https://exemplo.com", rascunho=False,
        )

        ano, mes = self._mes_de_hoje()
        titulos = [e["titulo"] for e in eventos_do_mes(PROFESSOR, ano, mes)["eventos"]]

        self.assertNotIn("Da outra turma", titulos)

    def test_filtro_por_turma_recusa_turma_alheia(self):
        outra = criar_turma(ADMIN, PROFESSOR2, "Clinica", "2026.2")["turma"]["id"]
        ano, mes = self._mes_de_hoje()

        self.assertFalse(eventos_do_mes(PROFESSOR, ano, mes, outra)["sucesso"])

    def test_mes_invalido_e_recusado(self):
        self.assertFalse(eventos_do_mes(PROFESSOR, 2026, 13)["sucesso"])
        self.assertFalse(eventos_do_mes(PROFESSOR, 2026, 0)["sucesso"])

    def test_avisa_quando_ha_dois_prazos_no_mesmo_dia(self):
        """E o aviso que o professor nao tem hoje: duas entregas no mesmo dia."""
        prazo = datetime.now(timezone.utc) + timedelta(days=6)
        self.criar_objetiva(titulo="Quiz A", prazo=prazo.isoformat())
        self.criar_objetiva(titulo="Quiz B", prazo=prazo.isoformat())

        resumo = eventos_do_mes(PROFESSOR, prazo.year, prazo.month)["resumo"]

        self.assertIn(prazo.date().isoformat(), resumo["dias_com_dois_prazos"])

    def test_um_prazo_no_dia_nao_gera_aviso(self):
        prazo = datetime.now(timezone.utc) + timedelta(days=6)
        self.criar_objetiva(titulo="Quiz unico", prazo=prazo.isoformat())

        resumo = eventos_do_mes(PROFESSOR, prazo.year, prazo.month)["resumo"]
        self.assertEqual(resumo["dias_com_dois_prazos"], [])

    def test_eventos_vem_ordenados_por_dia(self):
        self.criar_material_simples("Hoje")
        depois = datetime.now(timezone.utc) + timedelta(days=4)
        self.criar_material_simples("Depois", data_liberacao=depois.isoformat())

        ano, mes = self._mes_de_hoje()
        eventos = eventos_do_mes(PROFESSOR, ano, mes)["eventos"]
        dias = [e["dia"] for e in eventos]

        self.assertEqual(dias, sorted(dias), "calendario fora de ordem")


class TestesMensagens(BaseDelta):
    """Conversa entre professor e aluno.

    O risco nao e calculo, e vazamento: a conversa de duas pessoas nao pode
    aparecer para uma terceira, e trocar um parametro na URL nao pode virar
    leitura da conversa alheia.
    """

    def setUp(self):
        super().setUp()
        criar_conta_staff(ADMIN, "aluno3@teste.com", SENHA, "aluno", nome="Aluno Tres")
        matricular_aluno(ADMIN, "aluno3@teste.com", self.turma_id)

    def test_aluno_escreve_e_professor_le(self):
        self.assertTrue(enviar_mensagem(ALUNO, self.turma_id, "Professor, nao entendi a fase B.")["sucesso"])

        conversa = abrir_conversa(PROFESSOR, self.turma_id, ALUNO)

        self.assertTrue(conversa["sucesso"])
        self.assertEqual(len(conversa["mensagens"]), 1)
        self.assertFalse(conversa["mensagens"][0]["minha"])
        self.assertIn("fase B", conversa["mensagens"][0]["conteudo"])

    def test_professor_responde_e_aluno_le(self):
        enviar_mensagem(ALUNO, self.turma_id, "Duvida.")
        enviar_mensagem(PROFESSOR, self.turma_id, "A fase B vai de uma a tres horas.", ALUNO)

        conversa = abrir_conversa(ALUNO, self.turma_id)

        self.assertEqual(len(conversa["mensagens"]), 2)
        self.assertTrue(conversa["mensagens"][1]["minha"] is False)

    def test_mensagem_vazia_e_recusada(self):
        self.assertFalse(enviar_mensagem(ALUNO, self.turma_id, "   ")["sucesso"])

    def test_mensagem_gigante_e_recusada(self):
        self.assertFalse(enviar_mensagem(ALUNO, self.turma_id, "a" * 3000)["sucesso"])

    # ---------------------------------------------------------- vazamento

    def test_aluno_de_outra_turma_nao_escreve(self):
        self.assertFalse(enviar_mensagem(ALUNO_FORA, self.turma_id, "Oi")["sucesso"])

    def test_aluno_de_outra_turma_nao_le(self):
        enviar_mensagem(ALUNO, self.turma_id, "Particular.")
        self.assertFalse(abrir_conversa(ALUNO_FORA, self.turma_id)["sucesso"])

    def test_aluno_nao_le_a_conversa_de_outro_aluno(self):
        """Mesmo matriculado na mesma turma: a conversa e dele com o professor."""
        enviar_mensagem(ALUNO, self.turma_id, "Minha duvida particular.")

        # Tenta se passar por outro informando o e-mail alheio: o parametro e
        # ignorado para aluno, entao ele le a propria conversa, que esta vazia.
        conversa = abrir_conversa("aluno3@teste.com", self.turma_id, ALUNO)

        self.assertTrue(conversa["sucesso"])
        self.assertEqual(conversa["mensagens"], [], "leu a conversa de outro aluno")

    def test_professor_de_outra_turma_nao_le(self):
        enviar_mensagem(ALUNO, self.turma_id, "Particular.")
        self.assertFalse(abrir_conversa(PROFESSOR2, self.turma_id, ALUNO)["sucesso"])

    def test_professor_nao_escreve_para_aluno_nao_matriculado(self):
        self.assertFalse(enviar_mensagem(PROFESSOR, self.turma_id, "Oi", ALUNO_FORA)["sucesso"])

    def test_professor_precisa_dizer_com_quem_fala(self):
        self.assertFalse(enviar_mensagem(PROFESSOR, self.turma_id, "Oi")["sucesso"])

    def test_turma_inexistente(self):
        self.assertFalse(enviar_mensagem(ALUNO, 9999, "Oi")["sucesso"])

    # ---------------------------------------------------------- nao lidas

    def test_mensagem_nova_conta_como_nao_lida(self):
        enviar_mensagem(ALUNO, self.turma_id, "Oi professor.")

        conversas = listar_conversas(PROFESSOR)
        do_aluno = [c for c in conversas["conversas"] if c["contraparte_email"] == ALUNO][0]

        self.assertEqual(do_aluno["nao_lidas"], 1)
        self.assertEqual(conversas["nao_lidas"], 1)

    def test_abrir_a_conversa_marca_como_lida(self):
        enviar_mensagem(ALUNO, self.turma_id, "Oi professor.")
        abrir_conversa(PROFESSOR, self.turma_id, ALUNO)

        self.assertEqual(listar_conversas(PROFESSOR)["nao_lidas"], 0)

    def test_abrir_nao_marca_as_proprias_como_lidas(self):
        """Marcar as proprias zeraria o contador do interlocutor."""
        enviar_mensagem(ALUNO, self.turma_id, "Oi professor.")
        abrir_conversa(ALUNO, self.turma_id)

        self.assertEqual(listar_conversas(PROFESSOR)["nao_lidas"], 1)

    def test_professor_ve_aluno_sem_conversa_iniciada(self):
        """Ele precisa poder puxar assunto, nao so responder."""
        conversas = listar_conversas(PROFESSOR)["conversas"]

        self.assertEqual(len(conversas), 2)
        self.assertTrue(all(c["ultima_em"] is None for c in conversas))

    def test_conversa_com_mensagem_nova_vem_primeiro(self):
        enviar_mensagem("aluno3@teste.com", self.turma_id, "Oi!")

        primeira = listar_conversas(PROFESSOR)["conversas"][0]
        self.assertEqual(primeira["contraparte_email"], "aluno3@teste.com")

    def test_aluno_tem_uma_conversa_por_turma(self):
        outra = criar_turma(ADMIN, PROFESSOR, "Clinica", "2026.2")["turma"]["id"]
        matricular_aluno(ADMIN, ALUNO, outra)

        conversas = listar_conversas(ALUNO)["conversas"]
        self.assertEqual(len(conversas), 2)

    def test_destinatario_e_avisado(self):
        enviar_mensagem(ALUNO, self.turma_id, "Oi professor.")

        tipos = [n["tipo"] for n in listar_notificacoes(PROFESSOR)["notificacoes"]]
        self.assertIn("mensagem", tipos)

    def test_quem_envia_nao_se_notifica(self):
        enviar_mensagem(ALUNO, self.turma_id, "Oi professor.")

        avisos = [n for n in listar_notificacoes(ALUNO)["notificacoes"] if n["tipo"] == "mensagem"]
        self.assertEqual(avisos, [])


# =========================================================================
# Turmas do aluno
#
# A lista alimenta o seletor do chat de estudos **e** a oferta de levar a
# dúvida ao professor quando o material não cobre a pergunta. Por isso o nome
# do professor é dado da rota, não enfeite: sem ele a oferta sai genérica.
# =========================================================================

class TestesTurmasDoAluno(BaseDelta):

    def test_traz_o_nome_do_professor_da_turma(self):
        turma = listar_turmas_do_aluno(ALUNO)["turmas"][0]

        self.assertEqual(turma["professor_nome"], "Professor Um")

    def test_cada_turma_traz_o_seu_proprio_professor(self):
        outra = criar_turma(ADMIN, PROFESSOR2, "Clinica", "2026.2")["turma"]["id"]
        matricular_aluno(ADMIN, ALUNO, outra)

        por_nome = {t["nome"]: t["professor_nome"] for t in listar_turmas_do_aluno(ALUNO)["turmas"]}

        self.assertEqual(por_nome["Cardiologia"], "Professor Um")
        self.assertEqual(por_nome["Clinica"], "Professor Dois")

    def test_professor_sem_nome_cai_no_email(self):
        """Banco anterior à coluna `nome`: a oferta precisa dizer *algo*.

        `criar_conta_staff` exige nome, então o produto não cria essa linha. Mas
        `nome` entrou por migração (ver infra/database.py) e é anulável, logo
        contas de antes dela existirem vêm com NULL. Por isso o INSERT direto:
        é o único jeito de reproduzir o dado que o fallback protege.
        """
        conexao = sqlite3.connect(CAMINHO_DB)
        conexao.execute(
            "INSERT INTO users (email, senha, tipo) VALUES (?, ?, ?)",
            ("anonimo@teste.com", hash_senha(SENHA), "professor"),
        )
        conexao.commit()
        conexao.close()

        turma = criar_turma(ADMIN, "anonimo@teste.com", "Anatomia", "2026.2")["turma"]["id"]
        matricular_aluno(ADMIN, ALUNO, turma)

        achada = [t for t in listar_turmas_do_aluno(ALUNO)["turmas"] if t["nome"] == "Anatomia"][0]

        self.assertEqual(achada["professor_nome"], "anonimo@teste.com")

    def test_turma_de_outro_aluno_nao_aparece(self):
        """A junção com users não pode ter afrouxado o filtro de matrícula."""
        self.assertEqual(listar_turmas_do_aluno(ALUNO_FORA)["turmas"], [])



# =========================================================================
# A turma de alunos (coorte) e o espalhamento para as disciplinas
#
# Vocabulário: `coorte` é a turma de alunos (MED 3A) e `turma` no banco é uma
# disciplina (Anatomia). Ver a nota em regras/coortes.py.
#
# A invariante central: `matriculas` continua sendo a única verdade sobre quem
# cursa o quê, e a coorte só escreve nela. Os 9 módulos que consultam
# `matriculas` direto não sabem que a coorte existe, e é isso que os mantém
# corretos sem alterar nenhum deles.
# =========================================================================

class BaseCoorte(BaseDelta):
    """MED 3A com Anatomia e Fisiologia, e um aluno de fora para controle."""

    def setUp(self):
        super().setUp()
        self.coorte_id = criar_coorte(ADMIN, "MED 3A", "2026.2")["coorte"]["id"]
        self.anatomia = criar_turma(
            ADMIN, PROFESSOR, "Anatomia", "2026.2", coorte_id=self.coorte_id
        )["turma"]["id"]
        self.fisiologia = criar_turma(
            ADMIN, PROFESSOR2, "Fisiologia", "2026.2", coorte_id=self.coorte_id
        )["turma"]["id"]

    def cursa(self, aluno_email, turma_id) -> bool:
        """Pergunta do jeito que o resto do sistema pergunta."""
        from regras.matriculas import aluno_matriculado_na_turma

        return aluno_matriculado_na_turma(aluno_email, turma_id)


class TestesCoorte(BaseCoorte):

    def test_nome_e_semestre_nao_repetem(self):
        repetida = criar_coorte(ADMIN, "MED 3A", "2026.2")
        self.assertFalse(repetida["sucesso"])

    def test_mesmo_nome_em_outro_semestre_e_outra_turma(self):
        """A MED 3A de 2027/1 não é a de 2026/2 — são pessoas diferentes."""
        outra = criar_coorte(ADMIN, "MED 3A", "2027.1")
        self.assertTrue(outra["sucesso"])

    def test_so_admin_cria(self):
        self.assertFalse(criar_coorte(PROFESSOR, "MED 4A", "2026.2")["sucesso"])
        self.assertFalse(criar_coorte(ALUNO, "MED 4A", "2026.2")["sucesso"])

    def test_listagem_conta_alunos_e_disciplinas(self):
        matricular_na_coorte(ADMIN, ALUNO, self.coorte_id)

        coorte = [c for c in listar_coortes(ADMIN)["coortes"] if c["id"] == self.coorte_id][0]

        self.assertEqual(coorte["total_alunos"], 1)
        self.assertEqual(coorte["total_disciplinas"], 2)


class TestesEspalhamento(BaseCoorte):

    def test_entrar_na_turma_matricula_nas_disciplinas(self):
        resultado = matricular_na_coorte(ADMIN, ALUNO, self.coorte_id)

        self.assertTrue(resultado["sucesso"])
        self.assertEqual(resultado["matriculados"], 2)
        self.assertTrue(self.cursa(ALUNO, self.anatomia))
        self.assertTrue(self.cursa(ALUNO, self.fisiologia))

    def test_disciplina_criada_depois_ja_nasce_com_a_turma(self):
        """O caso que o espalhamento-como-evento poderia ter perdido."""
        matricular_na_coorte(ADMIN, ALUNO, self.coorte_id)

        semiologia = criar_turma(
            ADMIN, PROFESSOR, "Semiologia", "2026.2", coorte_id=self.coorte_id
        )["turma"]["id"]

        self.assertTrue(self.cursa(ALUNO, semiologia))

    def test_aluno_de_fora_da_turma_nao_entra(self):
        matricular_na_coorte(ADMIN, ALUNO, self.coorte_id)

        self.assertFalse(self.cursa(ALUNO_FORA, self.anatomia))
        self.assertFalse(self.cursa(ALUNO_FORA, self.fisiologia))

    def test_sincronizar_duas_vezes_nao_duplica(self):
        matricular_na_coorte(ADMIN, ALUNO, self.coorte_id)
        sincronizar_coorte(self.coorte_id)
        sincronizar_coorte(self.coorte_id)

        conexao = sqlite3.connect(CAMINHO_DB)
        total = conexao.execute(
            "SELECT COUNT(*) FROM matriculas WHERE turma_id IN (?, ?)",
            (self.anatomia, self.fisiologia),
        ).fetchone()[0]
        conexao.close()

        self.assertEqual(total, 2)

    def test_disciplina_solta_nao_recebe_ninguem(self):
        """Sem coorte, nada espalha — continua funcionando como antes."""
        matricular_na_coorte(ADMIN, ALUNO, self.coorte_id)
        optativa = criar_turma(ADMIN, PROFESSOR, "Cirurgia Experimental", "2026.2")["turma"]["id"]

        self.assertFalse(self.cursa(ALUNO, optativa))

    def test_matricula_feita_na_mao_sobrevive_ao_espalhamento(self):
        """O sincronismo só manda nas disciplinas da coorte.

        Apagar uma matrícula que o admin fez à mão numa disciplina solta seria
        efeito sem causa visível — ele nem saberia onde foi.
        """
        optativa = criar_turma(ADMIN, PROFESSOR, "Cirurgia Experimental", "2026.2")["turma"]["id"]
        matricular_aluno(ADMIN, ALUNO, optativa)

        matricular_na_coorte(ADMIN, ALUNO, self.coorte_id)
        sincronizar_coorte(self.coorte_id)

        self.assertTrue(self.cursa(ALUNO, optativa))

    def test_sair_da_turma_tira_das_disciplinas(self):
        matricular_na_coorte(ADMIN, ALUNO, self.coorte_id)

        remover_da_coorte(ADMIN, ALUNO, self.coorte_id)

        self.assertFalse(self.cursa(ALUNO, self.anatomia))
        self.assertFalse(self.cursa(ALUNO, self.fisiologia))

    def test_aluno_nao_entra_duas_vezes(self):
        matricular_na_coorte(ADMIN, ALUNO, self.coorte_id)

        self.assertFalse(matricular_na_coorte(ADMIN, ALUNO, self.coorte_id)["sucesso"])

    def test_so_admin_matricula(self):
        self.assertFalse(matricular_na_coorte(PROFESSOR, ALUNO, self.coorte_id)["sucesso"])
        self.assertFalse(matricular_na_coorte(ALUNO, ALUNO_FORA, self.coorte_id)["sucesso"])


class TestesExcecao(BaseCoorte):
    """O aluno que traz Anatomia aproveitada de outra instituição."""

    def setUp(self):
        super().setUp()
        matricular_na_coorte(ADMIN, ALUNO, self.coorte_id)

    def test_excecao_tira_da_disciplina_e_mantem_na_turma(self):
        resultado = criar_excecao(ADMIN, ALUNO, self.anatomia)

        self.assertTrue(resultado["sucesso"])
        self.assertFalse(self.cursa(ALUNO, self.anatomia))
        # Continua na turma, e por isso continua nas outras disciplinas.
        self.assertTrue(self.cursa(ALUNO, self.fisiologia))
        emails = [a["email"] for a in listar_alunos_da_coorte(ADMIN, self.coorte_id)["alunos"]]
        self.assertIn(ALUNO, emails)

    def test_excecao_sobrevive_a_um_novo_espalhamento(self):
        """A invariante que justifica a exceção ser tabela, e não só a ausência
        de uma linha em `matriculas`.

        Guardada só como ausência, o próximo sincronismo — disparado por
        qualquer aluno novo entrando na turma — recolocaria este aqui em
        Anatomia, e o admin teria que tirar de novo sem entender por quê.
        """
        criar_excecao(ADMIN, ALUNO, self.anatomia)

        matricular_na_coorte(ADMIN, ALUNO_FORA, self.coorte_id)
        sincronizar_coorte(self.coorte_id)

        self.assertFalse(self.cursa(ALUNO, self.anatomia))
        self.assertTrue(self.cursa(ALUNO_FORA, self.anatomia))

    def test_excecao_aparece_na_listagem_da_turma(self):
        criar_excecao(ADMIN, ALUNO, self.anatomia)

        aluno = [a for a in listar_alunos_da_coorte(ADMIN, self.coorte_id)["alunos"]
                 if a["email"] == ALUNO][0]

        self.assertEqual([d["nome"] for d in aluno["fora_de"]], ["Anatomia"])

    def test_desfazer_excecao_devolve_a_disciplina(self):
        criar_excecao(ADMIN, ALUNO, self.anatomia)

        resultado = remover_excecao(ADMIN, ALUNO, self.anatomia)

        self.assertTrue(resultado["sucesso"])
        self.assertTrue(self.cursa(ALUNO, self.anatomia))

    def test_excecao_nao_se_repete(self):
        criar_excecao(ADMIN, ALUNO, self.anatomia)

        self.assertFalse(criar_excecao(ADMIN, ALUNO, self.anatomia)["sucesso"])

    def test_desfazer_excecao_que_nao_existe_e_recusado(self):
        self.assertFalse(remover_excecao(ADMIN, ALUNO, self.anatomia)["sucesso"])

    def test_excecao_recusada_em_disciplina_sem_turma(self):
        """Em disciplina solta o admin desmatricula direto — duas formas de
        dizer a mesma coisa seria uma a mais do que dá para confiar."""
        optativa = criar_turma(ADMIN, PROFESSOR, "Cirurgia Experimental", "2026.2")["turma"]["id"]

        self.assertFalse(criar_excecao(ADMIN, ALUNO, optativa)["sucesso"])

    def test_excecao_recusada_para_aluno_de_outra_turma(self):
        self.assertFalse(criar_excecao(ADMIN, ALUNO_FORA, self.anatomia)["sucesso"])

    def test_sair_da_turma_apaga_as_excecoes(self):
        """Rematrícula futura não herda decisão de outro semestre em silêncio."""
        criar_excecao(ADMIN, ALUNO, self.anatomia)
        remover_da_coorte(ADMIN, ALUNO, self.coorte_id)

        matricular_na_coorte(ADMIN, ALUNO, self.coorte_id)

        self.assertTrue(self.cursa(ALUNO, self.anatomia))

    def test_so_admin_faz_excecao(self):
        self.assertFalse(criar_excecao(PROFESSOR, ALUNO, self.anatomia)["sucesso"])
        self.assertFalse(criar_excecao(ALUNO, ALUNO, self.anatomia)["sucesso"])


class TestesDesfazerCoorte(BaseCoorte):

    def setUp(self):
        super().setUp()
        matricular_na_coorte(ADMIN, ALUNO, self.coorte_id)

    def test_desfazer_a_turma_nao_desfaz_o_semestre_do_aluno(self):
        """O aluno cursou Anatomia. Isso não deixa de ter acontecido porque o
        agrupamento foi desfeito — há nota e material lido do outro lado."""
        excluir_coorte(ADMIN, self.coorte_id)

        self.assertTrue(self.cursa(ALUNO, self.anatomia))
        self.assertTrue(self.cursa(ALUNO, self.fisiologia))

    def test_disciplinas_voltam_a_ser_soltas(self):
        excluir_coorte(ADMIN, self.coorte_id)

        conexao = sqlite3.connect(CAMINHO_DB)
        vinculadas = conexao.execute(
            "SELECT COUNT(*) FROM turmas WHERE coorte_id IS NOT NULL"
        ).fetchone()[0]
        conexao.close()

        self.assertEqual(vinculadas, 0)

    def test_so_admin_desfaz(self):
        self.assertFalse(excluir_coorte(PROFESSOR, self.coorte_id)["sucesso"])

    def test_disciplinas_da_turma_sao_listadas_com_professor(self):
        disciplinas = listar_disciplinas_da_coorte(ADMIN, self.coorte_id)["disciplinas"]

        por_nome = {d["nome"]: d for d in disciplinas}
        self.assertEqual(por_nome["Anatomia"]["professor_nome"], "Professor Um")
        self.assertEqual(por_nome["Fisiologia"]["professor_nome"], "Professor Dois")
        self.assertEqual(por_nome["Anatomia"]["total_alunos"], 1)



# =========================================================================
# As rotas da coorte
#
# Os testes acima chamam os módulos direto e não veem nada do HTTP. Esta classe
# existe por causa de um bug que só aparecia pela rota: `DELETE
# /admin/coortes/excecoes` casava com `DELETE /admin/coortes/{coorte_id}`, e o
# FastAPI tentava ler "excecoes" como inteiro. A lógica estava certa, os 27
# testes de unidade passavam, e a tela não funcionava.
# =========================================================================

class TestesRotasCoorte(BaseDelta):

    def setUp(self):
        super().setUp()

        # Importado aqui e não no topo: carregar `main` puxa o app inteiro, e
        # só esta classe precisa dele.
        from fastapi.testclient import TestClient

        import main

        self.cliente = TestClient(main.app)
        self.adm = self._token(ADMIN)

    def _token(self, email):
        resposta = self.cliente.post("/login", json={"email": email, "senha": SENHA})
        return resposta.json()["token"]

    def _cab(self, token):
        return {"Authorization": f"Bearer {token}"}

    def _disciplinas_do_aluno(self, email=ALUNO):
        """O que o aluno cursa **fora** da linha de base.

        `BaseDelta` já o matricula em Cardiologia à mão, e essa matrícula direta
        é justamente a que a coorte não deve mexer. Descontá-la isola o efeito
        que estes testes medem — e o teste de que ela sobrevive está em
        TestesEspalhamento.
        """
        resposta = self.cliente.get("/aluno/turmas", headers=self._cab(self._token(email)))
        nomes = [t["nome"] for t in resposta.json()["turmas"]]
        self.assertIn("Cardiologia", nomes, "a matrícula direta da linha de base desapareceu")
        return sorted(n for n in nomes if n != "Cardiologia")

    def _criar_coorte(self, nome="MED 3A"):
        resposta = self.cliente.post(
            "/admin/coortes", json={"nome": nome, "semestre": "2026.2"}, headers=self._cab(self.adm)
        )
        return resposta.json()["coorte"]["id"]

    def test_excluir_coorte_por_id(self):
        coorte_id = self._criar_coorte()

        resposta = self.cliente.delete(f"/admin/coortes/{coorte_id}", headers=self._cab(self.adm))

        self.assertTrue(resposta.json()["sucesso"], resposta.text)

    def test_excecao_nao_colide_com_o_id_da_coorte(self):
        """O bug que a suíte de unidade não via.

        Se a rota da exceção voltar para baixo de /admin/coortes/, o DELETE
        passa a ser lido como um id e responde 422 — e o sintoma não aponta
        para a causa.
        """
        coorte_id = self._criar_coorte()
        disciplina = criar_turma(
            ADMIN, PROFESSOR, "Anatomia", "2026.2", coorte_id=coorte_id
        )["turma"]["id"]
        self.cliente.post(
            f"/admin/coortes/{coorte_id}/alunos",
            json={"aluno_email": ALUNO},
            headers=self._cab(self.adm),
        )

        corpo = {"aluno_email": ALUNO, "turma_id": disciplina}

        criar = self.cliente.post("/admin/excecoes", json=corpo, headers=self._cab(self.adm))
        self.assertEqual(criar.status_code, 200, criar.text)
        self.assertTrue(criar.json()["sucesso"], criar.text)

        remover = self.cliente.request(
            "DELETE", "/admin/excecoes", json=corpo, headers=self._cab(self.adm)
        )
        self.assertEqual(remover.status_code, 200, remover.text)
        self.assertTrue(remover.json()["sucesso"], remover.text)

    def test_matricula_em_cascata_pela_rota(self):
        coorte_id = self._criar_coorte()
        criar_turma(ADMIN, PROFESSOR, "Anatomia", "2026.2", coorte_id=coorte_id)
        criar_turma(ADMIN, PROFESSOR2, "Fisiologia", "2026.2", coorte_id=coorte_id)

        resposta = self.cliente.post(
            f"/admin/coortes/{coorte_id}/alunos",
            json={"aluno_email": ALUNO},
            headers=self._cab(self.adm),
        )

        self.assertEqual(resposta.json()["matriculados"], 2, resposta.text)

        # A visão do aluno é o que importa: é dela que o seletor do chat vive.
        self.assertEqual(self._disciplinas_do_aluno(), ["Anatomia", "Fisiologia"])

    def test_remover_aluno_da_coorte_aceita_corpo_no_delete(self):
        """DELETE com corpo, igual a /admin/matriculas. Alguns clientes o
        descartam, então a rota precisa ser exercitada de verdade."""
        coorte_id = self._criar_coorte()
        criar_turma(ADMIN, PROFESSOR, "Anatomia", "2026.2", coorte_id=coorte_id)
        self.cliente.post(
            f"/admin/coortes/{coorte_id}/alunos",
            json={"aluno_email": ALUNO},
            headers=self._cab(self.adm),
        )

        resposta = self.cliente.request(
            "DELETE",
            f"/admin/coortes/{coorte_id}/alunos",
            json={"aluno_email": ALUNO},
            headers=self._cab(self.adm),
        )

        self.assertTrue(resposta.json()["sucesso"], resposta.text)
        self.assertEqual(self._disciplinas_do_aluno(), [])

    def test_disciplina_criada_pela_rota_aceita_a_coorte(self):
        coorte_id = self._criar_coorte()
        self.cliente.post(
            f"/admin/coortes/{coorte_id}/alunos",
            json={"aluno_email": ALUNO},
            headers=self._cab(self.adm),
        )

        resposta = self.cliente.post(
            "/admin/turmas",
            json={
                "professor_email": PROFESSOR,
                "nome": "Semiologia",
                "semestre": "2026.2",
                "coorte_id": coorte_id,
            },
            headers=self._cab(self.adm),
        )

        self.assertTrue(resposta.json()["sucesso"], resposta.text)
        self.assertEqual(self._disciplinas_do_aluno(), ["Semiologia"])

    def test_disciplina_sem_coorte_continua_valendo(self):
        """coorte_id ausente não é erro: disciplina solta é caso legítimo."""
        resposta = self.cliente.post(
            "/admin/turmas",
            json={"professor_email": PROFESSOR, "nome": "Cirurgia Experimental", "semestre": "2026.2"},
            headers=self._cab(self.adm),
        )

        self.assertTrue(resposta.json()["sucesso"], resposta.text)

    def test_professor_e_aluno_nao_alcancam_as_rotas_de_coorte(self):
        coorte_id = self._criar_coorte()

        for email in (PROFESSOR, ALUNO):
            token = self._cab(self._token(email))
            with self.subTest(perfil=email):
                self.assertIn(self.cliente.get("/admin/coortes", headers=token).status_code, (401, 403))
                self.assertIn(
                    self.cliente.post(
                        "/admin/coortes", json={"nome": "MED 4A", "semestre": "2026.2"}, headers=token
                    ).status_code,
                    (401, 403),
                )
                self.assertIn(
                    self.cliente.get(f"/admin/coortes/{coorte_id}/alunos", headers=token).status_code,
                    (401, 403),
                )

    def test_sem_token_nao_alcanca(self):
        self.assertIn(self.cliente.get("/admin/coortes").status_code, (401, 403))



# =========================================================================
# Entrega em documento
#
# Nem toda atividade cabe numa caixa de texto: relatório de caso clínico, foto
# de peça anatômica, traçado de ECG. O anexo é propriedade da **atividade**
# ('nenhum' / 'opcional' / 'obrigatorio'), e não um terceiro tipo.
#
# O que mais importa aqui é quem pode baixar: o aluno que entregou e o
# professor dono da atividade, e mais ninguém. Trabalho de aluno não é
# material de turma.
# =========================================================================

# Um PDF minúsculo, porém válido: base64 de um arquivo de verdade, para o
# caminho de gravação ser exercitado como em produção.
PDF_BASE64 = (
    "JVBERi0xLjQKMSAwIG9iago8PC9UeXBlL0NhdGFsb2cvUGFnZXMgMiAwIFI+PgplbmRvYmoK"
    "MiAwIG9iago8PC9UeXBlL1BhZ2VzL0tpZHNbXS9Db3VudCAwPj4KZW5kb2JqCnRyYWlsZXIK"
    "PDwvUm9vdCAxIDAgUj4+CiUlRU9G"
)


class BaseAnexo(BaseAtividades):

    def criar_com_anexo(self, anexo, tipo="dissertativa", pontos=10):
        resultado = criar_atividade_em_turmas(
            PROFESSOR,
            [self.turma_id],
            titulo=f"Caso clinico ({anexo})",
            tipo=tipo,
            enunciado="Descreva o caso.",
            pontos=pontos,
            rascunho=False,
            anexo=anexo,
        )
        return resultado

    def tearDown(self):
        # Os arquivos gravados no disco não são do banco e não somem com ele.
        import shutil

        from infra.arquivos import PASTA_ENTREGAS

        shutil.rmtree(PASTA_ENTREGAS, ignore_errors=True)
        super().tearDown()


class TestesAtividadeComAnexo(BaseAnexo):

    def test_anexo_invalido_e_recusado(self):
        resultado = self.criar_com_anexo("talvez")

        self.assertFalse(resultado["sucesso"])

    def test_objetiva_nao_aceita_anexo(self):
        """O sistema corrige pelo gabarito — ninguém leria o arquivo.

        Aceitar aqui criaria promessa que a plataforma não cumpre: o aluno
        anexa o trabalho e ele nunca chega a ser visto por ninguém.
        """
        resultado = criar_atividade_em_turmas(
            PROFESSOR,
            [self.turma_id],
            titulo="Quiz",
            tipo="objetiva",
            rascunho=False,
            anexo="obrigatorio",
            questoes=[{"enunciado": "1+1?", "alternativas": ["1", "2"], "correta": 1}],
        )

        self.assertFalse(resultado["sucesso"])

    def test_atividade_antiga_continua_sem_anexo(self):
        """Quem já existia não muda de comportamento por causa da migração."""
        atividade = criar_atividade_em_turmas(
            PROFESSOR, [self.turma_id], titulo="Resenha", tipo="dissertativa", rascunho=False
        )["atividade_ids"][0]

        vista = obter_atividade_do_aluno(ALUNO, atividade)["atividade"]

        self.assertEqual(vista["anexo"], "nenhum")

    def test_a_listagem_do_professor_traz_o_anexo(self):
        """O formulário de edição lê daqui.

        Sem isto ele lia `undefined`, caía no padrão 'nenhum', e salvar a
        edição de uma atividade com anexo obrigatório o apagava em silêncio.
        """
        self.criar_com_anexo("obrigatorio")

        atividade = [
            a for a in listar_atividades(PROFESSOR)["atividades"]
            if a["titulo"] == "Caso clinico (obrigatorio)"
        ][0]

        self.assertEqual(atividade["anexo"], "obrigatorio")

    def test_o_aluno_sabe_que_precisa_anexar(self):
        atividade = self.criar_com_anexo("obrigatorio")["atividade_ids"][0]

        vista = obter_atividade_do_aluno(ALUNO, atividade)["atividade"]

        self.assertEqual(vista["anexo"], "obrigatorio")


class TestesEntregaComArquivo(BaseAnexo):

    def test_entrega_com_arquivo_guarda_o_nome_original(self):
        atividade = self.criar_com_anexo("opcional")["atividade_ids"][0]

        resultado = enviar_entrega(
            ALUNO, atividade, "Segue o relatorio.", PDF_BASE64, "caso-clinico.pdf"
        )

        self.assertTrue(resultado["sucesso"], resultado)
        entrega = obter_atividade_do_aluno(ALUNO, atividade)["entrega"]
        self.assertEqual(entrega["arquivo_nome"], "caso-clinico.pdf")

    def test_arquivo_vai_para_o_disco_com_nome_de_uuid(self):
        """Nome vindo do cliente traz '../' e colide entre dois alunos que
        chamaram o trabalho de 'relatorio.pdf'."""
        import os

        atividade = self.criar_com_anexo("opcional")["atividade_ids"][0]
        enviar_entrega(ALUNO, atividade, "texto", PDF_BASE64, "relatorio.pdf")

        entrega_id = obter_atividade_do_aluno(ALUNO, atividade)["entrega"]["entrega_id"]
        caminho, nome = obter_arquivo_entrega(ALUNO, entrega_id)

        self.assertTrue(os.path.isfile(caminho))
        self.assertNotIn("relatorio", os.path.basename(caminho))
        self.assertEqual(nome, "relatorio.pdf")

    def test_anexo_obrigatorio_recusa_entrega_sem_arquivo(self):
        atividade = self.criar_com_anexo("obrigatorio")["atividade_ids"][0]

        resultado = enviar_entrega(ALUNO, atividade, "Segue em anexo.")

        self.assertFalse(resultado["sucesso"])

    def test_anexo_obrigatorio_dispensa_o_texto(self):
        """O documento **é** a entrega. Exigir texto também faria o aluno
        escrever 'segue em anexo' só para o formulário deixar enviar."""
        atividade = self.criar_com_anexo("obrigatorio")["atividade_ids"][0]

        resultado = enviar_entrega(ALUNO, atividade, "", PDF_BASE64, "monografia.pdf")

        self.assertTrue(resultado["sucesso"], resultado)

    def test_atividade_sem_anexo_recusa_arquivo(self):
        atividade = self.criar_com_anexo("nenhum")["atividade_ids"][0]

        resultado = enviar_entrega(ALUNO, atividade, "texto", PDF_BASE64, "arquivo.pdf")

        self.assertFalse(resultado["sucesso"])

    def test_formato_proibido_e_recusado(self):
        atividade = self.criar_com_anexo("opcional")["atividade_ids"][0]

        resultado = enviar_entrega(ALUNO, atividade, "texto", PDF_BASE64, "virus.exe")

        self.assertFalse(resultado["sucesso"])

    def test_arquivo_recusado_nao_deixa_entrega_gravada(self):
        """A recusa acontece antes de gravar qualquer coisa.

        Gravando a entrega primeiro, o aluno ficaria com "já entregou" e sem
        arquivo — e sem poder tentar de novo.
        """
        atividade = self.criar_com_anexo("opcional")["atividade_ids"][0]
        enviar_entrega(ALUNO, atividade, "texto", PDF_BASE64, "virus.exe")

        entrega = obter_atividade_do_aluno(ALUNO, atividade)["entrega"]
        self.assertIsNone(entrega["enviado_em"])

        # E a segunda tentativa, agora com formato válido, passa.
        segunda = enviar_entrega(ALUNO, atividade, "texto", PDF_BASE64, "relatorio.pdf")
        self.assertTrue(segunda["sucesso"], segunda)

    def test_professor_ve_o_nome_do_arquivo_na_lista_de_entregas(self):
        atividade = self.criar_com_anexo("opcional")["atividade_ids"][0]
        enviar_entrega(ALUNO, atividade, "texto", PDF_BASE64, "caso-clinico.pdf")

        entregas = listar_entregas(atividade, PROFESSOR)["entregas"]
        minha = [e for e in entregas if e["aluno_email"] == ALUNO][0]

        self.assertEqual(minha["arquivo_nome"], "caso-clinico.pdf")


class TestesPermissaoDoArquivo(BaseAnexo):
    """Quem pode baixar o trabalho do aluno."""

    def setUp(self):
        super().setUp()
        self.atividade = self.criar_com_anexo("obrigatorio")["atividade_ids"][0]
        enviar_entrega(ALUNO, self.atividade, "", PDF_BASE64, "caso-clinico.pdf")
        self.entrega_id = obter_atividade_do_aluno(ALUNO, self.atividade)["entrega"]["entrega_id"]

    def test_quem_entregou_baixa(self):
        self.assertIsNotNone(obter_arquivo_entrega(ALUNO, self.entrega_id))

    def test_o_professor_da_atividade_baixa(self):
        self.assertIsNotNone(obter_arquivo_entrega(PROFESSOR, self.entrega_id))

    def test_outro_aluno_da_mesma_turma_nao_baixa(self):
        """Trabalho de aluno não é material de turma."""
        matricular_aluno(ADMIN, ALUNO_FORA, self.turma_id)

        self.assertIsNone(obter_arquivo_entrega(ALUNO_FORA, self.entrega_id))

    def test_outro_professor_nao_baixa(self):
        self.assertIsNone(obter_arquivo_entrega(PROFESSOR2, self.entrega_id))

    def test_o_admin_nao_baixa(self):
        """Ele governa contas e turmas; não lê o que o aluno escreveu."""
        self.assertIsNone(obter_arquivo_entrega(ADMIN, self.entrega_id))

    def test_entrega_que_nao_existe_devolve_nada(self):
        self.assertIsNone(obter_arquivo_entrega(PROFESSOR, 99999))

    def test_entrega_sem_arquivo_devolve_nada(self):
        outra = self.criar_com_anexo("nenhum")["atividade_ids"][0]
        enviar_entrega(ALUNO, outra, "so texto")
        entrega_id = obter_atividade_do_aluno(ALUNO, outra)["entrega"]["entrega_id"]

        self.assertIsNone(obter_arquivo_entrega(ALUNO, entrega_id))



# =========================================================================
# A rota de download da entrega
#
# Uma rota para os dois perfis (`usuario_logado`, não `usuario_aluno`), porque
# quem pode baixar é o aluno que entregou **ou** o professor dono da atividade.
# Vale exercitar pelo HTTP: a permissão de unidade já está coberta, o que se
# testa aqui é o 404 chegar como 404 e o arquivo voltar com o nome certo.
# =========================================================================

class TestesRotaDoAnexo(BaseAtividades):

    def setUp(self):
        super().setUp()

        from fastapi.testclient import TestClient

        import main

        self.cliente = TestClient(main.app)
        self.atividade = criar_atividade_em_turmas(
            PROFESSOR, [self.turma_id], titulo="Caso clinico",
            tipo="dissertativa", rascunho=False, anexo="obrigatorio",
        )["atividade_ids"][0]
        enviar_entrega(ALUNO, self.atividade, "", PDF_BASE64, "caso-clinico.pdf")
        self.entrega_id = obter_atividade_do_aluno(
            ALUNO, self.atividade
        )["entrega"]["entrega_id"]

    def tearDown(self):
        import shutil

        from infra.arquivos import PASTA_ENTREGAS

        shutil.rmtree(PASTA_ENTREGAS, ignore_errors=True)
        super().tearDown()

    def _token(self, email):
        return self.cliente.post(
            "/login", json={"email": email, "senha": SENHA}
        ).json()["token"]

    def _baixar(self, email):
        return self.cliente.get(
            f"/entregas/{self.entrega_id}/arquivo",
            headers={"Authorization": f"Bearer {self._token(email)}"},
        )

    def test_quem_entregou_recebe_o_arquivo_com_o_nome_original(self):
        resposta = self._baixar(ALUNO)

        self.assertEqual(resposta.status_code, 200, resposta.text)
        self.assertIn("caso-clinico.pdf", resposta.headers.get("content-disposition", ""))
        self.assertTrue(resposta.content.startswith(b"%PDF"))

    def test_o_professor_da_atividade_recebe(self):
        self.assertEqual(self._baixar(PROFESSOR).status_code, 200)

    def test_colega_de_turma_recebe_404(self):
        """404 e não 403: distinguir "não existe" de "não é seu" revelaria quem
        entregou o quê para quem tentasse ids na mão."""
        matricular_aluno(ADMIN, ALUNO_FORA, self.turma_id)

        self.assertEqual(self._baixar(ALUNO_FORA).status_code, 404)

    def test_outro_professor_recebe_404(self):
        self.assertEqual(self._baixar(PROFESSOR2).status_code, 404)

    def test_admin_recebe_404(self):
        self.assertEqual(self._baixar(ADMIN).status_code, 404)

    def test_sem_token_nao_passa(self):
        resposta = self.cliente.get(f"/entregas/{self.entrega_id}/arquivo")

        self.assertIn(resposta.status_code, (401, 403))

    def test_entrega_inexistente_e_404(self):
        resposta = self.cliente.get(
            "/entregas/99999/arquivo",
            headers={"Authorization": f"Bearer {self._token(PROFESSOR)}"},
        )

        self.assertEqual(resposta.status_code, 404)



# =========================================================================
# Recuperação de senha
#
# Não havia teste nenhum aqui, e era onde estava o furo mais sério do sistema:
# o código tem 6 dígitos e a busca era `WHERE reset_token = ?` — **global**.
# Um atacante tentava códigos contra qualquer conta com recuperação pendente,
# sem limite de tentativa. 900 mil combinações se percorrem em minutos.
#
# Duas defesas, e as duas precisam de teste porque nenhuma é visível de fora:
# o código agora está amarrado ao e-mail, e cinco erros o descartam.
# =========================================================================

class TestesRecuperacaoDeSenha(BaseDelta):

    def _codigo_de(self, email):
        """Lê o código direto do banco — em produção ele vai por e-mail."""
        conexao = sqlite3.connect(CAMINHO_DB)
        linha = conexao.execute(
            "SELECT reset_token FROM users WHERE email = ?", (email,)
        ).fetchone()
        conexao.close()
        return linha[0] if linha else None

    def test_o_fluxo_normal_funciona(self):
        solicitar_recuperacao(ALUNO)
        codigo = self._codigo_de(ALUNO)

        resultado = redefinir_senha(ALUNO, codigo, "senhanova123")

        self.assertTrue(resultado["sucesso"], resultado)
        self.assertTrue(realizar_login(ALUNO, "senhanova123")["sucesso"])

    def test_a_senha_antiga_para_de_valer(self):
        solicitar_recuperacao(ALUNO)
        redefinir_senha(ALUNO, self._codigo_de(ALUNO), "senhanova123")

        self.assertFalse(realizar_login(ALUNO, SENHA)["sucesso"])

    def test_o_codigo_de_um_nao_serve_para_outro(self):
        """O furo principal.

        Antes a busca era global: com o código do Aluno Um em mãos, este
        mesmo chamado trocava a senha do Aluno Dois. Era o que transformava
        900 mil palpites contra *o sistema* em invasão de *alguma* conta.
        """
        solicitar_recuperacao(ALUNO)
        codigo_do_aluno = self._codigo_de(ALUNO)
        solicitar_recuperacao(ALUNO_FORA)

        resultado = redefinir_senha(ALUNO_FORA, codigo_do_aluno, "invadida123")

        self.assertFalse(resultado["sucesso"])
        self.assertFalse(realizar_login(ALUNO_FORA, "invadida123")["sucesso"])

    def test_cinco_erros_queimam_o_codigo(self):
        """Sem teto, os 6 dígitos são 900 mil palpites livres."""
        solicitar_recuperacao(ALUNO)
        codigo = self._codigo_de(ALUNO)

        errado = "000000" if codigo != "000000" else "111111"
        for _ in range(MAX_TENTATIVAS_RESET):
            redefinir_senha(ALUNO, errado, "tentativa123")

        # O código certo também não vale mais: ele foi descartado.
        resultado = redefinir_senha(ALUNO, codigo, "senhanova123")

        self.assertFalse(resultado["sucesso"], resultado)
        self.assertTrue(realizar_login(ALUNO, SENHA)["sucesso"])

    def test_antes_do_teto_o_codigo_certo_ainda_vale(self):
        """Quem esqueceu a senha erra uma ou duas vezes e não pode ser punido."""
        solicitar_recuperacao(ALUNO)
        codigo = self._codigo_de(ALUNO)
        errado = "000000" if codigo != "000000" else "111111"

        redefinir_senha(ALUNO, errado, "tentativa123")
        redefinir_senha(ALUNO, errado, "tentativa123")

        self.assertTrue(redefinir_senha(ALUNO, codigo, "senhanova123")["sucesso"])

    def test_pedir_codigo_novo_devolve_as_tentativas(self):
        solicitar_recuperacao(ALUNO)
        errado = "000000" if self._codigo_de(ALUNO) != "000000" else "111111"
        for _ in range(MAX_TENTATIVAS_RESET - 1):
            redefinir_senha(ALUNO, errado, "tentativa123")

        solicitar_recuperacao(ALUNO)
        codigo = self._codigo_de(ALUNO)
        for _ in range(MAX_TENTATIVAS_RESET - 1):
            redefinir_senha(ALUNO, errado, "tentativa123")

        self.assertTrue(redefinir_senha(ALUNO, codigo, "senhanova123")["sucesso"])

    def test_a_resposta_nao_diz_se_a_conta_existe(self):
        """Senão a rota vira verificador de cadastro: com uma lista de e-mails,
        descobre-se quem é aluno desta instituição, um por requisição."""
        existe = solicitar_recuperacao(ALUNO)["mensagem"]
        nao_existe = solicitar_recuperacao("ninguem@lugar.com")["mensagem"]

        self.assertEqual(existe, nao_existe)

    def test_redefinir_sem_recuperacao_pendente_e_recusado(self):
        resultado = redefinir_senha(ALUNO, "123456", "senhanova123")

        self.assertFalse(resultado["sucesso"])

    def test_codigo_expirado_e_recusado(self):
        solicitar_recuperacao(ALUNO)
        codigo = self._codigo_de(ALUNO)

        conexao = sqlite3.connect(CAMINHO_DB)
        conexao.execute(
            "UPDATE users SET reset_expira = ? WHERE email = ?",
            ("2020-01-01T00:00:00", ALUNO),
        )
        conexao.commit()
        conexao.close()

        self.assertFalse(redefinir_senha(ALUNO, codigo, "senhanova123")["sucesso"])

    def test_senha_curta_e_recusada(self):
        solicitar_recuperacao(ALUNO)

        resultado = redefinir_senha(ALUNO, self._codigo_de(ALUNO), "123")

        self.assertFalse(resultado["sucesso"])

    def test_trocar_a_senha_derruba_as_sessoes_abertas(self):
        """Conta tomada: a senha nova não serve para nada enquanto o token do
        invasor continuar valendo por 12 horas."""
        token = realizar_login(ALUNO, SENHA)["token"]
        self.assertIsNotNone(buscar_usuario_da_sessao(token))

        solicitar_recuperacao(ALUNO)
        redefinir_senha(ALUNO, self._codigo_de(ALUNO), "senhanova123")

        self.assertIsNone(buscar_usuario_da_sessao(token))

    def test_o_codigo_usado_nao_serve_duas_vezes(self):
        solicitar_recuperacao(ALUNO)
        codigo = self._codigo_de(ALUNO)
        redefinir_senha(ALUNO, codigo, "senhanova123")

        segunda = redefinir_senha(ALUNO, codigo, "outra123456")

        self.assertFalse(segunda["sucesso"])
        self.assertTrue(realizar_login(ALUNO, "senhanova123")["sucesso"])



# =========================================================================
# Faixas do nível: bronze, prata, ouro, platina
#
# Os limites não são gosto: saíram de rodar os pesos de XP sobre um semestre de
# 20 semanas. Quem só aparece fica em Bronze o semestre inteiro, o aluno regular
# termina em Ouro, e Platina exige um semestre dedicado.
#
# A faixa é calculada no servidor de propósito. Se a tela também soubesse os
# limites, mudar a regra exigiria mudar os dois lugares — e o que ficasse para
# trás mostraria a faixa errada sem nenhum sintoma.
# =========================================================================

class TestesFaixas(unittest.TestCase):
    """Função pura: não precisa de banco."""

    def test_cada_faixa_nos_seus_limites(self):
        esperado = [
            (1, "Bronze"), (9, "Bronze"),
            (10, "Prata"), (19, "Prata"),
            (20, "Ouro"), (44, "Ouro"),
            (45, "Platina"), (86, "Platina"),
        ]
        for nivel, nome in esperado:
            with self.subTest(nivel=nivel):
                self.assertEqual(faixa_do_nivel(nivel)["nome"], nome)

    def test_a_faixa_nunca_desce_quando_o_nivel_sobe(self):
        """Monotonia: subir de nível não pode rebaixar ninguém.

        Um `>=` trocado por `>` numa comparação, ou a lista de FAIXAS fora de
        ordem, produziria exatamente isso — e o sintoma é o aluno abrir a tela
        e ver que perdeu Ouro por ter estudado.
        """
        ordem = {f["chave"]: i for i, f in enumerate(reversed(FAIXAS))}
        anterior = -1

        for nivel in range(1, 200):
            posicao = ordem[faixa_do_nivel(nivel)["chave"]]
            self.assertGreaterEqual(posicao, anterior, f"faixa caiu no nível {nivel}")
            anterior = posicao

    def test_todo_nivel_tem_faixa(self):
        for nivel in range(1, 500):
            with self.subTest(nivel=nivel):
                self.assertIn(faixa_do_nivel(nivel)["chave"], {f["chave"] for f in FAIXAS})

    def test_a_proxima_faixa_aponta_para_a_de_cima(self):
        self.assertEqual(faixa_do_nivel(1)["proxima"], "Prata")
        self.assertEqual(faixa_do_nivel(10)["proxima"], "Ouro")
        self.assertEqual(faixa_do_nivel(20)["proxima"], "Platina")

    def test_platina_nao_promete_proxima(self):
        """A tela escreve 'faltam N níveis para X'. Em Platina não há X, e
        inventar um degrau seria mentir para quem chegou no topo."""
        platina = faixa_do_nivel(45)

        self.assertIsNone(platina["proxima"])
        self.assertIsNone(platina["nivel_da_proxima"])

    def test_o_nivel_da_proxima_e_o_limite_dela(self):
        """Senão o 'faltam N níveis' dá um número que não corresponde à
        promoção que de fato acontece."""
        for nivel in (1, 15, 30):
            faixa = faixa_do_nivel(nivel)
            with self.subTest(nivel=nivel):
                # Chegando no nível anunciado, a faixa tem que ser a prometida.
                self.assertEqual(
                    faixa_do_nivel(faixa["nivel_da_proxima"])["nome"], faixa["proxima"]
                )

    def test_nivel_estranho_cai_em_bronze_sem_estourar(self):
        """Não deveria acontecer (nível é 1 + xp//150 e XP nunca é negativo),
        mas uma tela de progresso quebrada é pior que uma faixa errada."""
        for nivel in (0, -5):
            with self.subTest(nivel=nivel):
                self.assertEqual(faixa_do_nivel(nivel)["nome"], "Bronze")

    def test_as_faixas_estao_em_ordem_decrescente(self):
        """`faixa_do_nivel` devolve a primeira que couber, então a ordem da
        constante É a lógica. Fora de ordem, todo mundo viraria Bronze."""
        minimos = [f["nivel_minimo"] for f in FAIXAS]

        self.assertEqual(minimos, sorted(minimos, reverse=True))

    def test_bronze_comeca_no_primeiro_nivel(self):
        """Senão um aluno novo cairia no fallback em vez da faixa de verdade."""
        self.assertEqual(FAIXAS[-1]["nivel_minimo"], 1)


class TestesFaixaNoProgresso(BaseDelta):
    """A faixa tem que chegar junto do progresso — é de lá que a tela lê."""

    def test_aluno_novo_comeca_em_bronze(self):
        progresso = resumo_do_aluno(ALUNO)["progresso"]

        self.assertEqual(progresso["nivel"], 1)
        self.assertEqual(progresso["faixa"]["nome"], "Bronze")

    def test_a_faixa_acompanha_o_nivel_que_veio_no_mesmo_dicionario(self):
        """Faixa e nível calculados do mesmo XP: divergir seria mostrar 'Nível
        30' dentro de um escudo de Bronze."""
        progresso = resumo_do_aluno(ALUNO)["progresso"]

        self.assertEqual(
            progresso["faixa"]["nome"], faixa_do_nivel(progresso["nivel"])["nome"]
        )

    def test_a_faixa_traz_a_chave_que_o_css_usa(self):
        """A tela faz `anel.dataset.faixa = faixa.chave`. Sem a chave, o escudo
        fica sem cor nenhuma."""
        faixa = resumo_do_aluno(ALUNO)["progresso"]["faixa"]

        self.assertIn("chave", faixa)
        self.assertEqual(faixa["chave"], "bronze")



# =========================================================================
# Limite de tentativas no login
#
# Sem limite, um robô testava senhas indefinidamente. O bloqueio é por e-mail
# e temporário (ver o comentário em MAX_FALHAS_LOGIN sobre por que não é
# permanente nem por IP).
# =========================================================================

class TestesLimiteDeLogin(BaseDelta):

    def _errar(self, email, vezes):
        for _ in range(vezes):
            realizar_login(email, "senha-errada")

    def test_senha_certa_bloqueada_depois_do_limite(self):
        """Bloqueado, nem a senha certa entra — senão o robô só precisaria
        continuar tentando até acertar."""
        self._errar(ALUNO, MAX_FALHAS_LOGIN)

        resultado = realizar_login(ALUNO, SENHA)

        self.assertFalse(resultado["sucesso"])
        self.assertNotIn("token", resultado)

    def test_antes_do_limite_a_senha_certa_entra(self):
        """Quem esqueceu erra uma ou duas vezes e não pode ser punido."""
        self._errar(ALUNO, MAX_FALHAS_LOGIN - 1)

        self.assertTrue(realizar_login(ALUNO, SENHA)["sucesso"])

    def test_acertar_zera_o_contador(self):
        self._errar(ALUNO, MAX_FALHAS_LOGIN - 1)
        realizar_login(ALUNO, SENHA)

        self._errar(ALUNO, MAX_FALHAS_LOGIN - 1)

        self.assertTrue(realizar_login(ALUNO, SENHA)["sucesso"])

    def test_o_bloqueio_expira_com_a_janela(self):
        """Temporário de propósito: o mesmo mecanismo deixaria qualquer um
        trancar a conta de um colega, e isso não pode durar para sempre."""
        self._errar(ALUNO, MAX_FALHAS_LOGIN)

        passado = (
            datetime.utcnow() - timedelta(minutes=JANELA_LOGIN_MINUTOS + 1)
        ).isoformat()
        conexao = sqlite3.connect(CAMINHO_DB)
        conexao.execute("UPDATE tentativas_login SET criado_em = ?", (passado,))
        conexao.commit()
        conexao.close()

        self.assertTrue(realizar_login(ALUNO, SENHA)["sucesso"])

    def test_o_bloqueio_de_um_nao_tranca_outro(self):
        self._errar(ALUNO, MAX_FALHAS_LOGIN)

        self.assertTrue(realizar_login(ALUNO_FORA, SENHA)["sucesso"])

    def test_bloqueio_nao_revela_se_a_conta_existe(self):
        """Contando só contas reais, a mensagem de bloqueio apareceria só para
        elas — e viraria um verificador de cadastro."""
        self._errar(ALUNO, MAX_FALHAS_LOGIN)
        self._errar("ninguem@lugar.com", MAX_FALHAS_LOGIN)

        existe = realizar_login(ALUNO, "qualquer")["mensagem"]
        nao_existe = realizar_login("ninguem@lugar.com", "qualquer")["mensagem"]

        self.assertEqual(existe, nao_existe)

    def test_redefinir_a_senha_destranca(self):
        """A mensagem de bloqueio manda para 'Esqueci minha senha'. Quem prova
        pelo e-mail que é dono da conta não deve seguir esperando."""
        self._errar(ALUNO, MAX_FALHAS_LOGIN)

        solicitar_recuperacao(ALUNO)
        conexao = sqlite3.connect(CAMINHO_DB)
        codigo = conexao.execute(
            "SELECT reset_token FROM users WHERE email = ?", (ALUNO,)
        ).fetchone()[0]
        conexao.close()
        redefinir_senha(ALUNO, codigo, "senhanova123")

        self.assertTrue(realizar_login(ALUNO, "senhanova123")["sucesso"])

    def test_email_com_maiuscula_conta_como_o_mesmo(self):
        """Senão bastava variar a caixa para ganhar tentativas novas."""
        self._errar(ALUNO.upper(), MAX_FALHAS_LOGIN)

        self.assertFalse(realizar_login(ALUNO, SENHA)["sucesso"])


class TestesTempoDoLogin(BaseDelta):
    """Conta inexistente não pode responder mais rápido.

    Antes respondia 57x mais rápido (1ms contra 71ms), porque a conferência da
    senha nem rodava. A mensagem era igual, mas o cronômetro dizia quem é aluno.
    """

    def _mediana(self, email, repeticoes=9):
        import time

        tempos = []
        for _ in range(repeticoes):
            inicio = time.perf_counter()
            realizar_login(email, "errada")
            tempos.append(time.perf_counter() - inicio)
            # Limpa para o bloqueio não entrar no meio da medição: bloqueado
            # responde sem conferir senha, e aí os dois ficariam rápidos.
            conexao = sqlite3.connect(CAMINHO_DB)
            conexao.execute("DELETE FROM tentativas_login")
            conexao.commit()
            conexao.close()
        tempos.sort()
        return tempos[len(tempos) // 2]

    def test_conta_inexistente_leva_o_mesmo_tempo(self):
        existe = self._mediana(ALUNO)
        nao_existe = self._mediana("ninguem@lugar.com")

        # Folga larga de propósito: teste de tempo não pode ser frágil. O que
        # importa é pegar a volta do bug, que dava 57x.
        self.assertLess(existe / nao_existe, 3, f"existe={existe:.4f}s nao={nao_existe:.4f}s")



class TestesCors(unittest.TestCase):
    """De quais sites o navegador pode chamar a API.

    Era `*`: qualquer página na internet podia chamar a API a partir do
    navegador de um aluno logado. O tipo de configuração que vai para produção
    por esquecimento, e por isso tem teste.
    """

    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient

        import main

        cls.cliente = TestClient(main.app)

    def _liberado_para(self, origem):
        resposta = self.cliente.options("/login", headers={
            "Origin": origem,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        })
        return resposta.headers.get("access-control-allow-origin") == origem

    def test_o_front_de_desenvolvimento_passa(self):
        self.assertTrue(self._liberado_para("http://127.0.0.1:5500"))
        self.assertTrue(self._liberado_para("http://localhost:5500"))

    def test_site_de_fora_e_barrado(self):
        self.assertFalse(self._liberado_para("https://site-malicioso.com"))

    def test_nao_e_curinga(self):
        """Se alguém voltar para `*`, o cabeçalho sai como '*' e este pega."""
        resposta = self.cliente.options("/login", headers={
            "Origin": "https://qualquer.com",
            "Access-Control-Request-Method": "POST",
        })
        self.assertNotEqual(resposta.headers.get("access-control-allow-origin"), "*")



class TestesChatIsolado(BaseDelta):
    """O chat não pode travar o resto do sistema.

    Medido com um LLM falso de 2s e 48 perguntas simultâneas: com a rota
    síncrona, o login levava 23 segundos, porque as perguntas ocupavam as 40
    threads que o sistema inteiro divide. Com a rota `async` e o orçamento
    próprio da IA, 96ms. A carga de verdade é pesada demais para esta suíte
    (sobe um servidor, leva quase um minuto); o que se trava aqui é o que a
    produz: as rotas que falam com o LLM continuarem `async`, e funcionando.
    """

    def setUp(self):
        super().setUp()

        from fastapi.testclient import TestClient

        import main
        from regras import chat_ia

        self.main = main
        self.cliente = TestClient(main.app)

        # O LLM entra falso pelo ponto único de contato com o Ollama, como no
        # resto da suíte: nada aqui precisa do modelo ligado.
        self._original = chat_ia._chamar_ollama

        def ollama_falso(caminho, corpo):
            if caminho == "/api/embed":
                return {"embeddings": [embedding_falso(str(corpo["input"]))]}
            conteudo = json.dumps({"resposta": "Resposta de teste.", "fontes_usadas": []})
            return {"message": {"content": conteudo}}

        chat_ia._chamar_ollama = ollama_falso
        self.token = self.cliente.post(
            "/login", json={"email": ALUNO, "senha": SENHA}
        ).json()["token"]

    def tearDown(self):
        from regras import chat_ia

        chat_ia._chamar_ollama = self._original
        super().tearDown()

    def test_as_rotas_que_falam_com_o_llm_sao_async(self):
        """Voltar para `def` devolve o chat ao pool comum de 40 threads — e o
        login volta a esperar atrás dele. Nada mais na suíte pegaria isso."""
        import inspect

        for rota in (self.main.perguntar_chat_rota, self.main.criar_material_rota):
            with self.subTest(rota=rota.__name__):
                self.assertTrue(inspect.iscoroutinefunction(rota))

    def test_o_chat_responde_pela_rota(self):
        """A rota nova passa por to_thread e pelo limitador: um argumento
        trocado ali só aparece chamando de verdade."""
        resposta = self.cliente.post(
            "/chat/perguntar",
            json={"turma_id": self.turma_id, "pergunta": "O que é o coração?"},
            headers={"Authorization": f"Bearer {self.token}"},
        )

        self.assertEqual(resposta.status_code, 200, resposta.text)
        self.assertTrue(resposta.json()["sucesso"], resposta.text)

    def test_o_upload_de_pdf_continua_funcionando(self):
        """O upload também virou `async`, com o banco no pool comum e a
        indexação no orçamento da IA. `run_sync` não aceita argumento nomeado,
        e é por isso que o partial existe — este teste pega se ele sumir."""
        token = self.cliente.post(
            "/login", json={"email": PROFESSOR, "senha": SENHA}
        ).json()["token"]

        resposta = self.cliente.post(
            "/materiais",
            json={
                "turma_ids": [self.turma_id],
                "titulo": "Aula de anatomia",
                "tipo": "pdf",
                "rascunho": False,
                "arquivo_base64": PDF_BASE64,
                "arquivo_nome": "aula.pdf",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        self.assertEqual(resposta.status_code, 200, resposta.text)
        self.assertTrue(resposta.json()["sucesso"], resposta.text)



# =========================================================================
# Semestres
# =========================================================================

class TestesFormatoDeSemestre(unittest.TestCase):
    """O semestre era texto livre: o banco tinha `2026.2` e os formulários
    sugeriam `2026/2`. Comparados como texto, eram semestres diferentes, e a
    disciplina sumiria da frente do aluno por causa de um ponto."""

    def test_os_separadores_que_as_pessoas_digitam_viram_um_so(self):
        for entrada in ("2026/2", "2026.2", "2026-2", " 2026 2 ", "2026 / 2"):
            with self.subTest(entrada=entrada):
                self.assertEqual(normalizar_semestre(entrada), "2026/2")

    def test_o_que_nao_e_semestre_e_recusado(self):
        for entrada in ("2026/3", "2026/0", "26/2", "abc", "", None, "2026", "1999/1"):
            with self.subTest(entrada=entrada):
                self.assertIsNone(normalizar_semestre(entrada))

    def test_ordem_e_cronologica_e_nao_alfabetica(self):
        semestres = ["2026/1", "2025/2", "2027/1", "2026/2"]

        self.assertEqual(
            sorted(semestres, key=chave_de_ordem), ["2025/2", "2026/1", "2026/2", "2027/1"]
        )

    def test_calendario_divide_o_ano_no_meio(self):
        from datetime import date

        self.assertEqual(semestre_do_calendario(date(2026, 1, 1)), "2026/1")
        self.assertEqual(semestre_do_calendario(date(2026, 6, 30)), "2026/1")
        self.assertEqual(semestre_do_calendario(date(2026, 7, 1)), "2026/2")
        self.assertEqual(semestre_do_calendario(date(2026, 12, 31)), "2026/2")


class TestesSemestreVigente(BaseDelta):

    def _apagar_configuracao(self):
        conexao = sqlite3.connect(CAMINHO_DB)
        conexao.execute("DELETE FROM configuracoes")
        conexao.commit()
        conexao.close()

    def test_sem_definicao_vale_o_calendario(self):
        self._apagar_configuracao()

        self.assertEqual(semestre_vigente(), semestre_do_calendario())
        self.assertFalse(obter_semestre_vigente()["definido_pela_administracao"])

    def test_a_definicao_do_admin_vence_o_calendario(self):
        definir_semestre_vigente(ADMIN, "2031/1")

        self.assertEqual(semestre_vigente(), "2031/1")
        self.assertTrue(obter_semestre_vigente()["definido_pela_administracao"])

    def test_definir_normaliza_o_formato(self):
        resultado = definir_semestre_vigente(ADMIN, "2027.1")

        self.assertTrue(resultado["sucesso"])
        self.assertEqual(semestre_vigente(), "2027/1")

    def test_semestre_invalido_e_recusado(self):
        self.assertFalse(definir_semestre_vigente(ADMIN, "segundo semestre")["sucesso"])
        self.assertEqual(semestre_vigente(), SEMESTRE_DOS_TESTES)

    def test_so_admin_vira_o_semestre(self):
        self.assertFalse(definir_semestre_vigente(PROFESSOR, "2027/1")["sucesso"])
        self.assertFalse(definir_semestre_vigente(ALUNO, "2027/1")["sucesso"])
        self.assertEqual(semestre_vigente(), SEMESTRE_DOS_TESTES)


class TestesSemestreNaEntrada(BaseDelta):

    def test_disciplina_grava_o_formato_unico(self):
        turma = criar_turma(ADMIN, PROFESSOR, "Anatomia", "2027.1")["turma"]

        self.assertEqual(turma["semestre"], "2027/1")

    def test_disciplina_com_semestre_invalido_e_recusada(self):
        self.assertFalse(criar_turma(ADMIN, PROFESSOR, "Anatomia", "segundo")["sucesso"])

    def test_mesma_disciplina_com_outro_separador_e_duplicata(self):
        """Antes, `2026.2` e `2026/2` passavam como semestres diferentes e o
        mesmo professor ficava com a mesma disciplina duas vezes."""
        criar_turma(ADMIN, PROFESSOR, "Anatomia", "2026/2")

        self.assertFalse(criar_turma(ADMIN, PROFESSOR, "Anatomia", "2026.2")["sucesso"])

    def test_turma_de_alunos_grava_o_formato_unico(self):
        self.assertEqual(criar_coorte(ADMIN, "MED 3A", "2026-2")["coorte"]["semestre"], "2026/2")

    def test_a_migracao_converte_o_que_ja_estava_gravado(self):
        conexao = sqlite3.connect(CAMINHO_DB)
        conexao.execute("UPDATE turmas SET semestre = '2026.2' WHERE id = ?", (self.turma_id,))
        conexao.commit()
        conexao.close()

        configurar_banco(silencioso=True)

        conexao = sqlite3.connect(CAMINHO_DB)
        semestre = conexao.execute(
            "SELECT semestre FROM turmas WHERE id = ?", (self.turma_id,)
        ).fetchone()[0]
        conexao.close()
        self.assertEqual(semestre, "2026/2")


class BaseSemestres(BaseDelta):
    """Cardiologia é do semestre vigente (2026/2); Anatomia é do anterior."""

    def setUp(self):
        super().setUp()
        self.antiga = criar_turma(ADMIN, PROFESSOR, "Anatomia", "2026/1")["turma"]["id"]
        matricular_aluno(ADMIN, ALUNO, self.antiga)

    def material_em(self, turma_id, titulo, rascunho=False):
        return criar_material(
            professor_email=PROFESSOR, turma_id=turma_id, titulo=titulo, tipo="link",
            link_url="https://exemplo.com", rascunho=rascunho,
        )["material_id"]

    def trecho_de_pdf(self, material_id, texto):
        """O texto que o chat de IA já extraiu do PDF. A busca do histórico
        lê daqui em vez de abrir o arquivo de novo."""
        conexao = sqlite3.connect(CAMINHO_DB)
        conexao.execute(
            "INSERT INTO material_chunks (material_id, indice, texto, embedding) VALUES (?, 0, ?, '[]')",
            (material_id, texto),
        )
        conexao.commit()
        conexao.close()


class TestesDisciplinasVigentes(BaseSemestres):

    def test_a_lista_marca_quais_sao_do_semestre(self):
        por_nome = {t["nome"]: t["vigente"] for t in listar_turmas_do_aluno(ALUNO)["turmas"]}

        self.assertEqual(por_nome, {"Cardiologia": True, "Anatomia": False})

    def test_as_do_semestre_vem_primeiro(self):
        """Por ordem alfabética, o seletor do chat abriria em Anatomia — uma
        disciplina do semestre passado."""
        nomes = [t["nome"] for t in listar_turmas_do_aluno(ALUNO)["turmas"]]

        self.assertEqual(nomes[0], "Cardiologia")

    def test_virar_o_semestre_troca_quem_e_vigente(self):
        definir_semestre_vigente(ADMIN, "2027/1")

        vigentes = [t for t in listar_turmas_do_aluno(ALUNO)["turmas"] if t["vigente"]]

        self.assertEqual(vigentes, [])


class TestesXPPorSemestre(BaseSemestres):
    """A faixa premiava tempo de matrícula: somando a vida inteira, veterano
    era Platina para sempre, e quem parasse de estudar continuava lá."""

    def setUp(self):
        super().setUp()
        self.material_antigo = self.material_em(self.antiga, "Ossos do crânio")
        self.material_atual = self.material_em(self.turma_id, "Ciclo cardíaco")

    def test_estudo_do_semestre_passado_nao_conta_no_nivel_de_agora(self):
        from regras.aluno import XP_POR_DIA_ATIVO, XP_POR_MATERIAL_ACESSADO, registrar_acesso_material

        registrar_acesso_material(ALUNO, self.material_antigo)

        progresso = resumo_do_aluno(ALUNO)["progresso"]

        self.assertEqual(progresso["xp"], 0)
        self.assertEqual(progresso["xp_total"], XP_POR_MATERIAL_ACESSADO + XP_POR_DIA_ATIVO)

    def test_estudo_do_semestre_conta(self):
        from regras.aluno import XP_POR_DIA_ATIVO, XP_POR_MATERIAL_ACESSADO, registrar_acesso_material

        registrar_acesso_material(ALUNO, self.material_atual)

        self.assertEqual(
            resumo_do_aluno(ALUNO)["progresso"]["xp"],
            XP_POR_MATERIAL_ACESSADO + XP_POR_DIA_ATIVO,
        )

    def test_o_mesmo_dia_nao_conta_duas_vezes_no_total(self):
        from regras.aluno import XP_POR_DIA_ATIVO, XP_POR_MATERIAL_ACESSADO, registrar_acesso_material

        registrar_acesso_material(ALUNO, self.material_antigo)
        registrar_acesso_material(ALUNO, self.material_atual)

        self.assertEqual(
            resumo_do_aluno(ALUNO)["progresso"]["xp_total"],
            2 * XP_POR_MATERIAL_ACESSADO + XP_POR_DIA_ATIVO,
        )

    def test_virar_o_semestre_recomeca_o_nivel_e_preserva_o_total(self):
        from regras.aluno import registrar_acesso_material

        registrar_acesso_material(ALUNO, self.material_atual)
        antes = resumo_do_aluno(ALUNO)["progresso"]

        definir_semestre_vigente(ADMIN, "2027/1")
        depois = resumo_do_aluno(ALUNO)["progresso"]

        self.assertEqual(depois["xp"], 0)
        self.assertEqual(depois["faixa"]["nome"], "Bronze")
        self.assertEqual(depois["xp_total"], antes["xp_total"])
        self.assertEqual(depois["semestre"], "2027/1")


class TestesHistorico(BaseSemestres):

    def test_mostra_so_semestres_anteriores(self):
        self.material_em(self.antiga, "Ossos do crânio")
        self.material_em(self.turma_id, "Ciclo cardíaco")

        historico = historico_do_aluno(ALUNO)

        self.assertEqual([s["semestre"] for s in historico["semestres"]], ["2026/1"])
        disciplinas = historico["semestres"][0]["disciplinas"]
        self.assertEqual([d["nome"] for d in disciplinas], ["Anatomia"])
        self.assertEqual([m["titulo"] for m in disciplinas[0]["materiais"]], ["Ossos do crânio"])

    def test_rascunho_nao_aparece_nem_no_historico(self):
        self.material_em(self.antiga, "Rascunho esquecido", rascunho=True)

        materiais = historico_do_aluno(ALUNO)["semestres"][0]["disciplinas"][0]["materiais"]

        self.assertEqual(materiais, [])

    def test_aluno_so_ve_o_que_cursou(self):
        """O histórico parte da matrícula, como o resto do sistema."""
        self.material_em(self.antiga, "Ossos do crânio")

        self.assertEqual(historico_do_aluno(ALUNO_FORA)["semestres"], [])

    def test_professor_ve_as_proprias_disciplinas_antigas(self):
        self.material_em(self.antiga, "Ossos do crânio")

        historico = historico_do_professor(PROFESSOR)

        self.assertEqual(historico["semestres"][0]["disciplinas"][0]["nome"], "Anatomia")
        self.assertEqual(historico_do_professor(PROFESSOR2)["semestres"], [])

    def test_busca_pelo_titulo(self):
        self.material_em(self.antiga, "Ossos do crânio")
        self.material_em(self.antiga, "Músculos da face")

        disciplinas = historico_do_aluno(ALUNO, "crânio")["semestres"][0]["disciplinas"]

        self.assertEqual([m["titulo"] for m in disciplinas[0]["materiais"]], ["Ossos do crânio"])

    def test_busca_dentro_do_texto_do_pdf(self):
        """O que o aluno procura para a residência raramente está no título."""
        material = self.material_em(self.antiga, "Aula 7")
        self.trecho_de_pdf(material, "O forame magno permite a passagem da medula oblonga.")

        encontrado = historico_do_aluno(ALUNO, "forame magno")["semestres"][0]["disciplinas"][0]["materiais"][0]

        self.assertEqual(encontrado["titulo"], "Aula 7")
        self.assertIn("forame magno", encontrado["trecho"])

    def test_busca_curta_demais_nao_filtra(self):
        """Duas letras casam com quase todo PDF: não é busca, é listagem lenta."""
        self.material_em(self.antiga, "Ossos do crânio")

        historico = historico_do_aluno(ALUNO, "os")

        self.assertEqual(historico["busca"], "")
        self.assertEqual(len(historico["semestres"][0]["disciplinas"][0]["materiais"]), 1)

    def test_curinga_digitado_e_texto_e_nao_curinga(self):
        """Sem escapar, buscar '%%%' casaria com tudo."""
        self.material_em(self.antiga, "Ossos do crânio")

        self.assertEqual(historico_do_aluno(ALUNO, "%%%")["semestres"], [])

    def test_busca_sem_resultado_nao_devolve_semestre_vazio(self):
        self.material_em(self.antiga, "Ossos do crânio")

        self.assertEqual(historico_do_aluno(ALUNO, "inexistente")["semestres"], [])


class TestesRotasDeSemestre(BaseDelta):

    def setUp(self):
        super().setUp()

        from fastapi.testclient import TestClient

        import main

        self.cliente = TestClient(main.app)

    def _cab(self, email):
        token = self.cliente.post("/login", json={"email": email, "senha": SENHA}).json()["token"]
        return {"Authorization": f"Bearer {token}"}

    def test_todo_perfil_le_o_semestre(self):
        for email in (ADMIN, PROFESSOR, ALUNO):
            with self.subTest(perfil=email):
                resposta = self.cliente.get("/semestre", headers=self._cab(email))
                self.assertEqual(resposta.json()["semestre"], SEMESTRE_DOS_TESTES)

    def test_so_admin_vira_pela_rota(self):
        for email in (PROFESSOR, ALUNO):
            with self.subTest(perfil=email):
                resposta = self.cliente.put(
                    "/admin/semestre", json={"semestre": "2027/1"}, headers=self._cab(email)
                )
                self.assertIn(resposta.status_code, (401, 403))

        resposta = self.cliente.put(
            "/admin/semestre", json={"semestre": "2027/1"}, headers=self._cab(ADMIN)
        )
        self.assertTrue(resposta.json()["sucesso"], resposta.text)

    def test_historico_de_cada_perfil_na_sua_rota(self):
        self.assertTrue(self.cliente.get("/aluno/historico", headers=self._cab(ALUNO)).json()["sucesso"])
        self.assertTrue(self.cliente.get("/historico", headers=self._cab(PROFESSOR)).json()["sucesso"])
        self.assertIn(
            self.cliente.get("/historico", headers=self._cab(ALUNO)).status_code, (401, 403)
        )


# =========================================================================
# Exclusão em cascata
#
# Quando a chave estrangeira passou a ser cobrada, excluir uma disciplina que
# já tinha sido usada começou a falhar: a função apagava material, chat e
# matrícula, mas não atividades, entregas, mensagens, exceções, nem os
# registros de acesso ao material. Os testes antigos excluíam disciplinas
# vazias e não viam.
# =========================================================================

class TestesExclusaoDeDisciplinaUsada(BaseDelta):

    def setUp(self):
        super().setUp()
        from regras.aluno import registrar_acesso_material

        self.material = criar_material(
            professor_email=PROFESSOR, turma_id=self.turma_id, titulo="Aula 1",
            tipo="link", link_url="https://exemplo.com", rascunho=False,
        )["material_id"]
        registrar_acesso_material(ALUNO, self.material)

        self.atividade = criar_atividade_em_turmas(
            PROFESSOR, [self.turma_id], titulo="Relatório", tipo="dissertativa",
            rascunho=False, anexo="opcional",
        )["atividade_ids"][0]
        enviar_entrega(ALUNO, self.atividade, "texto", PDF_BASE64, "relatorio.pdf")
        self.arquivo = obter_arquivo_entrega(
            ALUNO, obter_atividade_do_aluno(ALUNO, self.atividade)["entrega"]["entrega_id"]
        )[0]

        enviar_mensagem(ALUNO, self.turma_id, "Professor, uma dúvida.")

        self.coorte = criar_coorte(ADMIN, "MED 3A", "2026/2")["coorte"]["id"]
        conexao = sqlite3.connect(CAMINHO_DB)
        conexao.execute("UPDATE turmas SET coorte_id = ? WHERE id = ?", (self.coorte, self.turma_id))
        conexao.commit()
        conexao.close()
        matricular_na_coorte(ADMIN, ALUNO, self.coorte)
        criar_excecao(ADMIN, ALUNO, self.turma_id)

    def test_a_disciplina_usada_sai(self):
        resultado = excluir_turma(ADMIN, self.turma_id)

        self.assertTrue(resultado["sucesso"], resultado)

    def test_nao_sobra_nada_apontando_para_ela(self):
        excluir_turma(ADMIN, self.turma_id)

        conexao = sqlite3.connect(CAMINHO_DB)
        conexao.execute("PRAGMA foreign_keys=ON")
        violacoes = conexao.execute("PRAGMA foreign_key_check").fetchall()
        conexao.close()

        self.assertEqual(violacoes, [])

    def test_o_documento_entregue_sai_do_disco(self):
        self.assertTrue(os.path.isfile(self.arquivo))

        excluir_turma(ADMIN, self.turma_id)

        self.assertFalse(os.path.isfile(self.arquivo))

    def test_material_ja_aberto_pode_ser_excluido(self):
        resultado = excluir_material(self.material, PROFESSOR)

        self.assertTrue(resultado["sucesso"], resultado)

    def test_excluir_atividade_leva_o_documento_do_disco(self):
        excluir_atividade(self.atividade, PROFESSOR)

        self.assertFalse(os.path.isfile(self.arquivo))

    def tearDown(self):
        import shutil

        from infra.arquivos import PASTA_ENTREGAS

        shutil.rmtree(PASTA_ENTREGAS, ignore_errors=True)
        super().tearDown()



# =========================================================================
# Ranking
#
# O cuidado que veio do backlog: ranking obrigatório expõe quem está indo mal.
# Então o público é só o topo, a posição de cada um só ele vê, e quem não quer
# aparecer vira "colega que preferiu não aparecer" sem perder a posição.
# =========================================================================

class BaseRanking(BaseDelta):
    """MED 3A com Anatomia; ALUNO e ALUNO_FORA na turma."""

    def setUp(self):
        super().setUp()
        self.coorte = criar_coorte(ADMIN, "MED 3A", SEMESTRE_DOS_TESTES)["coorte"]["id"]
        self.anatomia = criar_turma(
            ADMIN, PROFESSOR, "Anatomia", SEMESTRE_DOS_TESTES, coorte_id=self.coorte
        )["turma"]["id"]
        for aluno in (ALUNO, ALUNO_FORA):
            matricular_na_coorte(ADMIN, aluno, self.coorte)
        self.materiais = [
            criar_material(
                professor_email=PROFESSOR, turma_id=self.anatomia, titulo=f"Aula {i}",
                tipo="link", link_url="https://exemplo.com", rascunho=False,
            )["material_id"]
            for i in range(4)
        ]

    def estudar(self, aluno, quantos):
        """Abre `quantos` materiais hoje: 15 XP cada, mais 25 do dia."""
        from regras.aluno import registrar_acesso_material

        for material in self.materiais[:quantos]:
            registrar_acesso_material(aluno, material)

    def novo_aluno(self, email, nome):
        criar_conta_staff(ADMIN, email, SENHA, "aluno", nome=nome)
        matricular_na_coorte(ADMIN, email, self.coorte)


class TestesRanking(BaseRanking):

    def test_quem_estudou_mais_vem_primeiro(self):
        self.estudar(ALUNO, 3)
        self.estudar(ALUNO_FORA, 1)

        ranking = ranking_da_turma(ALUNO)

        self.assertEqual(ranking["eu"]["posicao"], 1)
        self.assertEqual(ranking_da_turma(ALUNO_FORA)["eu"]["posicao"], 2)
        self.assertEqual(ranking["total"], 2)

    def test_empate_divide_a_posicao(self):
        """Quem fez o mesmo XP não fica atrás por ordem alfabética."""
        self.estudar(ALUNO, 2)
        self.estudar(ALUNO_FORA, 2)

        self.assertEqual(ranking_da_turma(ALUNO)["eu"]["posicao"], 1)
        self.assertEqual(ranking_da_turma(ALUNO_FORA)["eu"]["posicao"], 1)

    def test_o_xp_do_ranking_e_o_mesmo_da_tela_inicial(self):
        """Duas telas mostrando números diferentes para o mesmo aluno é o tipo
        de coisa que faz a pessoa desconfiar do sistema inteiro."""
        self.estudar(ALUNO, 3)

        self.assertEqual(
            ranking_da_turma(ALUNO)["eu"]["xp"], resumo_do_aluno(ALUNO)["progresso"]["xp"]
        )

    def test_aluno_sem_turma_recebe_explicacao_e_nao_erro(self):
        criar_conta_staff(ADMIN, "solto@teste.com", SENHA, "aluno", nome="Solto")

        ranking = ranking_da_turma("solto@teste.com")

        self.assertTrue(ranking["sucesso"])
        self.assertIsNone(ranking["coorte"])

    def test_turma_de_semestre_passado_nao_tem_ranking(self):
        definir_semestre_vigente(ADMIN, "2027/1")

        self.assertIsNone(ranking_da_turma(ALUNO)["coorte"])

    def test_estudo_de_semestre_passado_nao_conta_no_ranking(self):
        """O ranking compara o semestre. Somando a vida inteira, o veterano
        ganharia sempre por tempo de casa."""
        from regras.aluno import registrar_acesso_material

        antiga = criar_turma(ADMIN, PROFESSOR, "Histologia", "2026/1")["turma"]["id"]
        matricular_aluno(ADMIN, ALUNO_FORA, antiga)
        material_antigo = criar_material(
            professor_email=PROFESSOR, turma_id=antiga, titulo="Tecido epitelial",
            tipo="link", link_url="https://exemplo.com", rascunho=False,
        )["material_id"]
        registrar_acesso_material(ALUNO_FORA, material_antigo)
        self.estudar(ALUNO, 1)

        self.assertEqual(ranking_da_turma(ALUNO_FORA)["eu"]["xp"], 0)
        self.assertEqual(ranking_da_turma(ALUNO)["eu"]["posicao"], 1)

    def test_turma_alheia_pedida_pela_url_e_ignorada(self):
        """Trocando o número na URL, dava para ver o ranking de outra turma."""
        outra = criar_coorte(ADMIN, "MED 5B", SEMESTRE_DOS_TESTES)["coorte"]["id"]

        ranking = ranking_da_turma(ALUNO, coorte_id=outra)

        self.assertEqual(ranking["coorte"]["id"], self.coorte)


class TestesPrivacidadeDoRanking(BaseRanking):

    def test_quem_preferiu_nao_aparecer_mantem_a_posicao_sem_o_nome(self):
        self.estudar(ALUNO_FORA, 3)
        self.estudar(ALUNO, 1)
        definir_visibilidade(ALUNO_FORA, aparecer=False)

        primeiro = ranking_da_turma(ALUNO)["topo"][0]

        self.assertEqual(primeiro["posicao"], 1)
        self.assertIsNone(primeiro["nome"])
        self.assertTrue(primeiro["oculto"])

    def test_quem_se_ocultou_ainda_se_ve_pelo_nome(self):
        self.estudar(ALUNO, 2)
        definir_visibilidade(ALUNO, aparecer=False)

        ranking = ranking_da_turma(ALUNO)

        self.assertEqual(ranking["topo"][0]["nome"], "Aluno Um")
        self.assertFalse(ranking["eu"]["aparece"])

    def test_o_fundo_nao_e_exposto(self):
        """Só o topo é público. Com mais alunos que o topo, os de trás não
        aparecem na lista de ninguém."""
        for i in range(TAMANHO_DO_TOPO + 3):
            email = f"colega{i}@teste.com"
            self.novo_aluno(email, f"Colega {i:02d}")
            self.estudar(email, 3 if i < TAMANHO_DO_TOPO else 1)
        self.estudar(ALUNO, 1)

        ranking = ranking_da_turma(ALUNO)

        self.assertEqual(len(ranking["topo"]), TAMANHO_DO_TOPO)
        self.assertNotIn("Aluno Um", [linha["nome"] for linha in ranking["topo"]])
        # Mas ele sabe onde está.
        self.assertGreater(ranking["eu"]["posicao"], TAMANHO_DO_TOPO)

    def test_zero_xp_nao_entra_no_topo(self):
        """Numa turma que ainda não começou, o topo seria uma lista de
        empatados em zero: exposição sem informação nenhuma."""
        self.estudar(ALUNO, 1)

        nomes = [linha["nome"] for linha in ranking_da_turma(ALUNO)["topo"]]

        self.assertEqual(nomes, ["Aluno Um"])

    def test_nenhum_email_ou_id_de_colega_sai_na_resposta(self):
        self.estudar(ALUNO_FORA, 2)
        definir_visibilidade(ALUNO_FORA, aparecer=False)

        texto = json.dumps(ranking_da_turma(ALUNO), ensure_ascii=False)

        self.assertNotIn(ALUNO_FORA, texto)
        self.assertNotIn('"id"', json.dumps(ranking_da_turma(ALUNO)["topo"]))

    def test_voltar_a_aparecer(self):
        definir_visibilidade(ALUNO, aparecer=False)
        definir_visibilidade(ALUNO, aparecer=True)

        self.assertTrue(ranking_da_turma(ALUNO)["eu"]["aparece"])


class TestesEvolucaoNoRanking(BaseRanking):

    def _acesso_antigo(self, aluno_email, material_id, dias_atras):
        conexao = sqlite3.connect(CAMINHO_DB)
        aluno_id = conexao.execute("SELECT id FROM users WHERE email = ?", (aluno_email,)).fetchone()[0]
        quando = (datetime.now(timezone.utc) - timedelta(days=dias_atras)).isoformat()
        conexao.execute(
            "INSERT INTO acessos_material (aluno_id, material_id, criado_em) VALUES (?, ?, ?)",
            (aluno_id, material_id, quando),
        )
        conexao.commit()
        conexao.close()

    def test_quem_estudou_esta_semana_aparece_em_destaque(self):
        self.estudar(ALUNO, 2)

        evoluiu = ranking_da_turma(ALUNO_FORA)["evoluiu"]

        self.assertEqual(evoluiu[0]["nome"], "Aluno Um")

    def test_estudo_antigo_nao_e_evolucao(self):
        self._acesso_antigo(ALUNO, self.materiais[0], DIAS_DA_EVOLUCAO + 2)

        ranking = ranking_da_turma(ALUNO)

        self.assertGreater(ranking["eu"]["xp"], 0)
        self.assertEqual(ranking["eu"]["xp_semana"], 0)

    def test_reabrir_material_antigo_nao_conta_como_estudo_novo(self):
        """Sem isto, bastaria reabrir tudo toda segunda-feira para liderar."""
        from regras.aluno import XP_POR_DIA_ATIVO, registrar_acesso_material

        self._acesso_antigo(ALUNO, self.materiais[0], DIAS_DA_EVOLUCAO + 2)
        registrar_acesso_material(ALUNO, self.materiais[0])

        # Só o dia ativo conta; o material não é novo.
        self.assertEqual(ranking_da_turma(ALUNO)["eu"]["xp_semana"], XP_POR_DIA_ATIVO)

    def test_quem_preferiu_nao_aparecer_fica_fora_do_destaque(self):
        self.estudar(ALUNO, 3)
        definir_visibilidade(ALUNO, aparecer=False)

        self.assertEqual(ranking_da_turma(ALUNO_FORA)["evoluiu"], [])


class TestesRotasDoRanking(BaseRanking):

    def setUp(self):
        super().setUp()

        from fastapi.testclient import TestClient

        import main

        self.cliente = TestClient(main.app)

    def _cab(self, email):
        token = self.cliente.post("/login", json={"email": email, "senha": SENHA}).json()["token"]
        return {"Authorization": f"Bearer {token}"}

    def test_o_aluno_le_o_ranking_e_muda_a_visibilidade(self):
        self.assertTrue(self.cliente.get("/aluno/ranking", headers=self._cab(ALUNO)).json()["sucesso"])

        resposta = self.cliente.put(
            "/aluno/ranking/visibilidade", json={"aparecer": False}, headers=self._cab(ALUNO)
        )

        self.assertFalse(resposta.json()["aparece"])

    def test_professor_nao_acessa_o_ranking(self):
        resposta = self.cliente.get("/aluno/ranking", headers=self._cab(PROFESSOR))

        self.assertIn(resposta.status_code, (401, 403))



# =========================================================================
# Contrato entre front e back
#
# Quebras que nenhum teste de regra pega, porque cada lado está certo sozinho:
# o front chamando uma rota que mudou de nome, ou um script procurando um
# elemento que a página não tem. Leitura estática do código (contrato_front.py).
# =========================================================================

class TestesContratoFrontBack(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import contrato_front
        import main

        cls.contrato = contrato_front
        cls.app = main.app

    def test_o_extrator_enxerga_as_chamadas(self):
        """Se a leitura do JS quebrar e achar zero chamadas, os outros testes
        passariam por não ter o que conferir."""
        self.assertGreater(len(self.contrato.chamadas_do_front()), 80)

    def test_toda_chamada_do_front_tem_rota_com_o_mesmo_verbo(self):
        self.assertEqual(self.contrato.chamadas_sem_rota(self.app), [])

    def test_todo_elemento_que_um_script_procura_existe(self):
        self.assertEqual(self.contrato.ids_ausentes(), [])

    def test_nenhuma_tela_anuncia_como_futuro_o_que_ja_existe(self):
        """O painel do professor passou dias dizendo que mensagens 'ainda não
        existe' com o módulo pronto. Promessa de futuro só vale na página do
        catálogo (em-breve.html), que lê de modulos.js."""
        import glob

        frases = ("ainda não existe", "Ver o que vem", "cartao--indisponivel")
        achados = []
        for pagina in glob.glob(os.path.join(self.contrato.FRONT, "**", "*.html"), recursive=True):
            if pagina.endswith("em-breve.html"):
                continue
            texto = open(pagina, encoding="utf-8").read()
            achados += [f"{os.path.relpath(pagina, self.contrato.FRONT)}: {f}" for f in frases if f in texto]

        self.assertEqual(achados, [])

    def test_todo_link_em_breve_tem_entrada_no_catalogo(self):
        """Link para um módulo que saiu do catálogo abre 'Módulo não
        encontrado' — o sinal de que alguém esqueceu de trocar o menu."""
        import glob
        import re

        catalogo = open(os.path.join(self.contrato.FRONT, "modulos.js"), encoding="utf-8").read()
        chaves = set(re.findall(r'^    "([a-z-]+)": \{', catalogo, re.M))
        orfaos = set()
        for pagina in glob.glob(os.path.join(self.contrato.FRONT, "**", "*.html"), recursive=True):
            texto = open(pagina, encoding="utf-8").read()
            orfaos |= set(re.findall(r"em-breve\.html\?modulo=([a-z-]+)", texto)) - chaves

        self.assertEqual(orfaos, set())

    def test_rotas_sem_uso_no_front_sao_so_as_conhecidas(self):
        """Rota nova sem tela, ou tela que deixou de chamar uma rota, aparece
        aqui. Cada item da lista tem motivo para estar nela."""
        conhecidas = {
            # Do próprio FastAPI; a raiz, que só redireciona para as telas; e a
            # de saúde, que é para o monitoramento e não para a tela.
            "GET /", "GET /saude",
            "GET /docs", "GET /docs/oauth2-redirect", "GET /openapi.json", "GET /redoc",
            # A atividade com gabarito, só para o professor dono. A tela de
            # edição usa os dados da lista, e as questões não são editáveis.
            "GET /atividades/{atividade_id}",
        }

        self.assertEqual(set(self.contrato.rotas_nunca_chamadas(self.app)), conhecidas)



# =========================================================================
# Um semestre inteiro, pelo HTTP
#
# Os testes acima provam cada módulo sozinho. Este prova que eles conversam:
# cada passo é feito por um perfil pela rota, como a tela faria, e o passo
# seguinte confere o efeito do outro lado — a notificação chegou, a nota
# apareceu, o XP subiu, o ranking mudou, o material foi para o histórico.
#
# É um teste só, e longo, de propósito: os passos dependem uns dos outros, e
# o que interessa é descobrir **onde a corrente quebra**. A mensagem de cada
# assert diz em que passo.
# =========================================================================

def pdf_com_texto(texto: str) -> str:
    """Um PDF de verdade, com texto extraível, em base64.

    O PDF vazio dos outros testes não tem página; este passa pela extração do
    pypdf, vira trechos indexados e é encontrado pela busca do chat e pela do
    histórico — a cadeia inteira que um PDF real percorre.
    """
    conteudo = f"BT /F1 12 Tf 72 720 Td ({texto}) Tj ET".encode("latin-1")
    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R"
        b" /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(conteudo)).encode() + b" >>\nstream\n" + conteudo + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    pdf = b"%PDF-1.4\n"
    posicoes = []
    for numero, corpo in enumerate(objetos, start=1):
        posicoes.append(len(pdf))
        pdf += f"{numero} 0 obj\n".encode() + corpo + b"\nendobj\n"
    inicio_xref = len(pdf)
    pdf += f"xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n".encode()
    for posicao in posicoes:
        pdf += f"{posicao:010d} 00000 n \n".encode()
    pdf += f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\nstartxref\n{inicio_xref}\n%%EOF\n".encode()
    return base64.b64encode(pdf).decode()


class TestesSemestreCompleto(BaseDelta):

    def setUp(self):
        super().setUp()

        from fastapi.testclient import TestClient

        import main
        from regras import chat_ia

        # Erro do servidor vira 500 na resposta, como no navegador, em vez de
        # estourar dentro do teste: assim a falha diz em que passo aconteceu.
        self.cliente = TestClient(main.app, raise_server_exceptions=False)
        self._ollama_original = chat_ia._chamar_ollama

        def ollama_falso(caminho, corpo):
            if caminho == "/api/embed":
                return {"embeddings": [embedding_falso(str(corpo["input"]))]}
            # Cita o primeiro material que o servidor ofereceu no schema, como
            # o modelo faria ao responder com base nele.
            titulos = (
                corpo.get("format", {}).get("properties", {}).get("fontes_usadas", {})
                .get("items", {}).get("enum", [])
            )
            resposta = {"resposta": "O forame magno fica na base do crânio.", "fontes_usadas": titulos[:1]}
            return {"message": {"content": json.dumps(resposta)}}

        chat_ia._chamar_ollama = ollama_falso

    def tearDown(self):
        import shutil

        from infra.arquivos import PASTA_ENTREGAS, PASTA_UPLOADS
        from regras import chat_ia

        chat_ia._chamar_ollama = self._ollama_original
        shutil.rmtree(PASTA_ENTREGAS, ignore_errors=True)
        shutil.rmtree(PASTA_UPLOADS, ignore_errors=True)
        super().tearDown()

    # ------------------------------------------------------------ ajudantes

    def entrar(self, email):
        resposta = self.cliente.post("/login", json={"email": email, "senha": SENHA})
        self.assertTrue(resposta.json().get("sucesso"), f"login de {email}: {resposta.text}")
        return {"Authorization": f"Bearer {resposta.json()['token']}"}

    def chamar(self, quem, metodo, caminho, corpo=None, esperado=200):
        resposta = self.cliente.request(metodo, caminho, json=corpo, headers=quem)
        self.assertEqual(
            resposta.status_code, esperado, f"{metodo} {caminho} -> {resposta.status_code}: {resposta.text[:300]}"
        )
        if resposta.headers.get("content-type", "").startswith("application/json"):
            dados = resposta.json()
            if isinstance(dados, dict) and "sucesso" in dados and esperado == 200:
                self.assertTrue(dados["sucesso"], f"{metodo} {caminho}: {dados}")
            return dados
        return resposta

    def tipos_de_notificacao(self, quem):
        return [n["tipo"] for n in self.chamar(quem, "GET", "/notificacoes")["notificacoes"]]

    # ------------------------------------------------------------ o semestre

    def test_um_semestre_inteiro(self):
        admin = self.entrar(ADMIN)
        marina = self.entrar(PROFESSOR)
        renato = self.entrar(PROFESSOR2)
        ana = self.entrar(ALUNO)
        bruno = self.entrar(ALUNO_FORA)

        # 1. O admin monta o semestre: a turma e as duas disciplinas dela.
        self.chamar(admin, "PUT", "/admin/semestre", {"semestre": "2026/2"})
        coorte = self.chamar(admin, "POST", "/admin/coortes", {"nome": "MED 3A", "semestre": "2026/2"})["coorte"]["id"]
        anatomia = self.chamar(admin, "POST", "/admin/turmas", {
            "professor_email": PROFESSOR, "nome": "Anatomia", "semestre": "2026.2", "coorte_id": coorte,
        })["turma"]
        self.assertEqual(anatomia["semestre"], "2026/2", "1: semestre não foi normalizado na entrada")
        anatomia = anatomia["id"]
        fisiologia = self.chamar(admin, "POST", "/admin/turmas", {
            "professor_email": PROFESSOR2, "nome": "Fisiologia", "semestre": "2026/2", "coorte_id": coorte,
        })["turma"]["id"]

        # 2. Alunos entram na turma e caem nas duas disciplinas; Bruno fica
        #    fora de Fisiologia por exceção.
        for email in (ALUNO, ALUNO_FORA):
            self.chamar(admin, "POST", f"/admin/coortes/{coorte}/alunos", {"aluno_email": email})
        self.chamar(admin, "POST", "/admin/excecoes", {"aluno_email": ALUNO_FORA, "turma_id": fisiologia})

        nomes_ana = {t["nome"] for t in self.chamar(ana, "GET", "/aluno/turmas")["turmas"]}
        nomes_bruno = {t["nome"] for t in self.chamar(bruno, "GET", "/aluno/turmas")["turmas"]}
        self.assertTrue({"Anatomia", "Fisiologia"} <= nomes_ana, f"2: Ana devia cursar as duas: {nomes_ana}")
        self.assertIn("Anatomia", nomes_bruno, "2: Bruno devia cursar Anatomia")
        self.assertNotIn("Fisiologia", nomes_bruno, "2: a exceção não tirou Bruno de Fisiologia")
        self.assertIn("matricula", self.tipos_de_notificacao(marina), "2: professora não soube da matrícula")

        # 3. A professora publica um PDF de verdade. Ele é indexado para o chat.
        material = self.chamar(marina, "POST", "/materiais", {
            "turma_ids": [anatomia], "titulo": "Base do cranio", "tipo": "pdf", "rascunho": False,
            "arquivo_base64": pdf_com_texto("O forame magno permite a passagem da medula oblonga."),
            "arquivo_nome": "base-do-cranio.pdf",
        })
        self.assertNotIn("aviso_indexacao", material, f"3: o PDF não foi indexado: {material}")
        material = material["material_id"]
        self.assertIn("material", self.tipos_de_notificacao(ana), "3: aluna não foi avisada do material")

        # 4. A aluna abre o material e pergunta ao assistente sobre ele.
        visiveis = [m["id"] for m in self.chamar(ana, "GET", "/aluno/materiais")["materiais"]]
        self.assertIn(material, visiveis, "4: material publicado não aparece para a aluna")
        arquivo = self.chamar(ana, "GET", f"/aluno/materiais/{material}/arquivo")
        self.assertTrue(arquivo.content.startswith(b"%PDF"), "4: o download não devolveu o PDF")

        resposta_chat = self.chamar(ana, "POST", "/chat/perguntar", {"turma_id": anatomia, "pergunta": "Onde fica o forame magno?"})
        self.assertEqual(resposta_chat["fontes"], ["Base do cranio"], "4: o chat não citou o material indexado")

        # 4b. A aluna guarda o material e anota nele.
        self.chamar(ana, "PUT", f"/aluno/favoritos/{material}")
        self.chamar(ana, "POST", "/aluno/anotacoes", {
            "material_id": material, "texto": "Revisar para a prova.", "trecho": "forame magno",
        })
        visto = next(m for m in self.chamar(ana, "GET", "/aluno/materiais")["materiais"] if m["id"] == material)
        self.assertTrue(visto["favorito"] and visto["total_anotacoes"] == 1,
                        f"4b: a lista de materiais não mostra estrela e anotação: {visto}")

        # 5. A professora propõe duas atividades: uma objetiva e um relatório
        #    com anexo obrigatório.
        prazo = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
        objetiva = self.chamar(marina, "POST", "/atividades", {
            "turma_ids": [anatomia], "titulo": "Quiz do crânio", "tipo": "objetiva", "pontos": 10,
            "rascunho": False, "prazo": prazo,
            "questoes": [{"enunciado": "Por onde passa a medula?", "alternativas": ["Forame oval", "Forame magno"], "correta": 1}],
        })["atividade_ids"][0]
        relatorio = self.chamar(marina, "POST", "/atividades", {
            "turma_ids": [anatomia], "titulo": "Relatório de dissecação", "tipo": "dissertativa",
            "pontos": 10, "rascunho": False, "anexo": "obrigatorio",
        })["atividade_ids"][0]
        self.assertIn("atividade", self.tipos_de_notificacao(ana), "5: aluna não foi avisada da atividade")

        # 6. A aluna entrega as duas. A objetiva se corrige sozinha.
        self.chamar(ana, "POST", f"/aluno/atividades/{objetiva}/entrega", {"respostas": [1]})
        self.chamar(ana, "POST", f"/aluno/atividades/{relatorio}/entrega", {
            "respostas": "", "arquivo_base64": PDF_BASE64, "arquivo_nome": "relatorio.pdf",
        })
        minhas = {a["id"]: a for a in self.chamar(ana, "GET", "/aluno/atividades")["atividades"]}
        self.assertEqual(minhas[objetiva].get("nota"), 10, f"6: objetiva não foi corrigida: {minhas[objetiva]}")

        # 7. A professora vê as entregas, baixa o relatório e corrige.
        entregas = self.chamar(marina, "GET", f"/atividades/{relatorio}/entregas")["entregas"]
        da_ana = next(e for e in entregas if e["aluno_email"] == ALUNO)
        self.assertEqual(da_ana["arquivo_nome"], "relatorio.pdf", "7: professora não vê o anexo")
        baixado = self.chamar(marina, "GET", f"/entregas/{da_ana['entrega_id']}/arquivo")
        self.assertTrue(baixado.content.startswith(b"%PDF"), "7: professora não baixou o relatório")
        self.chamar(renato, "GET", f"/entregas/{da_ana['entrega_id']}/arquivo", esperado=404)
        self.chamar(bruno, "GET", f"/entregas/{da_ana['entrega_id']}/arquivo", esperado=404)

        self.chamar(marina, "POST", f"/entregas/{da_ana['entrega_id']}/correcao", {"nota": 8, "devolutiva": "Bom trabalho."})
        self.assertIn("correcao", self.tipos_de_notificacao(ana), "7: aluna não soube da correção")
        minhas = {a["id"]: a for a in self.chamar(ana, "GET", "/aluno/atividades")["atividades"]}
        self.assertEqual(minhas[relatorio].get("nota"), 8, "7: a nota não chegou à aluna")

        # 7b. A coordenação supervisiona: vê o material e o gabarito, e não
        #     enxerga o que a aluna entregou.
        conteudo = self.chamar(admin, "GET", "/admin/conteudo")
        anatomia_vista = next(d for d in conteudo["disciplinas"] if d["id"] == anatomia)
        self.assertIn("Base do cranio", [m["titulo"] for m in anatomia_vista["materiais"]],
                      "7b: coordenação não vê o material publicado")
        questoes = self.chamar(admin, "GET", f"/admin/conteudo/atividades/{objetiva}")["questoes"]
        self.assertEqual(questoes[0]["correta"], 1, "7b: coordenação não vê o gabarito")
        self.assertNotIn("relatorio.pdf", json.dumps(conteudo), "7b: o anexo da aluna vazou na supervisão")

        # 8. O prazo da objetiva aparece no calendário da professora.
        hoje = datetime.now(timezone.utc)
        dia_do_prazo = datetime.fromisoformat(prazo)
        eventos = self.chamar(marina, "GET", f"/calendario?ano={dia_do_prazo.year}&mes={dia_do_prazo.month}")["eventos"]
        self.assertTrue(any("Quiz do crânio" in json.dumps(e, ensure_ascii=False) for e in eventos),
                        "8: o prazo não apareceu no calendário")

        # 9. Mensagens: a aluna escreve, a professora vê como não lida e responde.
        self.chamar(ana, "POST", "/mensagens", {"turma_id": anatomia, "conteudo": "Professora, e o forame jugular?"})
        conversas = self.chamar(marina, "GET", "/mensagens/conversas")
        self.assertGreaterEqual(conversas["nao_lidas"], 1, "9: a mensagem não chegou como não lida")
        self.chamar(marina, "POST", "/mensagens", {"turma_id": anatomia, "conteudo": "Veremos na próxima aula.", "aluno_email": ALUNO})
        self.assertIn("mensagem", self.tipos_de_notificacao(ana), "9: aluna não soube da resposta")

        # 9b. Avisos: a professora avisa a disciplina com urgência, e a
        #     coordenação avisa a instituição inteira.
        self.chamar(marina, "POST", "/avisos", {
            "titulo": "Prova antecipada", "conteudo": "A prova passa para quarta.",
            "turma_ids": [anatomia], "urgente": True,
        })
        self.assertIn("aviso", self.tipos_de_notificacao(ana), "9b: aluna não foi avisada pelo sino")
        mural = self.chamar(ana, "GET", "/avisos/recebidos")["avisos"]
        self.assertTrue(mural and mural[0]["titulo"] == "Prova antecipada" and mural[0]["em_destaque"],
                        f"9b: aviso urgente não está no topo do mural: {mural}")
        self.chamar(admin, "POST", "/avisos", {"titulo": "Semana acadêmica", "conteudo": "Sem aula na sexta.", "geral": True})
        self.assertIn("Semana acadêmica",
                      [a["titulo"] for a in self.chamar(marina, "GET", "/avisos/recebidos")["avisos"]],
                      "9b: aviso geral não chegou à professora")

        # 10. Desempenho dos dois lados.
        self.chamar(ana, "GET", f"/aluno/desempenho?turma_id={anatomia}")
        self.chamar(marina, "GET", f"/desempenho?turma_id={anatomia}")

        # 11. Denúncia: a aluna reporta, o admin é avisado e trata, a aluna sabe.
        denuncia = self.chamar(ana, "POST", "/denuncias", {"material_id": material, "motivo": "incorreto", "descricao": "Falta a imagem."})
        self.assertIn("denuncia", self.tipos_de_notificacao(admin), "11: admin não soube da denúncia")
        denuncia_id = denuncia.get("denuncia", {}).get("id") or denuncia.get("id")
        if denuncia_id is None:
            denuncia_id = self.chamar(admin, "GET", "/admin/denuncias")["denuncias"][0]["id"]
        self.chamar(admin, "POST", f"/admin/denuncias/{denuncia_id}", {"status": "concluida", "acao": "Imagem incluída."})
        self.assertIn("denuncia", self.tipos_de_notificacao(ana), "11: aluna não soube do desfecho")

        # 12. Progresso e ranking: a aluna estudou mais que o colega.
        progresso = self.chamar(ana, "GET", "/aluno/resumo")["progresso"]
        self.assertGreater(progresso["xp"], 0, "12: XP não subiu com estudo")
        self.assertEqual(progresso["semestre"], "2026/2")
        ranking = self.chamar(ana, "GET", "/aluno/ranking")
        self.assertEqual(ranking["coorte"]["nome"], "MED 3A", "12: ranking na turma errada")
        self.assertEqual(ranking["eu"]["posicao"], 1, f"12: quem estudou devia estar em 1º: {ranking['eu']}")
        self.assertEqual(ranking["eu"]["xp"], progresso["xp"], "12: ranking e tela inicial discordam do XP")

        # 13. O semestre vira.
        self.chamar(admin, "PUT", "/admin/semestre", {"semestre": "2027/1"})

        # 14. A aluna recomeça o nível, mas não perde nada.
        depois = self.chamar(ana, "GET", "/aluno/resumo")
        self.assertEqual(depois["progresso"]["xp"], 0, "14: XP do semestre não recomeçou")
        self.assertEqual(depois["progresso"]["xp_total"], progresso["xp_total"], "14: o XP acumulado se perdeu")
        self.assertEqual(depois["total_turmas"], 0, "14: disciplinas antigas continuam na tela inicial")
        self.assertIsNone(self.chamar(ana, "GET", "/aluno/ranking")["coorte"], "14: ranking da turma antiga continua")
        self.assertFalse(any(t["vigente"] for t in self.chamar(ana, "GET", "/aluno/turmas")["turmas"]))

        # 15. O material foi para o histórico, e a busca acha o texto do PDF.
        historico = self.chamar(ana, "GET", "/aluno/historico")
        self.assertTrue(historico["semestres"], "15: o histórico da aluna está vazio")
        self.assertEqual(historico["semestres"][0]["semestre"], "2026/2", "15: semestre não foi para o histórico")
        achado = self.chamar(ana, "GET", "/aluno/historico?busca=forame%20magno")
        self.assertTrue(achado["semestres"], "15: a busca no texto do PDF não achou nada")
        materiais_achados = [m for d in achado["semestres"][0]["disciplinas"] for m in d["materiais"]]
        self.assertEqual([m["titulo"] for m in materiais_achados], ["Base do cranio"], "15: busca no PDF falhou")
        self.assertIn("forame magno", materiais_achados[0]["trecho"])
        self.assertEqual(self.chamar(bruno, "GET", "/aluno/historico?busca=Fisiologia")["semestres"], [],
                         "15: Bruno vê disciplina que não cursou")

        # 16. O material antigo continua abrindo, e o chat antigo respondendo.
        self.chamar(ana, "GET", f"/aluno/materiais/{material}/arquivo")
        self.chamar(ana, "POST", "/chat/perguntar", {"turma_id": anatomia, "pergunta": "Revisão: o que passa pelo forame magno?"})

        # 16b. Favorito e anotação atravessam a virada do semestre.
        self.assertEqual([f["id"] for f in self.chamar(ana, "GET", "/aluno/favoritos")["favoritos"]], [material],
                         "16b: o favorito sumiu na virada")
        self.assertEqual(len(self.chamar(ana, "GET", "/aluno/anotacoes")["anotacoes"]), 1,
                         "16b: a anotação sumiu na virada")

        # 17. O histórico da professora também tem Anatomia.
        disciplinas_marina = [d["nome"] for s in self.chamar(marina, "GET", "/historico")["semestres"] for d in s["disciplinas"]]
        self.assertIn("Anatomia", disciplinas_marina, "17: histórico da professora vazio")

        # 18. O admin exclui a disciplina antiga, com tudo o que ela tem.
        self.chamar(admin, "DELETE", f"/admin/turmas/{anatomia}")
        conexao = sqlite3.connect(CAMINHO_DB)
        conexao.execute("PRAGMA foreign_keys=ON")
        self.assertEqual(conexao.execute("PRAGMA foreign_key_check").fetchall(), [],
                         "18: a exclusão deixou registro órfão")
        conexao.close()

        # 19. O caderno da aluna sobrevive à disciplina: sem vínculo, com o título.
        anotacoes = self.chamar(ana, "GET", "/aluno/anotacoes")["anotacoes"]
        self.assertEqual(len(anotacoes), 1, "19: a exclusão da disciplina apagou a anotação da aluna")
        self.assertFalse(anotacoes[0]["material_disponivel"])
        self.assertEqual(anotacoes[0]["material_titulo"], "Base do cranio")
        self.assertEqual(self.chamar(ana, "GET", "/aluno/favoritos")["favoritos"], [],
                         "19: sobrou favorito de material que não existe")



# =========================================================================
# Avisos
#
# Uma pessoa escrevendo para outras. Professor escreve para as disciplinas
# dele; administração, para a instituição inteira ou para qualquer disciplina;
# aluno só lê.
# =========================================================================

class BaseAvisos(BaseDelta):
    """Cardiologia (do PROFESSOR) tem ALUNO; Fisiologia (do PROFESSOR2) tem ALUNO_FORA."""

    def setUp(self):
        super().setUp()
        self.fisiologia = criar_turma(ADMIN, PROFESSOR2, "Fisiologia", SEMESTRE_DOS_TESTES)["turma"]["id"]
        matricular_aluno(ADMIN, ALUNO_FORA, self.fisiologia)

    def notificacoes_de(self, email, tipo="aviso"):
        return [n for n in listar_notificacoes(email)["notificacoes"] if n["tipo"] == tipo]

    def titulos_no_mural(self, email):
        return [a["titulo"] for a in listar_avisos_recebidos(email)["avisos"]]


class TestesPublicarAviso(BaseAvisos):

    def test_professor_avisa_a_propria_disciplina(self):
        resultado = publicar_aviso(PROFESSOR, "Prova adiada", "A prova vai para sexta.", [self.turma_id])

        self.assertTrue(resultado["sucesso"], resultado)
        self.assertEqual(self.titulos_no_mural(ALUNO), ["Prova adiada"])
        self.assertEqual(len(self.notificacoes_de(ALUNO)), 1)

    def test_quem_nao_esta_na_disciplina_nao_recebe(self):
        publicar_aviso(PROFESSOR, "Prova adiada", "A prova vai para sexta.", [self.turma_id])

        self.assertEqual(self.titulos_no_mural(ALUNO_FORA), [])
        self.assertEqual(self.notificacoes_de(ALUNO_FORA), [])

    def test_professor_nao_escreve_para_disciplina_alheia(self):
        """Tudo ou nada: com uma disciplina alheia no meio, ninguém recebe —
        envio parcial deixaria o professor sem saber quem foi avisado."""
        resultado = publicar_aviso(PROFESSOR, "Oi", "Texto.", [self.turma_id, self.fisiologia])

        self.assertFalse(resultado["sucesso"])
        self.assertEqual(self.notificacoes_de(ALUNO), [])
        self.assertEqual(listar_avisos_enviados(PROFESSOR)["avisos"], [])

    def test_professor_nao_escreve_para_a_instituicao(self):
        self.assertFalse(publicar_aviso(PROFESSOR, "Oi", "Texto.", geral=True)["sucesso"])

    def test_aluno_nao_escreve_aviso(self):
        self.assertFalse(publicar_aviso(ALUNO, "Oi", "Texto.", [self.turma_id])["sucesso"])

    def test_sem_destino_e_recusado(self):
        self.assertFalse(publicar_aviso(PROFESSOR, "Oi", "Texto.", [])["sucesso"])

    def test_titulo_ou_texto_em_branco_e_recusado(self):
        self.assertFalse(publicar_aviso(PROFESSOR, "  ", "Texto.", [self.turma_id])["sucesso"])
        self.assertFalse(publicar_aviso(PROFESSOR, "Título", "   ", [self.turma_id])["sucesso"])

    def test_aviso_para_a_instituicao_chega_a_todos_menos_ao_autor(self):
        resultado = publicar_aviso(ADMIN, "Feriado", "Não haverá aula na sexta.", geral=True)

        for email in (ALUNO, ALUNO_FORA, PROFESSOR, PROFESSOR2):
            with self.subTest(email=email):
                self.assertIn("Feriado", self.titulos_no_mural(email))
                self.assertEqual(len(self.notificacoes_de(email)), 1)
        self.assertEqual(self.notificacoes_de(ADMIN), [])
        self.assertEqual(resultado["destinatarios"], 4)

    def test_aviso_da_administracao_para_disciplina_chega_tambem_ao_professor(self):
        """O professor precisa saber o que a coordenação disse à turma dele."""
        publicar_aviso(ADMIN, "Sala nova", "Cardiologia muda para a sala 12.", [self.turma_id])

        self.assertIn("Sala nova", self.titulos_no_mural(PROFESSOR))
        self.assertEqual(self.titulos_no_mural(PROFESSOR2), [])
        # O mural tem filtro próprio; o sino, não. Conferir só o mural deixava
        # a notificação do professor se perder sem nenhum teste acusar.
        self.assertEqual(len(self.notificacoes_de(PROFESSOR)), 1)
        self.assertEqual(self.notificacoes_de(PROFESSOR2), [])

    def test_o_proprio_aviso_nao_aparece_como_recebido(self):
        publicar_aviso(PROFESSOR, "Prova adiada", "Texto.", [self.turma_id])

        self.assertEqual(self.titulos_no_mural(PROFESSOR), [])
        # Nem no sino: quem escreveu não precisa ser avisado do que escreveu.
        self.assertEqual(self.notificacoes_de(PROFESSOR), [])
        self.assertEqual([a["titulo"] for a in listar_avisos_enviados(PROFESSOR)["avisos"]], ["Prova adiada"])

    def test_varias_disciplinas_sao_um_aviso_so_no_historico(self):
        segunda = criar_turma(ADMIN, PROFESSOR, "Semiologia", SEMESTRE_DOS_TESTES)["turma"]["id"]
        matricular_aluno(ADMIN, ALUNO, segunda)

        publicar_aviso(PROFESSOR, "Monitoria", "Toda quarta.", [self.turma_id, segunda])

        enviados = listar_avisos_enviados(PROFESSOR)["avisos"]
        self.assertEqual(len(enviados), 1)
        self.assertEqual(enviados[0]["disciplinas"], ["Cardiologia", "Semiologia"])
        # E quem está nas duas é avisado uma vez só.
        self.assertEqual(len(self.notificacoes_de(ALUNO)), 1)


class TestesMuralDeAvisos(BaseAvisos):

    def _envelhecer(self, titulo, dias):
        conexao = sqlite3.connect(CAMINHO_DB)
        quando = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
        conexao.execute("UPDATE avisos SET criado_em = ? WHERE titulo = ?", (quando, titulo))
        conexao.commit()
        conexao.close()

    def test_urgente_recente_vem_primeiro(self):
        publicar_aviso(PROFESSOR, "Urgente de ontem", "Texto.", [self.turma_id], urgente=True)
        self._envelhecer("Urgente de ontem", 1)
        publicar_aviso(PROFESSOR, "Comum de hoje", "Texto.", [self.turma_id])

        self.assertEqual(self.titulos_no_mural(ALUNO), ["Urgente de ontem", "Comum de hoje"])

    def test_urgente_antigo_perde_o_topo(self):
        """Urgente para sempre deixa de ser urgente."""
        publicar_aviso(PROFESSOR, "Urgente antigo", "Texto.", [self.turma_id], urgente=True)
        self._envelhecer("Urgente antigo", DIAS_NO_TOPO + 1)
        publicar_aviso(PROFESSOR, "Comum de hoje", "Texto.", [self.turma_id])

        mural = listar_avisos_recebidos(ALUNO)["avisos"]
        self.assertEqual([a["titulo"] for a in mural], ["Comum de hoje", "Urgente antigo"])
        self.assertFalse(mural[1]["em_destaque"])
        self.assertTrue(mural[1]["urgente"])

    def test_notificacao_de_urgente_diz_que_e_urgente(self):
        publicar_aviso(PROFESSOR, "Prova hoje", "Texto.", [self.turma_id], urgente=True)

        self.assertTrue(self.notificacoes_de(ALUNO)[0]["titulo"].startswith("Urgente"))


class TestesApagarAviso(BaseAvisos):

    def test_autor_apaga_e_sai_do_mural(self):
        aviso = publicar_aviso(PROFESSOR, "Errado", "Texto.", [self.turma_id])["aviso_id"]

        self.assertTrue(excluir_aviso(PROFESSOR, aviso)["sucesso"])
        self.assertEqual(self.titulos_no_mural(ALUNO), [])

    def test_ninguem_alem_do_autor_apaga(self):
        aviso = publicar_aviso(PROFESSOR, "Certo", "Texto.", [self.turma_id])["aviso_id"]

        for email in (PROFESSOR2, ALUNO, ADMIN):
            with self.subTest(email=email):
                self.assertFalse(excluir_aviso(email, aviso)["sucesso"])
        self.assertEqual(self.titulos_no_mural(ALUNO), ["Certo"])

    def test_excluir_a_disciplina_leva_o_aviso_que_era_so_dela(self):
        """Tabela nova apontando para disciplina tem que entrar na exclusão em
        cascata — senão a exclusão volta a falhar pela chave estrangeira."""
        segunda = criar_turma(ADMIN, PROFESSOR, "Semiologia", SEMESTRE_DOS_TESTES)["turma"]["id"]
        publicar_aviso(PROFESSOR, "Só Cardiologia", "Texto.", [self.turma_id])
        publicar_aviso(PROFESSOR, "Nas duas", "Texto.", [self.turma_id, segunda])

        self.assertTrue(excluir_turma(ADMIN, self.turma_id)["sucesso"])

        enviados = {a["titulo"]: a for a in listar_avisos_enviados(PROFESSOR)["avisos"]}
        self.assertNotIn("Só Cardiologia", enviados)
        self.assertEqual(enviados["Nas duas"]["disciplinas"], ["Semiologia"])

        conexao = sqlite3.connect(CAMINHO_DB)
        conexao.execute("PRAGMA foreign_keys=ON")
        self.assertEqual(conexao.execute("PRAGMA foreign_key_check").fetchall(), [])
        conexao.close()


class TestesRotasDeAvisos(BaseAvisos):

    def setUp(self):
        super().setUp()

        from fastapi.testclient import TestClient

        import main

        self.cliente = TestClient(main.app)

    def _cab(self, email):
        token = self.cliente.post("/login", json={"email": email, "senha": SENHA}).json()["token"]
        return {"Authorization": f"Bearer {token}"}

    def test_do_envio_ao_mural_pela_rota(self):
        resposta = self.cliente.post("/avisos", headers=self._cab(PROFESSOR), json={
            "titulo": "Prova adiada", "conteudo": "Sexta.", "turma_ids": [self.turma_id], "urgente": True,
        })
        self.assertTrue(resposta.json()["sucesso"], resposta.text)

        mural = self.cliente.get("/avisos/recebidos", headers=self._cab(ALUNO)).json()["avisos"]
        self.assertEqual(mural[0]["titulo"], "Prova adiada")
        self.assertTrue(mural[0]["em_destaque"])

        enviados = self.cliente.get("/avisos/enviados", headers=self._cab(PROFESSOR)).json()["avisos"]
        apagou = self.cliente.delete(f"/avisos/{enviados[0]['id']}", headers=self._cab(PROFESSOR)).json()
        self.assertTrue(apagou["sucesso"])

    def test_aluno_e_recusado_pela_rota(self):
        resposta = self.cliente.post("/avisos", headers=self._cab(ALUNO), json={
            "titulo": "Oi", "conteudo": "Texto.", "turma_ids": [self.turma_id],
        })
        self.assertFalse(resposta.json()["sucesso"])



# =========================================================================
# Favoritos e anotações
# =========================================================================

class BaseEstudoPessoal(BaseDelta):
    """Um material publicado em Cardiologia, que só ALUNO cursa."""

    def setUp(self):
        super().setUp()
        self.material = criar_material(
            professor_email=PROFESSOR, turma_id=self.turma_id, titulo="Ciclo cardíaco",
            tipo="link", link_url="https://exemplo.com", rascunho=False,
        )["material_id"]
        self.rascunho = criar_material(
            professor_email=PROFESSOR, turma_id=self.turma_id, titulo="Ainda não",
            tipo="link", link_url="https://exemplo.com", rascunho=True,
        )["material_id"]


class TestesFavoritos(BaseEstudoPessoal):

    def test_marcar_e_desmarcar(self):
        self.assertTrue(marcar_favorito(ALUNO, self.material)["sucesso"])
        self.assertEqual([f["titulo"] for f in listar_favoritos(ALUNO)["favoritos"]], ["Ciclo cardíaco"])

        desmarcar_favorito(ALUNO, self.material)

        self.assertEqual(listar_favoritos(ALUNO)["favoritos"], [])

    def test_marcar_duas_vezes_nao_e_erro(self):
        marcar_favorito(ALUNO, self.material)

        self.assertTrue(marcar_favorito(ALUNO, self.material)["sucesso"])
        self.assertEqual(len(listar_favoritos(ALUNO)["favoritos"]), 1)

    def test_a_lista_de_materiais_mostra_a_estrela(self):
        marcar_favorito(ALUNO, self.material)

        material = listar_materiais_do_aluno(ALUNO)["materiais"][0]

        self.assertTrue(material["favorito"])

    def test_nao_favorita_material_que_nao_ve(self):
        """Por id, dava para marcar material de disciplina alheia ou rascunho
        — e o próprio sucesso contaria que ele existe."""
        self.assertFalse(marcar_favorito(ALUNO_FORA, self.material)["sucesso"])
        self.assertFalse(marcar_favorito(ALUNO, self.rascunho)["sucesso"])

    def test_favoritos_valem_entre_semestres(self):
        marcar_favorito(ALUNO, self.material)

        definir_semestre_vigente(ADMIN, "2027/1")

        self.assertEqual(len(listar_favoritos(ALUNO)["favoritos"]), 1)

    def test_material_apagado_leva_o_favorito(self):
        marcar_favorito(ALUNO, self.material)

        self.assertTrue(excluir_material(self.material, PROFESSOR)["sucesso"])
        self.assertEqual(listar_favoritos(ALUNO)["favoritos"], [])

    def test_os_favoritos_sao_de_cada_um(self):
        matricular_aluno(ADMIN, ALUNO_FORA, self.turma_id)
        marcar_favorito(ALUNO, self.material)

        self.assertEqual(listar_favoritos(ALUNO_FORA)["favoritos"], [])


class TestesAnotacoes(BaseEstudoPessoal):

    def test_escrever_editar_e_apagar(self):
        criada = criar_anotacao(ALUNO, self.material, "Revisar a fase isovolumétrica.", "fase de ejeção")
        self.assertTrue(criada["sucesso"], criada)
        anotacao = criada["anotacao"]["id"]

        editar_anotacao(ALUNO, anotacao, "Revisar a fase isovolumétrica e a de ejeção.")
        self.assertEqual(listar_anotacoes(ALUNO)["anotacoes"][0]["texto"],
                         "Revisar a fase isovolumétrica e a de ejeção.")

        self.assertTrue(excluir_anotacao(ALUNO, anotacao)["sucesso"])
        self.assertEqual(listar_anotacoes(ALUNO)["anotacoes"], [])

    def test_a_lista_de_materiais_conta_as_anotacoes(self):
        criar_anotacao(ALUNO, self.material, "Primeira.")
        criar_anotacao(ALUNO, self.material, "Segunda.")

        self.assertEqual(listar_materiais_do_aluno(ALUNO)["materiais"][0]["total_anotacoes"], 2)

    def test_nao_anota_material_que_nao_ve(self):
        self.assertFalse(criar_anotacao(ALUNO_FORA, self.material, "Oi.")["sucesso"])
        self.assertFalse(criar_anotacao(ALUNO, self.rascunho, "Oi.")["sucesso"])

    def test_anotacao_vazia_e_recusada(self):
        self.assertFalse(criar_anotacao(ALUNO, self.material, "   ")["sucesso"])

    def test_anotacao_sobrevive_ao_material_apagado(self):
        """É trabalho do aluno. Perde o vínculo, não o conteúdo."""
        criar_anotacao(ALUNO, self.material, "O que eu entendi da aula.")

        excluir_material(self.material, PROFESSOR)

        anotacao = listar_anotacoes(ALUNO)["anotacoes"][0]
        self.assertEqual(anotacao["texto"], "O que eu entendi da aula.")
        self.assertEqual(anotacao["material_titulo"], "Ciclo cardíaco")
        self.assertFalse(anotacao["material_disponivel"])

    def test_anotacao_sobrevive_a_disciplina_excluida(self):
        criar_anotacao(ALUNO, self.material, "Nota.")
        marcar_favorito(ALUNO, self.material)

        self.assertTrue(excluir_turma(ADMIN, self.turma_id)["sucesso"])

        self.assertEqual(len(listar_anotacoes(ALUNO)["anotacoes"]), 1)
        conexao = sqlite3.connect(CAMINHO_DB)
        conexao.execute("PRAGMA foreign_keys=ON")
        self.assertEqual(conexao.execute("PRAGMA foreign_key_check").fetchall(), [])
        conexao.close()


class TestesPrivacidadeDasAnotacoes(BaseEstudoPessoal):
    """Anotação só é franca se ninguém mais lê."""

    def setUp(self):
        super().setUp()
        matricular_aluno(ADMIN, ALUNO_FORA, self.turma_id)
        self.anotacao = criar_anotacao(ALUNO, self.material, "Não entendi nada desta aula.")["anotacao"]["id"]

    def test_colega_no_mesmo_material_nao_ve(self):
        self.assertEqual(listar_anotacoes(ALUNO_FORA, self.material)["anotacoes"], [])

    def test_colega_nao_edita_nem_apaga(self):
        self.assertFalse(editar_anotacao(ALUNO_FORA, self.anotacao, "Invadido.")["sucesso"])
        self.assertFalse(excluir_anotacao(ALUNO_FORA, self.anotacao)["sucesso"])
        self.assertEqual(listar_anotacoes(ALUNO)["anotacoes"][0]["texto"], "Não entendi nada desta aula.")

    def test_professor_e_admin_nao_tem_rota_para_ler(self):
        from fastapi.testclient import TestClient

        import main

        cliente = TestClient(main.app)
        for email in (PROFESSOR, ADMIN):
            token = cliente.post("/login", json={"email": email, "senha": SENHA}).json()["token"]
            with self.subTest(perfil=email):
                resposta = cliente.get("/aluno/anotacoes", headers={"Authorization": f"Bearer {token}"})
                self.assertIn(resposta.status_code, (401, 403))

    def test_nenhuma_rota_fora_do_aluno_menciona_anotacoes(self):
        """A privacidade é a ausência da rota. Se alguém criar uma rota de
        professor ou de admin com anotações, este teste avisa."""
        import main

        fora_do_aluno = [
            rota.path for rota in main.app.routes
            if "anotac" in rota.path and not rota.path.startswith("/aluno/")
        ]
        self.assertEqual(fora_do_aluno, [])


class TestesRotasDeEstudoPessoal(BaseEstudoPessoal):

    def test_pela_rota(self):
        from fastapi.testclient import TestClient

        import main

        cliente = TestClient(main.app)
        token = cliente.post("/login", json={"email": ALUNO, "senha": SENHA}).json()["token"]
        cab = {"Authorization": f"Bearer {token}"}

        self.assertTrue(cliente.put(f"/aluno/favoritos/{self.material}", headers=cab).json()["favorito"])
        self.assertEqual(len(cliente.get("/aluno/favoritos", headers=cab).json()["favoritos"]), 1)
        self.assertFalse(cliente.delete(f"/aluno/favoritos/{self.material}", headers=cab).json()["favorito"])

        criada = cliente.post("/aluno/anotacoes", headers=cab,
                              json={"material_id": self.material, "texto": "Nota."}).json()
        self.assertTrue(criada["sucesso"], criada)
        anotacao = criada["anotacao"]["id"]
        self.assertTrue(cliente.put(f"/aluno/anotacoes/{anotacao}", headers=cab,
                                    json={"texto": "Nota editada."}).json()["sucesso"])
        self.assertEqual(
            cliente.get(f"/aluno/anotacoes?material_id={self.material}", headers=cab).json()["anotacoes"][0]["texto"],
            "Nota editada.",
        )
        self.assertTrue(cliente.delete(f"/aluno/anotacoes/{anotacao}", headers=cab).json()["sucesso"])



# =========================================================================
# Supervisão de conteúdo
#
# A coordenação vê o que os alunos veem ou vão ver — publicado e agendado —
# e nada que seja trabalho pessoal: rascunho do professor, entrega, anotação,
# conversa com o assistente, mensagem.
# =========================================================================

class BaseSupervisao(BaseDelta):

    def setUp(self):
        super().setUp()
        futuro = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()

        def material(titulo, rascunho=False, data_liberacao=None, arquivo=False):
            campos = dict(
                professor_email=PROFESSOR, turma_id=self.turma_id, titulo=titulo,
                rascunho=rascunho, data_liberacao=data_liberacao,
            )
            if arquivo:
                campos.update(tipo="pdf", arquivo_base64=PDF_BASE64, arquivo_nome=f"{titulo}.pdf")
            else:
                campos.update(tipo="link", link_url="https://exemplo.com")
            return criar_material(**campos)["material_id"]

        self.publicado = material("Publicado", arquivo=True)
        self.agendado = material("Agendado", data_liberacao=futuro)
        self.rascunho = material("Rascunho do professor", rascunho=True, arquivo=True)

        self.quiz = criar_atividade_em_turmas(
            PROFESSOR, [self.turma_id], titulo="Quiz", tipo="objetiva", rascunho=False,
            questoes=[{"enunciado": "Quantas câmaras tem o coração?",
                       "alternativas": ["Duas", "Quatro"], "correta": 1}],
        )["atividade_ids"][0]
        self.atividade_rascunho = criar_atividade_em_turmas(
            PROFESSOR, [self.turma_id], titulo="Ideia ainda crua", tipo="dissertativa", rascunho=True,
        )["atividade_ids"][0]

    def tearDown(self):
        import shutil

        from infra.arquivos import PASTA_UPLOADS

        shutil.rmtree(PASTA_UPLOADS, ignore_errors=True)
        super().tearDown()

    def cardiologia(self, **filtro):
        return next(d for d in visao_do_conteudo(ADMIN, **filtro)["disciplinas"] if d["nome"] == "Cardiologia")


class TestesSupervisaoDeConteudo(BaseSupervisao):

    def test_ve_o_publicado_e_o_agendado(self):
        titulos = {m["titulo"]: m["status"] for m in self.cardiologia()["materiais"]}

        self.assertEqual(titulos, {"Publicado": "publicado", "Agendado": "agendado"})

    def test_nao_ve_rascunho_de_professor(self):
        disciplina = self.cardiologia()

        self.assertNotIn("Rascunho do professor", [m["titulo"] for m in disciplina["materiais"]])
        self.assertNotIn("Ideia ainda crua", [a["titulo"] for a in disciplina["atividades"]])

    def test_abre_a_atividade_com_o_gabarito(self):
        """'A questão 3 está com a resposta errada' é o caso típico de
        conformidade — sem o gabarito, a coordenação não tem como conferir."""
        atividade = atividade_para_supervisao(ADMIN, self.quiz)

        self.assertTrue(atividade["sucesso"])
        self.assertEqual(atividade["questoes"][0]["correta"], 1)

    def test_atividade_em_rascunho_responde_como_inexistente(self):
        self.assertFalse(atividade_para_supervisao(ADMIN, self.atividade_rascunho)["sucesso"])

    def test_baixa_o_arquivo_publicado_e_nao_o_do_rascunho(self):
        self.assertIsNotNone(arquivo_para_supervisao(ADMIN, self.publicado))
        self.assertIsNone(arquivo_para_supervisao(ADMIN, self.rascunho))

    def test_mostra_quantas_denuncias_estao_abertas(self):
        criar_denuncia(ALUNO, self.publicado, "incorreto", "Imagem trocada.")

        publicado = next(m for m in self.cardiologia()["materiais"] if m["titulo"] == "Publicado")

        self.assertEqual(publicado["denuncias_abertas"], 1)

    def test_o_semestre_escolhe_as_disciplinas(self):
        criar_turma(ADMIN, PROFESSOR2, "Anatomia", "2026/1")

        vigente = [d["nome"] for d in visao_do_conteudo(ADMIN)["disciplinas"]]
        anterior = [d["nome"] for d in visao_do_conteudo(ADMIN, semestre="2026.1")["disciplinas"]]

        self.assertEqual(vigente, ["Cardiologia"])
        self.assertEqual(anterior, ["Anatomia"])
        self.assertEqual(visao_do_conteudo(ADMIN)["semestres"][:2], ["2026/2", "2026/1"])

    def test_so_a_administracao(self):
        for email in (PROFESSOR, ALUNO):
            with self.subTest(email=email):
                self.assertFalse(visao_do_conteudo(email)["sucesso"])
                self.assertFalse(atividade_para_supervisao(email, self.quiz)["sucesso"])
                self.assertIsNone(arquivo_para_supervisao(email, self.publicado))


class TestesLimitesDaSupervisao(BaseSupervisao):
    """O que a coordenação não vê não depende de filtro: não existe rota."""

    def test_nenhuma_rota_de_administracao_le_trabalho_pessoal(self):
        import main

        rotas_admin = [rota.path for rota in main.app.routes if rota.path.startswith("/admin/")]
        proibidas = [
            rota for rota in rotas_admin
            if any(p in rota for p in ("entrega", "anotac", "chat", "mensage", "favorit"))
        ]
        self.assertEqual(proibidas, [])

    def test_a_visao_nao_carrega_texto_de_entrega(self):
        """Só a contagem de entregas, número de acompanhamento."""
        enviar_entrega(ALUNO, self.quiz, [1])

        texto = json.dumps(visao_do_conteudo(ADMIN), ensure_ascii=False)

        quiz = next(a for a in self.cardiologia()["atividades"] if a["titulo"] == "Quiz")
        self.assertEqual(quiz["entregues"], 1)
        self.assertNotIn("respostas", texto)
        self.assertNotIn(ALUNO, texto)

    def test_pelas_rotas(self):
        from fastapi.testclient import TestClient

        import main

        cliente = TestClient(main.app)

        def cab(email):
            token = cliente.post("/login", json={"email": email, "senha": SENHA}).json()["token"]
            return {"Authorization": f"Bearer {token}"}

        self.assertTrue(cliente.get("/admin/conteudo", headers=cab(ADMIN)).json()["sucesso"])
        self.assertTrue(cliente.get(f"/admin/conteudo/atividades/{self.quiz}", headers=cab(ADMIN)).json()["sucesso"])
        arquivo = cliente.get(f"/admin/conteudo/materiais/{self.publicado}/arquivo", headers=cab(ADMIN))
        self.assertEqual(arquivo.status_code, 200)
        self.assertEqual(
            cliente.get(f"/admin/conteudo/materiais/{self.rascunho}/arquivo", headers=cab(ADMIN)).status_code, 404
        )
        self.assertIn(cliente.get("/admin/conteudo", headers=cab(PROFESSOR)).status_code, (401, 403))



# =========================================================================
# E-mail
#
# Um servidor SMTP de verdade, mínimo, sobe dentro do teste: o smtplib fala o
# protocolo inteiro com ele. Um dublê da biblioteca provaria só que o código
# chama a função; este prova que a mensagem sai e chega.
# =========================================================================

class ServidorSmtpDeTeste:
    """SMTP mínimo, sem TLS: guarda as mensagens recebidas em `caixa`."""

    def __init__(self, demora_no_envio=0.0):
        import socket
        import threading

        self.caixa = []
        self.demora = demora_no_envio
        self._socket = socket.socket()
        self._socket.bind(("127.0.0.1", 0))
        self._socket.listen()
        self.porta = self._socket.getsockname()[1]
        self._ativo = True
        threading.Thread(target=self._atender, daemon=True).start()

    def _atender(self):
        import time

        while self._ativo:
            try:
                conexao, _ = self._socket.accept()
            except OSError:
                return
            arquivo = conexao.makefile("rwb")

            def responder(linha):
                arquivo.write(linha.encode() + b"\r\n")
                arquivo.flush()

            responder("220 teste")
            dados = None
            while True:
                linha = arquivo.readline()
                if not linha:
                    break
                comando = linha.decode(errors="replace").strip()
                if dados is not None:
                    if comando == ".":
                        time.sleep(self.demora)
                        self.caixa.append("\n".join(dados))
                        dados = None
                        responder("250 ok")
                    else:
                        dados.append(comando)
                    continue
                verbo = comando.split(" ")[0].upper()
                if verbo == "EHLO":
                    responder("250 teste")
                elif verbo == "DATA":
                    dados = []
                    responder("354 pode mandar")
                elif verbo == "QUIT":
                    responder("221 tchau")
                    break
                else:
                    responder("250 ok")
            conexao.close()

    def parar(self):
        self._ativo = False
        self._socket.close()


class TestesEmail(BaseDelta):

    def setUp(self):
        super().setUp()
        self._ambiente = {k: v for k, v in os.environ.items() if k.startswith("DELTACARE_SMTP")}

    def tearDown(self):
        for chave in [k for k in os.environ if k.startswith("DELTACARE_SMTP")]:
            del os.environ[chave]
        os.environ.update(self._ambiente)
        super().tearDown()

    def configurar(self, servidor=None, porta=None):
        os.environ["DELTACARE_SMTP_HOST"] = "127.0.0.1"
        os.environ["DELTACARE_SMTP_PORTA"] = str(porta if porta is not None else servidor.porta)
        os.environ["DELTACARE_SMTP_SEGURANCA"] = "nenhuma"
        os.environ["DELTACARE_SMTP_REMETENTE"] = "Delta Care <nao-responda@teste.com>"

    def codigo_de(self, email):
        conexao = sqlite3.connect(CAMINHO_DB)
        codigo = conexao.execute("SELECT reset_token FROM users WHERE email = ?", (email,)).fetchone()[0]
        conexao.close()
        return codigo

    def esperar_caixa(self, servidor, quantas=1, limite=5.0):
        import time

        inicio = time.time()
        while len(servidor.caixa) < quantas and time.time() - inicio < limite:
            time.sleep(0.02)

    def test_sem_servidor_configurado_nao_envia_nem_quebra(self):
        from infra.email import enviar_email

        self.assertFalse(enviar_email("a@b.com", "Assunto", "Texto"))

    def test_a_mensagem_sai_e_chega(self):
        from infra.email import enviar_email

        servidor = ServidorSmtpDeTeste()
        self.configurar(servidor)
        try:
            self.assertTrue(enviar_email("aluno@med.com", "Teste de envio", "Corpo da mensagem."))
        finally:
            servidor.parar()

        recebida = servidor.caixa[0]
        self.assertIn("To: aluno@med.com", recebida)
        self.assertIn("Subject: Teste de envio", recebida)
        self.assertIn("Corpo da mensagem.", recebida)

    def test_o_codigo_de_recuperacao_chega_por_email(self):
        servidor = ServidorSmtpDeTeste()
        self.configurar(servidor)
        try:
            solicitar_recuperacao(ALUNO)
            self.esperar_caixa(servidor)
        finally:
            servidor.parar()

        self.assertEqual(len(servidor.caixa), 1)
        self.assertIn(f"To: {ALUNO}", servidor.caixa[0])
        self.assertIn(self.codigo_de(ALUNO), servidor.caixa[0])

    def test_conta_inexistente_nao_recebe_nada(self):
        import time

        servidor = ServidorSmtpDeTeste()
        self.configurar(servidor)
        try:
            solicitar_recuperacao("ninguem@lugar.com")
            time.sleep(0.3)
        finally:
            servidor.parar()

        self.assertEqual(servidor.caixa, [])

    def test_servidor_de_email_fora_do_ar_nao_derruba_a_rota(self):
        """A resposta é a mesma: a falha do e-mail não pode virar erro na tela
        nem uma resposta diferente que conte se a conta existe."""
        import socket

        livre = socket.socket()
        livre.bind(("127.0.0.1", 0))
        porta_fechada = livre.getsockname()[1]
        livre.close()
        self.configurar(porta=porta_fechada)

        from infra.email import enviar_email

        self.assertFalse(enviar_email("a@b.com", "Assunto", "Texto"))
        self.assertEqual(
            solicitar_recuperacao(ALUNO)["mensagem"],
            solicitar_recuperacao("ninguem@lugar.com")["mensagem"],
        )

    def test_a_falha_de_envio_nao_escreve_o_codigo_no_log(self):
        """Log é lido por mais gente que o dono da conta."""
        import contextlib
        import io

        from infra.email import enviar_email

        self.configurar(porta=1)
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            enviar_email("a@b.com", "Código", "Seu código é 482913")

        self.assertNotIn("482913", saida.getvalue())

    def test_servidor_lento_nao_revela_quem_tem_conta(self):
        """Enviar só acontece para conta real. Se a rota esperasse o envio,
        conta real responderia segundos mais devagar que a inexistente."""
        import time

        servidor = ServidorSmtpDeTeste(demora_no_envio=1.5)
        self.configurar(servidor)
        try:
            inicio = time.perf_counter()
            solicitar_recuperacao(ALUNO)
            com_conta = time.perf_counter() - inicio

            inicio = time.perf_counter()
            solicitar_recuperacao("ninguem@lugar.com")
            sem_conta = time.perf_counter() - inicio

            self.esperar_caixa(servidor)
        finally:
            servidor.parar()

        self.assertLess(com_conta, 0.5, f"esperou o envio: {com_conta:.2f}s")
        self.assertLess(abs(com_conta - sem_conta), 0.5)
        self.assertEqual(len(servidor.caixa), 1, "e o e-mail chegou mesmo assim")



# =========================================================================
# Implantação: backup e as telas servidas pela API
# =========================================================================

class TestesBackup(BaseDelta):

    def setUp(self):
        super().setUp()
        import tempfile

        self.destino = tempfile.mkdtemp(prefix="deltacare_backup_teste_")

    def tearDown(self):
        import shutil

        shutil.rmtree(self.destino, ignore_errors=True)
        super().tearDown()

    def test_a_copia_abre_e_tem_os_dados(self):
        from backup import fazer_backup

        pasta = fazer_backup(self.destino, manter=5)

        copia = sqlite3.connect(os.path.join(pasta, "deltacare.db"))
        emails = {linha[0] for linha in copia.execute("SELECT email FROM users")}
        copia.close()
        self.assertIn(ALUNO, emails)

    def test_pega_o_que_ainda_esta_so_no_wal(self):
        """No modo WAL, o que acabou de ser gravado pode não estar no .db
        ainda. Copiar o arquivo perderia; a API de backup do SQLite não."""
        from backup import fazer_backup

        conexao = sqlite3.connect(CAMINHO_DB)
        conexao.execute("PRAGMA wal_autocheckpoint=0")
        conexao.execute(
            "INSERT INTO users (email, senha, tipo, nome) VALUES ('recente@teste.com', 'x', 'aluno', 'Recente')"
        )
        conexao.commit()

        pasta = fazer_backup(self.destino, manter=5)
        conexao.close()

        copia = sqlite3.connect(os.path.join(pasta, "deltacare.db"))
        achado = copia.execute("SELECT 1 FROM users WHERE email = 'recente@teste.com'").fetchone()
        copia.close()
        self.assertIsNotNone(achado)

    def test_leva_os_arquivos_enviados(self):
        from backup import fazer_backup
        from infra.arquivos import PASTA_ENTREGAS

        os.makedirs(PASTA_ENTREGAS, exist_ok=True)
        with open(os.path.join(PASTA_ENTREGAS, "trabalho.pdf"), "wb") as arquivo:
            arquivo.write(b"%PDF-1.4 trabalho")

        pasta = fazer_backup(self.destino, manter=5)

        self.assertTrue(os.path.isfile(os.path.join(pasta, "uploads", "entregas", "trabalho.pdf")))

    def test_guarda_so_os_mais_recentes(self):
        import time

        from backup import fazer_backup

        for _ in range(4):
            fazer_backup(self.destino, manter=2)
            time.sleep(1.05)  # o nome da pasta tem precisão de segundo

        self.assertEqual(len(os.listdir(self.destino)), 2)


class TestesTelasServidasPelaApi(unittest.TestCase):
    """Em produção a API entrega as telas em /app/: mesma origem, sem CORS."""

    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient

        import main

        cls.cliente = TestClient(main.app)

    def test_a_raiz_leva_as_telas(self):
        resposta = self.cliente.get("/", follow_redirects=False)

        self.assertIn(resposta.status_code, (302, 307))
        self.assertEqual(resposta.headers["location"], "/app/index.html")

    def test_as_telas_abrem(self):
        for caminho in ("/app/index.html", "/app/aluno/inicio.html", "/app/config.js", "/app/style_dashboard.css"):
            with self.subTest(caminho=caminho):
                self.assertEqual(self.cliente.get(caminho).status_code, 200)

    def test_nao_sai_da_pasta_das_telas(self):
        """Só frontend/ é servido. Banco, código do servidor e uploads não."""
        for caminho in ("/app/../backend/main.py", "/app/%2e%2e/backend/main.py",
                        "/app/..%2fbackend%2fdeltacare.db", "/app/../uploads/"):
            with self.subTest(caminho=caminho):
                self.assertEqual(self.cliente.get(caminho).status_code, 404)

    def test_monitoramento(self):
        self.assertEqual(self.cliente.get("/saude").json(), {"status": "ok"})



class TestesPrimeiroAdmin(unittest.TestCase):
    """Num servidor novo, a primeira conta de confiança nasce por aqui — e não
    pelo seed, que cria contas com a senha de demonstração."""

    def setUp(self):
        for extra in ("", "-wal", "-shm"):
            if os.path.exists(CAMINHO_DB + extra):
                os.remove(CAMINHO_DB + extra)

    tearDown = setUp

    def test_cria_o_primeiro_e_ele_entra(self):
        from criar_admin import criar_primeiro_admin

        resultado = criar_primeiro_admin("Coord@Med.com", "Coordenação", "senha-forte-123")

        self.assertTrue(resultado["sucesso"], resultado)
        login = realizar_login("coord@med.com", "senha-forte-123")
        self.assertTrue(login["sucesso"])
        self.assertEqual(login["tipo"], "adm")

    def test_recusa_se_ja_existe_administracao(self):
        """Senão o script viraria um jeito de ganhar acesso total sem ninguém saber."""
        from criar_admin import criar_primeiro_admin

        criar_primeiro_admin("coord@med.com", "Coordenação", "senha-forte-123")

        self.assertFalse(criar_primeiro_admin("outro@med.com", "Outro", "senha-forte-456")["sucesso"])

    def test_senha_curta_e_recusada(self):
        from criar_admin import criar_primeiro_admin

        self.assertFalse(criar_primeiro_admin("coord@med.com", "Coordenação", "curta")["sucesso"])


class TestesConexaoDaRequisicao(BaseDelta):
    """Uma rota que quebra no meio não pode deixar o banco travado.

    Antes do FecharConexoesDaRequisicao, a conexão de uma rota que levantou
    exceção depois de um UPDATE ficava presa ao rastro do erro, com a trava de
    escrita na mão, e a escrita seguinte de qualquer usuário falhava com
    "database is locked".
    """

    def setUp(self):
        super().setUp()
        import gc

        from fastapi.testclient import TestClient

        import main

        self.main = main
        self.original = main.definir_visibilidade
        # O coletor de ciclos roda quando quer; desligado, o teste não depende
        # da sorte de ele passar entre a rota e a verificação.
        gc.disable()
        main.app.dependency_overrides[main.usuario_aluno] = lambda: {"email": ALUNO, "tipo": "aluno"}
        self.cliente = TestClient(main.app, raise_server_exceptions=False)

    def tearDown(self):
        import gc

        gc.enable()
        self.main.definir_visibilidade = self.original
        self.main.app.dependency_overrides.clear()
        super().tearDown()

    def _trocar_regra(self, regra):
        self.main.definir_visibilidade = regra
        return self.cliente.put("/aluno/ranking/visibilidade", json={"aparecer": False})

    def test_excecao_no_meio_da_escrita_nao_trava_o_banco(self):
        from infra.database import abrir_conexao

        def quebra_no_meio(email, aparecer):
            conexao = abrir_conexao()
            conexao.execute("UPDATE users SET nome = 'meio do caminho' WHERE email = ?", (ALUNO,))
            raise ValueError("falha depois do UPDATE, antes do commit")

        self.assertEqual(self._trocar_regra(quebra_no_meio).status_code, 500)

        # Timeout curto: com a trava presa, isto esperaria e falharia.
        outra = sqlite3.connect(CAMINHO_DB, timeout=0.5)
        try:
            nome = outra.execute("SELECT nome FROM users WHERE email = ?", (ALUNO,)).fetchone()[0]
            outra.execute("UPDATE users SET nome = 'Aluno Um' WHERE email = ?", (ALUNO,))
            outra.commit()
        finally:
            outra.close()

        # E a escrita pela metade foi descartada, não gravada.
        self.assertEqual(nome, "Aluno Um")

    def test_conexao_esquecida_aberta_e_fechada_ao_fim(self):
        from infra.database import abrir_conexao

        esquecidas = []

        def esquece_aberta(email, aparecer):
            esquecidas.append(abrir_conexao())
            return {"sucesso": True}

        self.assertEqual(self._trocar_regra(esquece_aberta).status_code, 200)

        with self.assertRaises(sqlite3.ProgrammingError):
            esquecidas[0].execute("SELECT 1")


class TestesSeedDeDemonstracao(unittest.TestCase):
    """O seed é o que aparece na apresentação. Se uma função mudar de
    assinatura ou passar a recusar alguma coisa, ele não quebra: as regras
    devolvem `sucesso: False` e o seed segue em frente — e a tela abre vazia
    na frente de quem está assistindo.

    Por isso o teste confere o resultado **pelo que as telas mostram**, e não
    pelo que o seed imprimiu. Roda sem o Ollama (a indexação é simulada fora
    do ar, como numa máquina sem ele).
    """

    @classmethod
    def setUpClass(cls):
        import contextlib
        import io
        from unittest import mock

        for extra in ("", "-wal", "-shm"):
            if os.path.exists(CAMINHO_DB + extra):
                os.remove(CAMINHO_DB + extra)

        import seed_demo

        def ollama_fora(material_id, *args, **kwargs):
            raise RuntimeError("Ollama fora do ar")

        with mock.patch("regras.chat_ia.indexar_material", ollama_fora), \
                contextlib.redirect_stdout(io.StringIO()):
            seed_demo.main()
            cls.contagem_primeira = cls._contar()
            # Rodar de novo não pode duplicar nada: o README promete.
            seed_demo.main()
            cls.contagem_segunda = cls._contar()

    @classmethod
    def tearDownClass(cls):
        for extra in ("", "-wal", "-shm"):
            if os.path.exists(CAMINHO_DB + extra):
                os.remove(CAMINHO_DB + extra)

    @staticmethod
    def _contar():
        conexao = sqlite3.connect(CAMINHO_DB)
        tabelas = ("users", "coortes", "turmas", "matriculas", "materiais", "atividades",
                   "entregas", "acessos_material", "mensagens", "avisos", "denuncias",
                   "favoritos", "anotacoes", "solicitacoes_privacidade")
        contagem = {t: conexao.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tabelas}
        conexao.close()
        return contagem

    def test_rodar_de_novo_nao_duplica(self):
        self.assertEqual(self.contagem_primeira, self.contagem_segunda)

    def test_turma_de_alunos_com_a_excecao(self):
        conexao = sqlite3.connect(CAMINHO_DB)
        por_disciplina = dict(conexao.execute(
            "SELECT t.nome, COUNT(m.aluno_id) FROM turmas t"
            " LEFT JOIN matriculas m ON m.turma_id = t.id GROUP BY t.id"
        ).fetchall())
        conexao.close()

        self.assertEqual(
            por_disciplina, {"Cardiologia I": 8, "Anatomia": 8, "Fisiologia": 7, "Histologia": 3}
        )

    def test_professor_tem_o_que_corrigir_e_uma_mensagem_nova(self):
        from regras.mensagens import listar_conversas

        atividades = listar_atividades("professor@deltacare.com")["atividades"]
        conversas = listar_conversas("professor@deltacare.com")["conversas"]

        self.assertEqual(sum(a["a_corrigir"] for a in atividades), 1)
        self.assertEqual([c["titulo"] for c in conversas if c["nao_lidas"]], ["Ana Beatriz Rocha"])

    def test_ranking_com_a_turma_toda_e_quem_pediu_para_sair_fora(self):
        from regras.ranking import ranking_da_turma

        ranking = ranking_da_turma("aluno@deltacare.com")

        self.assertEqual(ranking["total"], 8)
        self.assertEqual(ranking["eu"]["posicao"], 1)
        self.assertNotIn("Júlia Fernandes", [linha["nome"] for linha in ranking["topo"]])

    def test_administracao_tem_um_pedido_de_privacidade_esperando(self):
        from regras.privacidade import listar_solicitacoes

        pendentes = listar_solicitacoes("adm@deltacare.com", "pendente")["solicitacoes"]

        self.assertEqual([p["aluno"]["nome"] for p in pendentes], ["Rafael Moreira"])

    def test_aluna_ve_avisos_e_o_semestre_anterior(self):
        from regras.avisos import listar_avisos_recebidos
        from regras.semestres import historico_do_aluno

        avisos = listar_avisos_recebidos("aluno@deltacare.com")["avisos"]
        historico = historico_do_aluno("aluno@deltacare.com")["semestres"]

        self.assertEqual({a["titulo"] for a in avisos}, {"Prova antecipada", "Semana acadêmica"})
        self.assertEqual(
            [d["nome"] for s in historico for d in s["disciplinas"]], ["Histologia"]
        )


# =========================================================================
# Privacidade (LGPD) — regras/privacidade.py
#
# As decisões da instituição: cópia dos dados na hora; correção e exclusão
# passam pela administração; exclusão é desativação imediata e anonimização
# 45 dias depois, reversível até lá.
# =========================================================================

class BasePrivacidade(BaseDelta):

    def setUp(self):
        super().setUp()
        from regras.anotacoes import criar_anotacao
        from regras.favoritos import marcar_favorito

        material_id = self.criar_material_simples("Ciclo cardíaco")["material_id"]
        self.material_id = material_id
        marcar_favorito(ALUNO, material_id)
        criar_anotacao(ALUNO, material_id, "Revisar a fase isovolumétrica.")
        enviar_mensagem(ALUNO, self.turma_id, "Professor, a prova cobre valvopatias?")

        atividade = criar_atividade_em_turmas(
            PROFESSOR, [self.turma_id], titulo="Quiz de sopros", tipo="objetiva", rascunho=False,
            questoes=[{"enunciado": "Sopro sistólico em foco mitral sugere?",
                       "alternativas": ["Insuficiência mitral", "Estenose aórtica"], "correta": 0}],
        )
        enviar_entrega(ALUNO, atividade["atividade_ids"][0], [0])

        conexao = sqlite3.connect(CAMINHO_DB)
        aluno_id = conexao.execute("SELECT id FROM users WHERE email = ?", (ALUNO,)).fetchone()[0]
        self.aluno_id = aluno_id
        # O chat de verdade precisa do Ollama; a linha é o que importa aqui.
        conexao.execute(
            "INSERT INTO chat_mensagens (aluno_id, turma_id, papel, conteudo, criado_em)"
            " VALUES (?, ?, 'user', 'Qual a dose de ataque?', '2026-09-01T10:00:00+00:00')",
            (aluno_id, self.turma_id),
        )
        conexao.commit()
        conexao.close()

    def _contar(self, sql, *parametros):
        conexao = sqlite3.connect(CAMINHO_DB)
        valor = conexao.execute(sql, parametros).fetchone()[0]
        conexao.close()
        return valor

    def _pedir_exclusao_aprovada(self):
        from regras.privacidade import decidir, solicitar

        pedido = solicitar(ALUNO, "exclusao", motivo="Transferência para outra faculdade.")
        self.assertTrue(pedido["sucesso"], pedido)
        self.assertTrue(decidir(ADMIN, pedido["id"], True)["sucesso"])
        return pedido["id"]


class TestesExportacao(BasePrivacidade):

    def test_copia_tem_os_dados_do_aluno_e_nada_de_senha(self):
        from regras.privacidade import exportar_dados

        dados = exportar_dados(ALUNO)["dados"]
        texto = json.dumps(dados, ensure_ascii=False)

        self.assertEqual(dados["titular"]["email"], ALUNO)
        self.assertEqual(dados["anotacoes"][0]["texto"], "Revisar a fase isovolumétrica.")
        self.assertEqual(dados["favoritos"][0]["material"], "Ciclo cardíaco")
        self.assertEqual(dados["entregas"][0]["nota"], 10)
        self.assertEqual(dados["entregas"][0]["respostas"], [0])
        self.assertEqual(dados["mensagens_com_professores"][0]["autor"], "você")
        self.assertEqual(dados["conversas_com_o_assistente"][0]["conteudo"], "Qual a dose de ataque?")
        self.assertEqual(dados["conversas_com_o_assistente"][0]["autor"], "você")
        self.assertNotIn("pbkdf2", texto.lower())
        self.assertNotIn("senha", dados["titular"])

    def test_copia_nao_traz_dado_de_outro_aluno(self):
        """O colega tem de tudo numa disciplina que só ele cursa. Na mesma
        disciplina do titular, um vazamento da lista de disciplinas passaria
        despercebido: o nome seria o mesmo."""
        from regras.anotacoes import criar_anotacao
        from regras.favoritos import marcar_favorito
        from regras.privacidade import exportar_dados

        neuro = criar_turma(ADMIN, PROFESSOR2, "Neurologia", "2026.2")["turma"]["id"]
        matricular_aluno(ADMIN, ALUNO_FORA, neuro)
        material = self.criar_material_simples("Vias motoras", professor=PROFESSOR2, turma_id=neuro)["material_id"]
        marcar_favorito(ALUNO_FORA, material)
        registrar_acesso_material(ALUNO_FORA, material)
        criar_anotacao(ALUNO_FORA, material, "Anotação particular do colega.")
        enviar_mensagem(ALUNO_FORA, neuro, "Mensagem particular do colega.")
        atividade = criar_atividade_em_turmas(
            PROFESSOR2, [neuro], titulo="Quiz de reflexos", tipo="objetiva", rascunho=False,
            questoes=[{"enunciado": "Reflexo patelar?", "alternativas": ["L4", "S1"], "correta": 0}],
        )
        enviar_entrega(ALUNO_FORA, atividade["atividade_ids"][0], [0])
        criar_denuncia(ALUNO_FORA, material, "outro", "Denúncia particular do colega.")
        matricular_na_coorte(ADMIN, ALUNO_FORA, criar_coorte(ADMIN, "MED 5B", SEMESTRE_DOS_TESTES)["coorte"]["id"])
        from regras.privacidade import solicitar

        solicitar(ALUNO_FORA, "exclusao", motivo="Pedido particular do colega.")
        conexao = sqlite3.connect(CAMINHO_DB)
        colega_id = conexao.execute("SELECT id FROM users WHERE email = ?", (ALUNO_FORA,)).fetchone()[0]
        conexao.execute(
            "INSERT INTO chat_mensagens (aluno_id, turma_id, papel, conteudo, criado_em)"
            " VALUES (?, ?, 'user', 'Pergunta particular do colega.', '2026-09-01T10:00:00+00:00')",
            (colega_id, neuro),
        )
        conexao.commit()
        conexao.close()

        texto = json.dumps(exportar_dados(ALUNO)["dados"], ensure_ascii=False)

        for rastro in ("Neurologia", "MED 5B", "Vias motoras", "Quiz de reflexos", "particular do colega", ALUNO_FORA):
            self.assertNotIn(rastro, texto)

    def test_copia_fica_registrada_mas_nao_entra_na_fila_da_administracao(self):
        from regras.privacidade import exportar_dados, listar_minhas, listar_solicitacoes

        exportar_dados(ALUNO)

        self.assertEqual([s["tipo"] for s in listar_minhas(ALUNO)["solicitacoes"]], ["exportacao"])
        self.assertEqual(listar_solicitacoes(ADMIN)["solicitacoes"], [])

    def test_so_aluno_exporta(self):
        from regras.privacidade import exportar_dados

        self.assertFalse(exportar_dados(PROFESSOR)["sucesso"])


class TestesCorrecao(BasePrivacidade):

    def test_aprovada_troca_o_dado_e_a_administracao_viu_o_antes(self):
        from regras.privacidade import decidir, listar_solicitacoes, solicitar

        pedido = solicitar(ALUNO, "correcao", "nome", "Aluno Um da Silva")
        item = listar_solicitacoes(ADMIN)["solicitacoes"][0]

        self.assertEqual(item["valor_atual"], "Aluno Um")
        self.assertTrue(decidir(ADMIN, pedido["id"], True)["sucesso"])
        self.assertEqual(self._contar("SELECT nome FROM users WHERE email = ?", ALUNO), "Aluno Um da Silva")

    def test_email_corrigido_vira_o_login(self):
        from regras.privacidade import decidir, solicitar

        pedido = solicitar(ALUNO, "correcao", "email", "  Aluno.Um@Teste.com ")
        decidir(ADMIN, pedido["id"], True)

        self.assertTrue(realizar_login("aluno.um@teste.com", SENHA)["sucesso"])
        self.assertFalse(realizar_login(ALUNO, SENHA)["sucesso"])

    def test_email_de_outra_conta_e_recusado_na_aprovacao(self):
        """Conferido na hora de aprovar, e não só no pedido: o e-mail pode ter
        sido dado a outra pessoa enquanto o pedido esperava na fila."""
        from regras.privacidade import decidir, solicitar

        pedido = solicitar(ALUNO, "correcao", "email", "livre@teste.com")
        criar_conta_staff(ADMIN, "livre@teste.com", SENHA, "aluno", nome="Chegou antes")

        self.assertFalse(decidir(ADMIN, pedido["id"], True)["sucesso"])
        self.assertEqual(self._contar("SELECT COUNT(*) FROM users WHERE email = ?", ALUNO), 1)

    def test_campo_fora_da_lista_nao_entra(self):
        """O nome do campo vai para o SQL: só a lista fechada pode passar."""
        from regras.privacidade import solicitar

        for campo in ("tipo", "senha", "nome = 'x', tipo"):
            self.assertFalse(solicitar(ALUNO, "correcao", campo, "adm")["sucesso"], campo)

    def test_recusa_exige_motivo_e_avisa_o_aluno(self):
        from regras.privacidade import decidir, solicitar

        pedido = solicitar(ALUNO, "correcao", "matricula", "RM 12345")

        self.assertFalse(decidir(ADMIN, pedido["id"], False)["sucesso"])
        self.assertTrue(decidir(ADMIN, pedido["id"], False, "A matrícula confere com a secretaria.")["sucesso"])
        titulos = [n["titulo"] for n in listar_notificacoes(ALUNO)["notificacoes"]]
        self.assertIn("Correção de dados: pedido recusado", titulos)

    def test_um_pedido_igual_em_aberto_por_vez(self):
        from regras.privacidade import solicitar

        self.assertTrue(solicitar(ALUNO, "correcao", "nome", "Um")["sucesso"])
        self.assertFalse(solicitar(ALUNO, "correcao", "nome", "Dois")["sucesso"])
        self.assertTrue(solicitar(ALUNO, "correcao", "matricula", "RM 1")["sucesso"])

    def test_aluno_cancela_o_proprio_e_nao_o_alheio(self):
        from regras.privacidade import cancelar, solicitar

        matricular_aluno(ADMIN, ALUNO_FORA, self.turma_id)
        pedido = solicitar(ALUNO, "correcao", "nome", "Outro nome")

        self.assertFalse(cancelar(ALUNO_FORA, pedido["id"])["sucesso"])
        self.assertTrue(cancelar(ALUNO, pedido["id"])["sucesso"])

    def test_so_administracao_decide(self):
        from regras.privacidade import decidir, listar_solicitacoes, solicitar

        pedido = solicitar(ALUNO, "correcao", "nome", "Outro nome")

        self.assertFalse(decidir(PROFESSOR, pedido["id"], True)["sucesso"])
        self.assertFalse(decidir(ALUNO, pedido["id"], True)["sucesso"])
        self.assertFalse(listar_solicitacoes(PROFESSOR)["sucesso"])


class TestesExclusao(BasePrivacidade):

    def test_aprovada_desativa_na_hora(self):
        sessao = realizar_login(ALUNO, SENHA)["token"]

        self._pedir_exclusao_aprovada()

        from infra.sessoes import buscar_usuario_da_sessao

        self.assertIsNone(buscar_usuario_da_sessao(sessao))
        login = realizar_login(ALUNO, SENHA)
        self.assertFalse(login["sucesso"])
        self.assertIn("desativada", login["mensagem"])

    def test_sessao_que_escapou_da_limpeza_nao_abre_nada(self):
        """A desativação apaga as sessões; este é o filtro de reserva, para a
        sessão criada depois (banco restaurado de backup, corrida)."""
        from infra.sessoes import buscar_usuario_da_sessao, criar_sessao

        self._pedir_exclusao_aprovada()

        self.assertIsNone(buscar_usuario_da_sessao(criar_sessao(self.aluno_id)))

    def test_desativada_so_e_dita_a_quem_sabe_a_senha(self):
        """Senão a mensagem contaria a qualquer um que o e-mail é de aluno daqui."""
        self._pedir_exclusao_aprovada()

        self.assertEqual(realizar_login(ALUNO, "senha-errada")["mensagem"], "E-mail ou senha incorretos.")

    def test_desativada_nao_recebe_codigo_de_recuperacao(self):
        self._pedir_exclusao_aprovada()

        solicitar_recuperacao(ALUNO)

        self.assertIsNone(self._contar("SELECT reset_token FROM users WHERE email = ?", ALUNO))

    def test_desativada_sai_do_ranking(self):
        from regras.ranking import ranking_da_turma

        coorte = criar_coorte(ADMIN, "MED 3A", SEMESTRE_DOS_TESTES)["coorte"]["id"]
        matricular_na_coorte(ADMIN, ALUNO, coorte)
        matricular_na_coorte(ADMIN, ALUNO_FORA, coorte)
        self.assertEqual(ranking_da_turma(ALUNO_FORA)["total"], 2)

        self._pedir_exclusao_aprovada()

        self.assertEqual(ranking_da_turma(ALUNO_FORA)["total"], 1)

    def test_revertida_no_prazo_volta_a_entrar(self):
        from regras.privacidade import reverter_exclusao

        pedido_id = self._pedir_exclusao_aprovada()

        self.assertTrue(reverter_exclusao(ADMIN, pedido_id)["sucesso"])
        self.assertTrue(realizar_login(ALUNO, SENHA)["sucesso"])

    def test_dentro_do_prazo_nada_e_apagado(self):
        from regras.privacidade import PRAZO_ANONIMIZACAO_DIAS, anonimizar_vencidas

        self._pedir_exclusao_aprovada()
        quase = datetime.now(timezone.utc) + timedelta(days=PRAZO_ANONIMIZACAO_DIAS - 1)

        self.assertEqual(anonimizar_vencidas(quase), 0)
        self.assertEqual(self._contar("SELECT COUNT(*) FROM anotacoes WHERE aluno_id = ?", self.aluno_id), 1)


class TestesAnonimizacao(BasePrivacidade):

    def setUp(self):
        super().setUp()
        from regras.privacidade import PRAZO_ANONIMIZACAO_DIAS, anonimizar_vencidas, solicitar

        # Um pedido de correção antigo, já atendido, guarda o e-mail: tem que sumir também.
        solicitar(ALUNO, "correcao", "email", "pessoal@gmail.com", "Uso este e-mail.")
        self.pedido_id = self._pedir_exclusao_aprovada()
        self.passou = datetime.now(timezone.utc) + timedelta(days=PRAZO_ANONIMIZACAO_DIAS + 1)
        self.anonimizadas = anonimizar_vencidas(self.passou)

    def test_some_o_que_identifica(self):
        conexao = sqlite3.connect(CAMINHO_DB)
        nome, email, matricula = conexao.execute(
            "SELECT nome, email, matricula FROM users WHERE id = ?", (self.aluno_id,)
        ).fetchone()
        conexao.close()

        self.assertEqual(self.anonimizadas, 1)
        self.assertEqual(nome, "Aluno removido")
        self.assertNotIn("aluno1", email)
        self.assertIsNone(matricula)

    def test_some_o_que_e_pessoal(self):
        for tabela, coluna in (("anotacoes", "aluno_id"), ("favoritos", "aluno_id"),
                               ("chat_mensagens", "aluno_id"), ("mensagens", "aluno_id"),
                               ("notificacoes", "user_id"), ("sessoes", "user_id")):
            self.assertEqual(
                self._contar(f"SELECT COUNT(*) FROM {tabela} WHERE {coluna} = ?", self.aluno_id), 0, tabela
            )
        self.assertEqual(
            self._contar("SELECT COUNT(*) FROM solicitacoes_privacidade WHERE valor_novo LIKE '%gmail%'"), 0
        )

    def test_registro_academico_fica(self):
        self.assertEqual(self._contar("SELECT nota FROM entregas WHERE aluno_id = ?", self.aluno_id), 10)
        self.assertEqual(self._contar("SELECT COUNT(*) FROM matriculas WHERE aluno_id = ?", self.aluno_id), 1)

    def test_ninguem_entra_e_nao_ha_volta(self):
        from regras.privacidade import reverter_exclusao

        self.assertFalse(realizar_login(ALUNO, SENHA)["sucesso"])
        self.assertFalse(reverter_exclusao(ADMIN, self.pedido_id)["sucesso"])

    def test_rodar_de_novo_nao_faz_nada(self):
        from regras.privacidade import anonimizar_vencidas

        self.assertEqual(anonimizar_vencidas(self.passou), 0)


class TestesRotasPrivacidade(BaseDelta):
    """Cada rota com o perfil certo — a regra confere, mas a rota é a porta."""

    def setUp(self):
        super().setUp()
        from fastapi.testclient import TestClient

        import main

        self.cliente = TestClient(main.app)

    def _cab(self, email):
        token = self.cliente.post("/login", json={"email": email, "senha": SENHA}).json()["token"]
        return {"Authorization": f"Bearer {token}"}

    def test_aluno_pede_e_administracao_decide(self):
        aluno, admin = self._cab(ALUNO), self._cab(ADMIN)

        pedido = self.cliente.post("/aluno/privacidade/solicitacoes", headers=aluno,
                                   json={"tipo": "correcao", "campo": "nome", "valor_novo": "Aluno Um Souza"}).json()
        fila = self.cliente.get("/admin/privacidade/solicitacoes", headers=admin).json()
        decisao = self.cliente.put(f"/admin/privacidade/solicitacoes/{pedido['id']}", headers=admin,
                                   json={"aprovar": True}).json()

        self.assertEqual([s["id"] for s in fila["solicitacoes"]], [pedido["id"]])
        self.assertTrue(decisao["sucesso"], decisao)
        self.assertEqual(self.cliente.get("/eu", headers=aluno).json()["nome"], "Aluno Um Souza")

    def test_cada_lado_so_na_propria_porta(self):
        aluno, professor = self._cab(ALUNO), self._cab(PROFESSOR)

        self.assertEqual(self.cliente.get("/admin/privacidade/solicitacoes", headers=aluno).status_code, 403)
        self.assertEqual(self.cliente.get("/aluno/privacidade/exportar", headers=professor).status_code, 403)
        self.assertEqual(self.cliente.get("/aluno/privacidade/exportar").status_code, 401)


if __name__ == "__main__":
    print(f"Banco de teste: {CAMINHO_DB}")
    print("(o Ollama não precisa estar rodando)\n")
    unittest.main(verbosity=2)
