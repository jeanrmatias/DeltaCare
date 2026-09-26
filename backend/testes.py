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
# do banco no momento em que são importados.
_ARQUIVO_TEMP = os.path.join(tempfile.gettempdir(), "deltacare_testes.db")
os.environ["DELTACARE_DB"] = _ARQUIVO_TEMP

import sqlite3  # noqa: E402

from infra.database import CAMINHO_DB, configurar_banco  # noqa: E402
from regras.autenticacao import cadastrar_usuario, criar_conta_staff, realizar_login  # noqa: E402
from regras.aluno import (  # noqa: E402
    MAX_PERGUNTAS_QUE_PONTUAM_POR_DIA,
    XP_POR_ATIVIDADE_ENTREGUE,
    listar_materiais_do_aluno,
    obter_arquivo_material_do_aluno,
    registrar_acesso_material,
    resumo_do_aluno,
)
from regras.atividades import (  # noqa: E402
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
from regras.matriculas import listar_alunos_da_turma, matricular_aluno  # noqa: E402
from regras.turmas import criar_turma, excluir_turma, listar_usuarios  # noqa: E402
from infra.security import hash_senha, verificar_senha  # noqa: E402
from infra.sessoes import buscar_usuario_da_sessao, criar_sessao, encerrar_sessao  # noqa: E402
from regras import chat_ia  # noqa: E402

SENHA = "teste123"

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

        criar_conta_staff(ADMIN, PROFESSOR, SENHA, "professor", nome="Professor Um")
        criar_conta_staff(ADMIN, PROFESSOR2, SENHA, "professor", nome="Professor Dois")
        cadastrar_usuario(ALUNO, SENHA, "aluno", nome="Aluno Um")
        cadastrar_usuario(ALUNO_FORA, SENHA, "aluno", nome="Aluno Dois")

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

    def test_cadastro_publico_so_cria_aluno(self):
        """A rota pública não pode ser caminho para virar admin."""
        for tipo in ("adm", "professor"):
            resultado = cadastrar_usuario(f"invasor_{tipo}@teste.com", SENHA, tipo, nome="Invasor")
            self.assertFalse(resultado["sucesso"], f"cadastro público aceitou tipo {tipo}")

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

if __name__ == "__main__":
    print(f"Banco de teste: {CAMINHO_DB}")
    print("(o Ollama não precisa estar rodando)\n")
    unittest.main(verbosity=2)
