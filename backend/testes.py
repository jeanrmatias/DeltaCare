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
from regras.autenticacao import (  # noqa: E402
    MAX_TENTATIVAS_RESET,
    cadastrar_usuario,
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
        cadastrar_usuario("aluno3@teste.com", SENHA, "aluno", nome="Aluno Tres")
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
        cadastrar_usuario("aluno3@teste.com", SENHA, "aluno", nome="Aluno Tres")
        matricular_aluno(ADMIN, "aluno3@teste.com", self.turma_id)

        quiz = self.criar_quiz("Quiz", "Arritmias", [0])
        enviar_entrega(ALUNO, quiz, [0])

        atividade = desempenho_da_turma(PROFESSOR, self.turma_id)["atividades"][0]
        self.assertEqual(atividade["entregues"], 1)
        self.assertEqual(atividade["pendentes"], 1)

    def test_topico_da_turma_soma_os_erros_de_todos(self):
        cadastrar_usuario("aluno3@teste.com", SENHA, "aluno", nome="Aluno Tres")
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
        cadastrar_usuario("aluno3@teste.com", SENHA, "aluno", nome="Aluno Tres")
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
        cadastrar_usuario("aluno3@teste.com", SENHA, "aluno", nome="Aluno Tres")
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


if __name__ == "__main__":
    print(f"Banco de teste: {CAMINHO_DB}")
    print("(o Ollama não precisa estar rodando)\n")
    unittest.main(verbosity=2)
