import os
from functools import partial
from typing import Any, Optional

import anyio

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from pydantic import BaseModel

from infra.database import FecharConexoesDaRequisicao, configurar_banco
from infra.sessoes import (
    buscar_usuario_da_sessao,
    encerrar_sessao,
    limpar_sessoes_expiradas,
)
from regras.autenticacao import (
    alterar_senha,
    criar_conta_staff,
    realizar_login,
    redefinir_senha,
    solicitar_recuperacao,
)
from regras.materiais import (
    atualizar_material,
    criar_material,
    criar_material_em_turmas,
    excluir_material,
    listar_materiais,
    obter_arquivo_material,
)
from regras.turmas import (
    criar_turma,
    excluir_turma,
    listar_professores,
    listar_turmas,
    listar_turmas_admin,
    listar_usuarios,
    perfil_do_usuario,
)
from regras.conteudo import (
    arquivo_para_supervisao,
    atividade_para_supervisao,
    visao_do_conteudo,
)
from regras.anotacoes import (
    criar_anotacao,
    editar_anotacao,
    excluir_anotacao,
    listar_anotacoes,
)
from regras.favoritos import desmarcar_favorito, listar_favoritos, marcar_favorito
from regras.lacunas import listar_lacunas, marcar_tratada
from regras.privacidade import (
    anonimizar_vencidas,
    cancelar as cancelar_solicitacao_privacidade,
    decidir as decidir_solicitacao_privacidade,
    exportar_dados,
    listar_minhas as listar_minhas_solicitacoes_privacidade,
    listar_solicitacoes as listar_solicitacoes_privacidade,
    reverter_exclusao,
    solicitar as solicitar_privacidade,
)
from regras.avisos import (
    excluir_aviso,
    listar_avisos_enviados,
    listar_avisos_recebidos,
    publicar_aviso,
)
from regras.ranking import definir_visibilidade, ranking_da_turma
from regras.semestres import (
    definir_semestre_vigente,
    historico_do_aluno,
    historico_do_professor,
    obter_semestre_vigente,
)
from regras.coortes import (
    criar_coorte,
    criar_excecao,
    excluir_coorte,
    listar_alunos_da_coorte,
    listar_coortes,
    listar_disciplinas_da_coorte,
    matricular_na_coorte,
    remover_da_coorte,
    remover_excecao,
)
from regras.matriculas import (
    desmatricular_aluno,
    listar_alunos,
    listar_alunos_da_turma,
    listar_turmas_do_aluno,
    matricular_aluno,
)
from regras.aluno import (
    listar_materiais_do_aluno,
    obter_arquivo_material_do_aluno,
    registrar_acesso_material,
    resumo_do_aluno,
)
from regras.atividades import (
    atualizar_atividade,
    corrigir_entrega,
    criar_atividade_em_turmas,
    enviar_entrega,
    excluir_atividade,
    listar_atividades,
    listar_atividades_do_aluno,
    listar_entregas,
    obter_arquivo_entrega,
    obter_atividade,
    obter_atividade_do_aluno,
    salvar_progresso,
)
from regras.calendario import eventos_do_mes
from regras.denuncias import (
    criar_denuncia,
    listar_minhas,
    listar_todas,
    remover_denuncia,
    tratar_denuncia,
)
from regras.desempenho import desempenho_da_turma, desempenho_do_aluno
from regras.mensagens import abrir_conversa, enviar_mensagem, listar_conversas
from regras.importacao import analisar_planilha, importar_alunos
from regras.notificacoes import (
    listar_notificacoes,
    marcar_como_lida,
    marcar_todas_como_lidas,
)
from regras.chat_ia import buscar_historico, indexar_material, responder_pergunta

configurar_banco()

app = FastAPI()
# De quais endereços o navegador pode chamar esta API.
#
# Era `*` — qualquer site do mundo podia montar uma página que chamasse a API
# a partir do navegador de um aluno logado. Com o token no header e não em
# cookie o estrago é menor do que parece, mas `*` é o tipo de configuração que
# vai para produção por esquecimento.
#
# Padrão: os servidores de desenvolvimento — o front antigo (frontend/servir.py,
# porta 5500) e o React (web/, Vite, porta 5173) —, pelos dois nomes que o
# navegador usa para cada um. No servidor de verdade:
#
#     DELTACARE_ORIGENS=https://deltacare.moinhos.org.br
#
# vários separados por vírgula. Abrir o HTML por file:// não funciona, e já
# não funcionava antes (o README avisa).
ORIGENS_PERMITIDAS = [
    origem.strip()
    for origem in os.environ.get(
        "DELTACARE_ORIGENS",
        "http://127.0.0.1:5500,http://localhost:5500,http://127.0.0.1:5173,http://localhost:5173",
    ).split(",")
    if origem.strip()
]

# =========================================================================
# O servidor de IA tem orçamento próprio
#
# Rota `def` roda num pool de threads que o sistema inteiro divide, e esse pool
# tem 40. Cada pergunta ao chat prendia uma thread pelos 10-20 segundos da
# resposta do modelo, então 40 perguntas simultâneas ocupavam todas — e a 41ª
# requisição, fosse um login ou abrir uma tela, esperava na fila atrás delas.
# Medido com um LLM falso de 4s: com 60 perguntas em andamento, o login foi de
# 97ms para 7,4 segundos.
#
# Agora as chamadas ao LLM passam por `_com_ia`, que usa um limitador separado.
# Quem passar do limite **espera sem ocupar thread nenhuma**: login e telas
# nunca entram na fila do chat, por mais cheio que ele esteja.
#
# O número NÃO é teto de interações — ninguém é recusado. É quantas chamadas
# vão ao servidor de IA *ao mesmo tempo*. Mandar mais do que ele processa não
# acelera nada: o Ollama local atende poucas por vez (OLLAMA_NUM_PARALLEL) e
# enfileira o resto do lado dele, com a thread daqui presa esperando. No
# servidor de verdade, com um LLM que aguenta mais, basta subir:
#
#     DELTACARE_IA_SIMULTANEAS=32
#
# junto com OLLAMA_URL apontando para ele.
# =========================================================================

LIMITE_IA = anyio.CapacityLimiter(int(os.environ.get("DELTACARE_IA_SIMULTANEAS", "4")))


async def _com_ia(funcao, *args):
    """Roda uma função que fala com o LLM, dentro do orçamento da IA."""
    return await anyio.to_thread.run_sync(funcao, *args, limiter=LIMITE_IA)


app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENS_PERMITIDAS,
    # Só o que o front de fato usa. O token vai em Authorization; o resto é
    # JSON. Cookie não existe aqui, então nada de allow_credentials.
    allow_headers=["Authorization", "Content-Type"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
)

# Toda conexão que uma rota deixar aberta (exceção no meio do caminho) é
# fechada quando a requisição termina. Ver infra/database.py.
app.add_middleware(FecharConexoesDaRequisicao)

limpar_sessoes_expiradas()
# Exclusões que venceram o prazo enquanto o servidor estava parado.
anonimizar_vencidas()

# Sem SMTP, "Esqueci minha senha" não chega a ninguém: o código vai para este
# console. Em desenvolvimento é o esperado; em produção é um defeito, e o aviso
# na subida é o que impede de descobrir isso só quando um aluno reclamar.
from infra.email import email_configurado  # noqa: E402

if not email_configurado():
    print(
        "[Delta Care] AVISO: DELTACARE_SMTP_HOST não definido. Os e-mails de recuperação "
        "de senha não serão enviados; o código aparece neste console."
    )


# =========================================================================
# Autenticação
# =========================================================================
# Estas dependências são o único caminho pelo qual uma rota descobre quem está
# fazendo a requisição. Antes, a identidade vinha no corpo ou na query string
# (professor_email=...), o que significava que qualquer pessoa podia agir em
# nome de outra só trocando o e-mail. Agora vem do token da sessão.


# Com a senha provisória, só isto funciona: ver a própria conta, trocar a
# senha e sair. O resto espera a troca.
LIBERADAS_COM_SENHA_PROVISORIA = {("GET", "/eu"), ("PUT", "/eu/senha"), ("POST", "/logout")}


def usuario_logado(request: Request, authorization: Optional[str] = Header(default=None)) -> dict:
    """Valida o header `Authorization: Bearer <token>` e devolve o usuário."""
    token = ""

    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()

    usuario = buscar_usuario_da_sessao(token)

    if not usuario:
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada. Faça login de novo.")

    # Senha provisória (criada pela administração ou pela planilha, a mesma
    # para a turma toda): a troca é exigida aqui, e não só pela tela — senão
    # um colega que soubesse a senha da turma entraria na conta do outro por
    # qualquer rota da API.
    if usuario["senha_provisoria"] and (request.method, request.url.path) not in LIBERADAS_COM_SENHA_PROVISORIA:
        raise HTTPException(
            status_code=403,
            detail={"codigo": "trocar_senha", "mensagem": "Troque a senha provisória antes de continuar."},
        )

    return usuario


def exigir_perfil(*perfis: str):
    """Dependência que além de exigir login, exige um perfil específico.

    O perfil vem do banco (via token), não de nada que o cliente informe.
    """

    def verificar(usuario: dict = Depends(usuario_logado)) -> dict:
        if usuario["tipo"] not in perfis:
            raise HTTPException(status_code=403, detail="Você não tem permissão para esta ação.")
        return usuario

    return verificar


usuario_admin = exigir_perfil("adm")
usuario_professor = exigir_perfil("professor")
usuario_aluno = exigir_perfil("aluno")


class LoginRequest(BaseModel):
    email: str
    senha: str


class StaffRequest(BaseModel):
    email: str
    senha: str
    tipo: str
    nome: str = ""
    # Só usados no perfil correspondente; o formulário manda sempre o mesmo corpo.
    disciplinas: str = ""
    matricula: str = ""
    turma_id: Optional[int] = None


class RecuperacaoSenhaRequest(BaseModel):
    email: str


class RedefinicaoSenhaRequest(BaseModel):
    # `email` amarra o código a uma conta. Sem ele a busca era global e um
    # atacante tentava códigos contra qualquer recuperação pendente.
    email: str
    token: str
    nova_senha: str


class TurmaRequest(BaseModel):
    # professor_email continua aqui de propósito: é o professor que vai receber
    # a turma (o alvo da ação), não quem está fazendo a requisição.
    professor_email: str
    nome: str
    semestre: str
    # Opcional, e assim fica: disciplina sem coorte é caso legítimo (optativa,
    # extensão), e nada espalha quando ela vem vazia.
    coorte_id: Optional[int] = None


class CoorteRequest(BaseModel):
    """A turma de alunos. `coortes` no código, "Turma" na interface — a nota de
    vocabulário está em regras/coortes.py."""
    nome: str
    semestre: str


class CoorteAlunoRequest(BaseModel):
    # aluno_email é o aluno sendo movido (alvo), não quem faz a requisição.
    aluno_email: str


class ExcecaoRequest(BaseModel):
    aluno_email: str
    turma_id: int


class MaterialRequest(BaseModel):
    # turma_id continua aceito para não quebrar quem já integra com a rota;
    # turma_ids é o caminho novo, que publica em várias turmas de uma vez.
    turma_id: Optional[int] = None
    turma_ids: Optional[list[int]] = None
    titulo: str
    tipo: str
    descricao: str = ""
    assunto: str = ""
    topico: str = ""
    aula: str = ""
    semestre: str = ""
    rascunho: bool = True
    data_liberacao: Optional[str] = None
    link_url: Optional[str] = None
    arquivo_base64: Optional[str] = None
    arquivo_nome: Optional[str] = None


class MaterialAtualizacaoRequest(BaseModel):
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    assunto: Optional[str] = None
    topico: Optional[str] = None
    aula: Optional[str] = None
    semestre: Optional[str] = None
    rascunho: Optional[bool] = None
    data_liberacao: Optional[str] = None
    link_url: Optional[str] = None


class ImportacaoRequest(BaseModel):
    arquivo_base64: str
    arquivo_nome: str
    senha_padrao: str = ""
    turma_id: Optional[int] = None


class MatriculaRequest(BaseModel):
    # aluno_email é o aluno sendo matriculado (alvo), não quem faz a requisição.
    aluno_email: str
    turma_id: int


class PerguntaRequest(BaseModel):
    turma_id: int
    pergunta: str


class MensagemRequest(BaseModel):
    turma_id: int
    conteudo: str
    # Só usado quando quem envia é professor: diz com qual aluno da turma é a
    # conversa. Vindo de aluno, é ignorado (ver regras/mensagens.py).
    aluno_email: Optional[str] = None


class DenunciaRequest(BaseModel):
    material_id: int
    motivo: str
    descricao: str = ""


class TratamentoDenunciaRequest(BaseModel):
    status: str
    acao: str = ""


class QuestaoRequest(BaseModel):
    enunciado: str
    alternativas: list[str]
    # Índice da alternativa certa. Só trafega do professor para o servidor;
    # nunca no sentido contrário para o aluno (regras/atividades.py).
    correta: int


class EntregaRequest(BaseModel):
    """O que o aluno envia ao entregar.

    `respostas` é a lista de escolhas (objetiva) ou o texto (dissertativa). O
    arquivo vai em base64 dentro do JSON, como nos materiais, para não depender
    de python-multipart.
    """
    respostas: Any = None
    arquivo_base64: Optional[str] = None
    arquivo_nome: Optional[str] = None


class AtividadeRequest(BaseModel):
    # Mesmo par turma_id/turma_ids dos materiais: o segundo publica em várias
    # turmas de uma vez, o primeiro fica para não quebrar quem já integra.
    turma_id: Optional[int] = None
    turma_ids: Optional[list[int]] = None
    titulo: str
    tipo: str
    enunciado: str = ""
    assunto: str = ""
    topico: str = ""
    pontos: int = 10
    rascunho: bool = True
    data_liberacao: Optional[str] = None
    prazo: Optional[str] = None
    questoes: Optional[list[QuestaoRequest]] = None
    # 'nenhum' (padrão), 'opcional' ou 'obrigatorio'. Só vale em dissertativa —
    # numa objetiva o sistema corrige pelo gabarito e ninguém leria o arquivo.
    anexo: str = "nenhum"


class AtividadeAtualizacaoRequest(BaseModel):
    titulo: Optional[str] = None
    enunciado: Optional[str] = None
    assunto: Optional[str] = None
    topico: Optional[str] = None
    pontos: Optional[int] = None
    rascunho: Optional[bool] = None
    data_liberacao: Optional[str] = None
    prazo: Optional[str] = None
    anexo: Optional[str] = None


class CorrecaoRequest(BaseModel):
    nota: float
    devolutiva: str = ""


class RespostaRequest(BaseModel):
    # Objetiva manda uma lista de índices escolhidos; dissertativa manda texto.
    # O tipo é validado em regras/atividades.py, que sabe qual é a atividade.
    respostas: Any = None


@app.get("/")
def inicio():
    """Quem digita o endereço do sistema cai nas telas, e não num JSON."""
    return RedirectResponse(url="/app/")


@app.get("/saude")
def saude():
    """Para monitoramento: responde enquanto o processo está de pé."""
    return {"status": "ok"}


# ---------------------------- rotas públicas ----------------------------
# As únicas que não exigem token: sem elas ninguém conseguiria obter um.

@app.post("/login")
def login(dados: LoginRequest):
    return realizar_login(dados.email, dados.senha)


@app.post("/recuperar-senha")
def recuperar_senha(dados: RecuperacaoSenhaRequest):
    return solicitar_recuperacao(dados.email)


@app.post("/redefinir-senha")
def redefinicao_senha(dados: RedefinicaoSenhaRequest):
    return redefinir_senha(dados.email, dados.token, dados.nova_senha)


# ---------------------------- sessão ----------------------------

@app.post("/logout")
def logout(authorization: Optional[str] = Header(default=None)):
    """Invalida o token atual. Não dá erro se já estiver deslogado."""
    if authorization and authorization.lower().startswith("bearer "):
        encerrar_sessao(authorization[7:].strip())
    return {"sucesso": True, "mensagem": "Sessão encerrada."}


# ---------------------------- notificações ----------------------------
# Disponíveis para qualquer perfil logado: professor recebe aviso de matrícula,
# aluno recebe aviso de material liberado.

@app.get("/notificacoes")
def listar_notificacoes_rota(usuario: dict = Depends(usuario_logado)):
    return listar_notificacoes(usuario["email"])


@app.post("/notificacoes/{notificacao_id}/lida")
def marcar_lida_rota(notificacao_id: int, usuario: dict = Depends(usuario_logado)):
    return marcar_como_lida(usuario["email"], notificacao_id)


@app.post("/notificacoes/lidas")
def marcar_todas_lidas_rota(usuario: dict = Depends(usuario_logado)):
    return marcar_todas_como_lidas(usuario["email"])


@app.get("/eu")
def usuario_atual_rota(usuario: dict = Depends(usuario_logado)):
    """Dados da própria conta: usado para validar a sessão e pela tela de perfil."""
    return {**perfil_do_usuario(usuario["email"]), "trocar_senha": usuario["senha_provisoria"]}


class TrocaDeSenhaRequest(BaseModel):
    senha_atual: str
    nova_senha: str


@app.put("/eu/senha")
def alterar_senha_rota(dados: TrocaDeSenhaRequest, usuario: dict = Depends(usuario_logado)):
    return alterar_senha(usuario["email"], usuario["token"], dados.senha_atual, dados.nova_senha)


# ---------------------------- administração ----------------------------

@app.post("/admin/usuarios")
def criar_staff_rota(dados: StaffRequest, admin: dict = Depends(usuario_admin)):
    """Cria conta de qualquer perfil."""
    return criar_conta_staff(
        admin["email"],
        dados.email,
        dados.senha,
        dados.tipo,
        nome=dados.nome,
        disciplinas=dados.disciplinas,
        matricula=dados.matricula,
        turma_id=dados.turma_id,
    )


@app.get("/admin/turmas")
def listar_turmas_admin_rota(admin: dict = Depends(usuario_admin)):
    return listar_turmas_admin(admin["email"])


@app.post("/admin/turmas")
def criar_turma_rota(dados: TurmaRequest, admin: dict = Depends(usuario_admin)):
    return criar_turma(
        admin["email"], dados.professor_email, dados.nome, dados.semestre, dados.coorte_id
    )


@app.delete("/admin/turmas/{turma_id}")
def excluir_turma_rota(turma_id: int, admin: dict = Depends(usuario_admin)):
    return excluir_turma(admin["email"], turma_id)


@app.get("/admin/professores")
def listar_professores_rota(admin: dict = Depends(usuario_admin)):
    return listar_professores(admin["email"])


@app.get("/admin/usuarios")
def listar_usuarios_rota(admin: dict = Depends(usuario_admin)):
    """Todas as contas do sistema, para a tela de gestão de usuários."""
    return listar_usuarios(admin["email"])


@app.post("/admin/importar/analisar")
def analisar_planilha_rota(dados: ImportacaoRequest, admin: dict = Depends(usuario_admin)):
    """Confere a planilha sem gravar nada.

    Separado da importação para o admin ver o que vai acontecer antes de
    acontecer — uma planilha com metade das linhas erradas não deve criar
    metade das contas sem aviso.
    """
    return analisar_planilha(dados.arquivo_base64, dados.arquivo_nome)


@app.post("/admin/importar")
def importar_alunos_rota(dados: ImportacaoRequest, admin: dict = Depends(usuario_admin)):
    return importar_alunos(
        admin["email"],
        dados.arquivo_base64,
        dados.arquivo_nome,
        turma_id=dados.turma_id,
        senha_padrao=dados.senha_padrao,
    )


@app.post("/admin/matriculas")
def matricular_aluno_rota(dados: MatriculaRequest, admin: dict = Depends(usuario_admin)):
    return matricular_aluno(admin["email"], dados.aluno_email, dados.turma_id)


@app.delete("/admin/matriculas")
def desmatricular_aluno_rota(dados: MatriculaRequest, admin: dict = Depends(usuario_admin)):
    return desmatricular_aluno(admin["email"], dados.aluno_email, dados.turma_id)


@app.get("/admin/turmas/{turma_id}/alunos")
def listar_alunos_da_turma_rota(turma_id: int, admin: dict = Depends(usuario_admin)):
    return listar_alunos_da_turma(admin["email"], turma_id)


# =========================================================================
# Turmas de alunos (coortes)
#
# `/admin/coortes` e não `/admin/turmas` porque `/admin/turmas` já existe e
# serve as disciplinas — ver a nota de vocabulário em regras/coortes.py. A
# interface chama estas de "Turma" e aquelas de "Disciplina".
# =========================================================================

@app.get("/admin/coortes")
def listar_coortes_rota(admin: dict = Depends(usuario_admin)):
    return listar_coortes(admin["email"])


@app.post("/admin/coortes")
def criar_coorte_rota(dados: CoorteRequest, admin: dict = Depends(usuario_admin)):
    return criar_coorte(admin["email"], dados.nome, dados.semestre)


@app.delete("/admin/coortes/{coorte_id}")
def excluir_coorte_rota(coorte_id: int, admin: dict = Depends(usuario_admin)):
    return excluir_coorte(admin["email"], coorte_id)


@app.get("/admin/coortes/{coorte_id}/alunos")
def listar_alunos_da_coorte_rota(coorte_id: int, admin: dict = Depends(usuario_admin)):
    return listar_alunos_da_coorte(admin["email"], coorte_id)


@app.get("/admin/coortes/{coorte_id}/disciplinas")
def listar_disciplinas_da_coorte_rota(coorte_id: int, admin: dict = Depends(usuario_admin)):
    return listar_disciplinas_da_coorte(admin["email"], coorte_id)


@app.post("/admin/coortes/{coorte_id}/alunos")
def matricular_na_coorte_rota(
    coorte_id: int, dados: CoorteAlunoRequest, admin: dict = Depends(usuario_admin)
):
    """Entra na turma e, com ela, em todas as disciplinas menos as de exceção."""
    return matricular_na_coorte(admin["email"], dados.aluno_email, coorte_id)


@app.delete("/admin/coortes/{coorte_id}/alunos")
def remover_da_coorte_rota(
    coorte_id: int, dados: CoorteAlunoRequest, admin: dict = Depends(usuario_admin)
):
    """DELETE com o aluno no corpo, igual a /admin/matriculas."""
    return remover_da_coorte(admin["email"], dados.aluno_email, coorte_id)


# `/admin/excecoes` e **não** `/admin/coortes/excecoes`: o segundo colide com
# `/admin/coortes/{coorte_id}`, que é declarado antes e faria o FastAPI tentar
# ler "excecoes" como um inteiro. Dava para resolver declarando na ordem certa,
# e foi recusado: a correção some no primeiro dia em que alguem reorganizar o
# arquivo, e o sintoma (422 no DELETE) não aponta para a causa. Caminho sem
# ambiguidade não depende de ordem. Além disso, a exceção é sobre
# (aluno, disciplina) — a coorte se descobre a partir da disciplina.
@app.post("/admin/excecoes")
def criar_excecao_rota(dados: ExcecaoRequest, admin: dict = Depends(usuario_admin)):
    """Tira da disciplina um aluno que continua na turma."""
    return criar_excecao(admin["email"], dados.aluno_email, dados.turma_id)


@app.delete("/admin/excecoes")
def remover_excecao_rota(dados: ExcecaoRequest, admin: dict = Depends(usuario_admin)):
    """Desfaz a exceção: o aluno volta a cursar a disciplina."""
    return remover_excecao(admin["email"], dados.aluno_email, dados.turma_id)


@app.get("/admin/alunos")
def listar_alunos_rota(admin: dict = Depends(usuario_admin)):
    return listar_alunos(admin["email"])


# ---------------------------- professor ----------------------------

@app.get("/turmas")
def listar_turmas_rota(professor: dict = Depends(usuario_professor)):
    """Turmas do professor logado (somente leitura — quem cria é o admin)."""
    return listar_turmas(professor["email"])


@app.post("/materiais")
async def criar_material_rota(dados: MaterialRequest, professor: dict = Depends(usuario_professor)):
    turmas = dados.turma_ids or ([dados.turma_id] if dados.turma_id else [])

    if not turmas:
        raise HTTPException(status_code=400, detail="Escolha pelo menos uma turma.")

    campos = dict(
        titulo=dados.titulo,
        tipo=dados.tipo,
        descricao=dados.descricao,
        assunto=dados.assunto,
        topico=dados.topico,
        aula=dados.aula,
        semestre=dados.semestre,
        rascunho=dados.rascunho,
        data_liberacao=dados.data_liberacao,
        link_url=dados.link_url,
        arquivo_base64=dados.arquivo_base64,
        arquivo_nome=dados.arquivo_nome,
    )

    # Rota `async`: o que é banco vai para o pool comum (rápido), e só a
    # indexação vai para o orçamento da IA. Chamar código síncrono direto aqui
    # dentro travaria o laço de eventos do servidor inteiro.
    resultado = await anyio.to_thread.run_sync(
        partial(criar_material_em_turmas, professor["email"], turmas, **campos)
    )

    # Indexa os PDFs pro chat de IA do aluno poder buscar neles depois. Se a
    # indexação falhar (ex.: Ollama fora do ar), o material continua salvo —
    # só não vai aparecer nas buscas do chat.
    #
    # É uma chamada de embedding por trecho: um PDF grande são centenas. Por
    # isso passa por _com_ia, e disputa o servidor de IA com as perguntas dos
    # alunos pelas mesmas vagas, em vez de prender uma thread comum.
    if resultado.get("sucesso") and dados.tipo == "pdf":
        for material_id in resultado.get("material_ids", []):
            try:
                await _com_ia(indexar_material, material_id)
            except Exception as erro:
                resultado["aviso_indexacao"] = f"Material salvo, mas não indexado pro chat: {erro}"

    return resultado


@app.get("/materiais")
def listar_materiais_rota(
    turma_id: Optional[int] = None,
    professor: dict = Depends(usuario_professor),
):
    return listar_materiais(professor["email"], turma_id)


@app.put("/materiais/{material_id}")
def atualizar_material_rota(
    material_id: int,
    dados: MaterialAtualizacaoRequest,
    professor: dict = Depends(usuario_professor),
):
    campos = dados.model_dump(exclude_none=True)
    return atualizar_material(material_id, professor["email"], **campos)


@app.delete("/materiais/{material_id}")
def excluir_material_rota(material_id: int, professor: dict = Depends(usuario_professor)):
    return excluir_material(material_id, professor["email"])


@app.get("/materiais/{material_id}/arquivo")
def baixar_arquivo_material(material_id: int, professor: dict = Depends(usuario_professor)):
    resultado = obter_arquivo_material(material_id, professor["email"])

    if not resultado:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

    caminho, nome_original = resultado
    return FileResponse(caminho, filename=nome_original)


# ---------------------------- aluno ----------------------------

@app.get("/aluno/turmas")
def listar_turmas_do_aluno_rota(aluno: dict = Depends(usuario_aluno)):
    return listar_turmas_do_aluno(aluno["email"])


@app.get("/aluno/resumo")
def resumo_do_aluno_rota(aluno: dict = Depends(usuario_aluno)):
    """Números da tela inicial do aluno."""
    return resumo_do_aluno(aluno["email"])


@app.get("/aluno/materiais")
def listar_materiais_do_aluno_rota(
    turma_id: Optional[int] = None,
    aluno: dict = Depends(usuario_aluno),
):
    """Materiais publicados das turmas do aluno.

    Rota separada da do professor de propósito: aqui nunca aparece rascunho
    nem material agendado (ver logica_aluno).
    """
    return listar_materiais_do_aluno(aluno["email"], turma_id)


@app.get("/aluno/materiais/{material_id}/arquivo")
def baixar_arquivo_material_aluno(material_id: int, aluno: dict = Depends(usuario_aluno)):
    resultado = obter_arquivo_material_do_aluno(aluno["email"], material_id)

    if not resultado:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

    # Registrado só depois da checagem de permissão: material que o aluno não
    # pode ver não deve entrar no acompanhamento de estudo dele.
    registrar_acesso_material(aluno["email"], material_id)

    caminho, nome_original = resultado
    return FileResponse(caminho, filename=nome_original)


# ---------------------------- atividades ----------------------------
# Dois lados: o professor cria e corrige; o aluno resolve e entrega. A visão
# do aluno mora em funções separadas (regras/atividades.py) pelo mesmo motivo
# dos materiais — lá rascunho e agendado nunca aparecem, e o gabarito nunca sai
# do servidor.

@app.post("/atividades")
def criar_atividade_rota(dados: AtividadeRequest, professor: dict = Depends(usuario_professor)):
    turmas = dados.turma_ids or ([dados.turma_id] if dados.turma_id else [])

    return criar_atividade_em_turmas(
        professor["email"],
        turmas,
        titulo=dados.titulo,
        enunciado=dados.enunciado,
        tipo=dados.tipo,
        assunto=dados.assunto,
        topico=dados.topico,
        pontos=dados.pontos,
        rascunho=dados.rascunho,
        data_liberacao=dados.data_liberacao,
        prazo=dados.prazo,
        questoes=[q.model_dump() for q in (dados.questoes or [])],
        anexo=dados.anexo,
    )


@app.get("/atividades")
def listar_atividades_rota(
    turma_id: Optional[int] = None,
    professor: dict = Depends(usuario_professor),
):
    return listar_atividades(professor["email"], turma_id)


@app.get("/atividades/{atividade_id}")
def obter_atividade_rota(atividade_id: int, professor: dict = Depends(usuario_professor)):
    """Inclui o gabarito — por isso é rota de professor, nunca de aluno."""
    return obter_atividade(atividade_id, professor["email"])


@app.put("/atividades/{atividade_id}")
def atualizar_atividade_rota(
    atividade_id: int,
    dados: AtividadeAtualizacaoRequest,
    professor: dict = Depends(usuario_professor),
):
    return atualizar_atividade(atividade_id, professor["email"], **dados.model_dump(exclude_none=True))


@app.delete("/atividades/{atividade_id}")
def excluir_atividade_rota(atividade_id: int, professor: dict = Depends(usuario_professor)):
    return excluir_atividade(atividade_id, professor["email"])


@app.get("/atividades/{atividade_id}/entregas")
def listar_entregas_rota(atividade_id: int, professor: dict = Depends(usuario_professor)):
    return listar_entregas(atividade_id, professor["email"])


@app.post("/entregas/{entrega_id}/correcao")
def corrigir_entrega_rota(
    entrega_id: int,
    dados: CorrecaoRequest,
    professor: dict = Depends(usuario_professor),
):
    return corrigir_entrega(entrega_id, professor["email"], dados.nota, dados.devolutiva)


@app.get("/aluno/atividades")
def listar_atividades_do_aluno_rota(
    turma_id: Optional[int] = None,
    aluno: dict = Depends(usuario_aluno),
):
    return listar_atividades_do_aluno(aluno["email"], turma_id)


@app.get("/aluno/atividades/{atividade_id}")
def obter_atividade_do_aluno_rota(atividade_id: int, aluno: dict = Depends(usuario_aluno)):
    return obter_atividade_do_aluno(aluno["email"], atividade_id)


@app.post("/aluno/atividades/{atividade_id}/progresso")
def salvar_progresso_rota(
    atividade_id: int,
    dados: RespostaRequest,
    aluno: dict = Depends(usuario_aluno),
):
    """Salva sem entregar, para o aluno retomar de onde parou."""
    return salvar_progresso(aluno["email"], atividade_id, dados.respostas)


@app.post("/aluno/atividades/{atividade_id}/entrega")
def enviar_entrega_rota(
    atividade_id: int,
    dados: EntregaRequest,
    aluno: dict = Depends(usuario_aluno),
):
    return enviar_entrega(
        aluno["email"],
        atividade_id,
        dados.respostas,
        dados.arquivo_base64 or "",
        dados.arquivo_nome or "",
    )


@app.get("/entregas/{entrega_id}/arquivo")
def baixar_arquivo_entrega(entrega_id: int, usuario: dict = Depends(usuario_logado)):
    """O documento que o aluno entregou.

    Uma rota para os dois perfis, e não uma por perfil: quem pode baixar é o
    aluno que entregou **ou** o professor dono da atividade, e essa regra mora
    inteira em `obter_arquivo_entrega`. Duas rotas dariam dois lugares para a
    mesma verificação divergir.

    404 para todo o resto, sem distinguir "não existe" de "não é seu" — a
    diferença revelaria quem entregou o quê para quem tentasse ids na mão.
    """
    resultado = obter_arquivo_entrega(usuario["email"], entrega_id)

    if not resultado:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

    caminho, nome_original = resultado
    return FileResponse(caminho, filename=nome_original)


# ---------------------------- mensagens ----------------------------
# Conversa entre professor e aluno, por turma. As três rotas valem para os dois
# perfis: quem está logado define de que lado da conversa está, e o aluno nunca
# informa quem é — senão trocar um parâmetro leria a conversa de outro.

@app.get("/mensagens/conversas")
def listar_conversas_rota(usuario: dict = Depends(usuario_logado)):
    return listar_conversas(usuario["email"])


@app.get("/mensagens")
def abrir_conversa_rota(
    turma_id: int,
    aluno_email: Optional[str] = None,
    usuario: dict = Depends(usuario_logado),
):
    """`aluno_email` só é lido quando quem chama é professor."""
    return abrir_conversa(usuario["email"], turma_id, aluno_email)


@app.post("/mensagens")
def enviar_mensagem_rota(dados: MensagemRequest, usuario: dict = Depends(usuario_logado)):
    return enviar_mensagem(usuario["email"], dados.turma_id, dados.conteudo, dados.aluno_email)


# ---------------------------- calendário ----------------------------

@app.get("/calendario")
def calendario_rota(
    ano: int,
    mes: int,
    turma_id: Optional[int] = None,
    professor: dict = Depends(usuario_professor),
):
    """Materiais, atividades e prazos que caem no mês, nas turmas do professor."""
    return eventos_do_mes(professor["email"], ano, mes, turma_id)


# ---------------------------- denúncias ----------------------------
# Os dois lados da mesma entrega: aluno e professor reportam, a administração
# trata. Implementar só um dos lados repetiria a lacuna que originou o módulo.

@app.post("/denuncias")
def criar_denuncia_rota(dados: DenunciaRequest, usuario: dict = Depends(usuario_logado)):
    return criar_denuncia(usuario["email"], dados.material_id, dados.motivo, dados.descricao)


@app.get("/denuncias")
def listar_minhas_denuncias_rota(usuario: dict = Depends(usuario_logado)):
    """O que a própria pessoa reportou. Nunca o que os outros reportaram."""
    return listar_minhas(usuario["email"])


@app.delete("/denuncias/{denuncia_id}")
def remover_denuncia_rota(denuncia_id: int, usuario: dict = Depends(usuario_logado)):
    """Quem reportou volta atrás. Só a própria denúncia, e só antes do desfecho."""
    return remover_denuncia(usuario["email"], denuncia_id)


@app.get("/admin/denuncias")
def listar_denuncias_rota(
    status: Optional[str] = None,
    admin: dict = Depends(usuario_admin),
):
    return listar_todas(admin["email"], status)


@app.post("/admin/denuncias/{denuncia_id}")
def tratar_denuncia_rota(
    denuncia_id: int,
    dados: TratamentoDenunciaRequest,
    admin: dict = Depends(usuario_admin),
):
    return tratar_denuncia(admin["email"], denuncia_id, dados.status, dados.acao)


# ---------------------------- desempenho ----------------------------
# As duas rotas leem os mesmos dados e respondem perguntas diferentes: o aluno
# quer saber onde ele erra; o professor, onde a turma erra. A do aluno só
# enxerga as entregas dele — o id vem do token, nunca da query.

@app.get("/aluno/desempenho")
def desempenho_do_aluno_rota(
    turma_id: Optional[int] = None,
    dias: Optional[int] = None,
    aluno: dict = Depends(usuario_aluno),
):
    return desempenho_do_aluno(aluno["email"], turma_id, dias)


@app.get("/desempenho")
def desempenho_da_turma_rota(
    turma_id: int,
    dias: Optional[int] = None,
    professor: dict = Depends(usuario_professor),
):
    return desempenho_da_turma(professor["email"], turma_id, dias)


# ---------------------------- semestres ----------------------------
# O semestre vigente decide o que aparece na frente (disciplinas, pendências,
# XP e faixa) e o que vai para o histórico. Nada é apagado na virada — ver
# regras/semestres.py.

class SemestreRequest(BaseModel):
    semestre: str


@app.get("/semestre")
def semestre_vigente_rota(usuario: dict = Depends(usuario_logado)):
    """Qualquer perfil logado lê: as três telas precisam saber qual é."""
    return obter_semestre_vigente()


@app.put("/admin/semestre")
def definir_semestre_rota(dados: SemestreRequest, admin: dict = Depends(usuario_admin)):
    return definir_semestre_vigente(admin["email"], dados.semestre)


@app.get("/aluno/historico")
def historico_do_aluno_rota(busca: str = "", aluno: dict = Depends(usuario_aluno)):
    return historico_do_aluno(aluno["email"], busca)


@app.get("/historico")
def historico_do_professor_rota(busca: str = "", professor: dict = Depends(usuario_professor)):
    return historico_do_professor(professor["email"], busca)


# ---------------------------- supervisão de conteúdo ----------------------------
# A coordenação vê material e atividade publicados ou agendados. Entregas,
# anotações, conversas e mensagens não têm rota de administração — ver
# regras/conteudo.py.

@app.get("/admin/conteudo")
def conteudo_rota(semestre: Optional[str] = None, admin: dict = Depends(usuario_admin)):
    return visao_do_conteudo(admin["email"], semestre)


@app.get("/admin/conteudo/atividades/{atividade_id}")
def atividade_supervisao_rota(atividade_id: int, admin: dict = Depends(usuario_admin)):
    return atividade_para_supervisao(admin["email"], atividade_id)


@app.get("/admin/conteudo/materiais/{material_id}/arquivo")
def arquivo_supervisao_rota(material_id: int, admin: dict = Depends(usuario_admin)):
    resultado = arquivo_para_supervisao(admin["email"], material_id)
    if not resultado:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")
    caminho, nome_original = resultado
    return FileResponse(caminho, filename=nome_original)


# ---------------------------- avisos ----------------------------
# Uma rota para professor e administração escreverem: a diferença de quem pode
# o quê (disciplina própria, qualquer disciplina, instituição inteira) mora
# inteira em regras/avisos.py.

class AvisoRequest(BaseModel):
    titulo: str
    conteudo: str
    turma_ids: Optional[list[int]] = None
    geral: bool = False
    urgente: bool = False


@app.post("/avisos")
def publicar_aviso_rota(dados: AvisoRequest, usuario: dict = Depends(usuario_logado)):
    return publicar_aviso(
        usuario["email"], dados.titulo, dados.conteudo, dados.turma_ids, dados.geral, dados.urgente
    )


@app.get("/avisos/recebidos")
def avisos_recebidos_rota(usuario: dict = Depends(usuario_logado)):
    return listar_avisos_recebidos(usuario["email"])


@app.get("/avisos/enviados")
def avisos_enviados_rota(usuario: dict = Depends(usuario_logado)):
    return listar_avisos_enviados(usuario["email"])


@app.delete("/avisos/{aviso_id}")
def excluir_aviso_rota(aviso_id: int, usuario: dict = Depends(usuario_logado)):
    return excluir_aviso(usuario["email"], aviso_id)


# ---------------------------- favoritos e anotações ----------------------------
# Só do aluno. Anotação não tem rota nenhuma para professor ou administração:
# a privacidade é a ausência da rota, e não um filtro que alguém esqueça.

class AnotacaoRequest(BaseModel):
    material_id: Optional[int] = None
    texto: str
    trecho: str = ""


@app.get("/aluno/favoritos")
def listar_favoritos_rota(aluno: dict = Depends(usuario_aluno)):
    return listar_favoritos(aluno["email"])


@app.put("/aluno/favoritos/{material_id}")
def marcar_favorito_rota(material_id: int, aluno: dict = Depends(usuario_aluno)):
    return marcar_favorito(aluno["email"], material_id)


@app.delete("/aluno/favoritos/{material_id}")
def desmarcar_favorito_rota(material_id: int, aluno: dict = Depends(usuario_aluno)):
    return desmarcar_favorito(aluno["email"], material_id)


@app.get("/aluno/anotacoes")
def listar_anotacoes_rota(material_id: Optional[int] = None, aluno: dict = Depends(usuario_aluno)):
    return listar_anotacoes(aluno["email"], material_id)


@app.post("/aluno/anotacoes")
def criar_anotacao_rota(dados: AnotacaoRequest, aluno: dict = Depends(usuario_aluno)):
    if dados.material_id is None:
        raise HTTPException(status_code=400, detail="Informe o material.")
    return criar_anotacao(aluno["email"], dados.material_id, dados.texto, dados.trecho)


@app.put("/aluno/anotacoes/{anotacao_id}")
def editar_anotacao_rota(anotacao_id: int, dados: AnotacaoRequest, aluno: dict = Depends(usuario_aluno)):
    return editar_anotacao(aluno["email"], anotacao_id, dados.texto, dados.trecho)


@app.delete("/aluno/anotacoes/{anotacao_id}")
def excluir_anotacao_rota(anotacao_id: int, aluno: dict = Depends(usuario_aluno)):
    return excluir_anotacao(aluno["email"], anotacao_id)


# ---------------------------- ranking ----------------------------
# Só do aluno. O topo da turma é público entre colegas; a posição de cada um,
# só ele vê. Ver regras/ranking.py.

class VisibilidadeRankingRequest(BaseModel):
    aparecer: bool


@app.get("/aluno/ranking")
def ranking_rota(coorte_id: Optional[int] = None, aluno: dict = Depends(usuario_aluno)):
    return ranking_da_turma(aluno["email"], coorte_id)


@app.put("/aluno/ranking/visibilidade")
def visibilidade_ranking_rota(
    dados: VisibilidadeRankingRequest, aluno: dict = Depends(usuario_aluno)
):
    return definir_visibilidade(aluno["email"], dados.aparecer)


@app.post("/chat/perguntar")
async def perguntar_chat_rota(dados: PerguntaRequest, aluno: dict = Depends(usuario_aluno)):
    # `async` e não `def`: é o que tira esta rota do pool de 40 threads. O
    # trabalho em si continua síncrono e roda dentro de _com_ia.
    return await _com_ia(responder_pergunta, aluno["email"], dados.turma_id, dados.pergunta)


@app.get("/chat/historico")
def historico_chat_rota(turma_id: int, aluno: dict = Depends(usuario_aluno)):
    return buscar_historico(aluno["email"], turma_id)


# ---------------------------- lacunas do material ----------------------------
# O que os alunos perguntam ao assistente e o material não responde, por
# assunto e sem nome (regras/lacunas.py).

class LacunaTratadaRequest(BaseModel):
    turma_id: int
    assunto: str


@app.get("/lacunas")
def listar_lacunas_rota(turma_id: Optional[int] = None, professor: dict = Depends(usuario_professor)):
    return listar_lacunas(professor["email"], turma_id)


@app.post("/lacunas/tratadas")
def marcar_lacuna_tratada_rota(dados: LacunaTratadaRequest, professor: dict = Depends(usuario_professor)):
    return marcar_tratada(professor["email"], dados.turma_id, dados.assunto)


# ---------------------------- privacidade (LGPD) ----------------------------
# Regras e decisões em regras/privacidade.py. A cópia dos dados é na hora; a
# correção e a exclusão viram pedido para a administração.

class SolicitacaoPrivacidadeRequest(BaseModel):
    tipo: str
    campo: str = ""
    valor_novo: str = ""
    motivo: str = ""


class DecisaoPrivacidadeRequest(BaseModel):
    aprovar: bool
    resposta: str = ""


@app.get("/aluno/privacidade/exportar")
def exportar_dados_rota(aluno: dict = Depends(usuario_aluno)):
    return exportar_dados(aluno["email"])


@app.get("/aluno/privacidade/solicitacoes")
def minhas_solicitacoes_privacidade_rota(aluno: dict = Depends(usuario_aluno)):
    return listar_minhas_solicitacoes_privacidade(aluno["email"])


@app.post("/aluno/privacidade/solicitacoes")
def solicitar_privacidade_rota(dados: SolicitacaoPrivacidadeRequest, aluno: dict = Depends(usuario_aluno)):
    return solicitar_privacidade(aluno["email"], dados.tipo, dados.campo, dados.valor_novo, dados.motivo)


@app.delete("/aluno/privacidade/solicitacoes/{solicitacao_id}")
def cancelar_solicitacao_privacidade_rota(solicitacao_id: int, aluno: dict = Depends(usuario_aluno)):
    return cancelar_solicitacao_privacidade(aluno["email"], solicitacao_id)


@app.get("/admin/privacidade/solicitacoes")
def listar_solicitacoes_privacidade_rota(status: str = "", admin: dict = Depends(usuario_admin)):
    return listar_solicitacoes_privacidade(admin["email"], status)


@app.put("/admin/privacidade/solicitacoes/{solicitacao_id}")
def decidir_solicitacao_privacidade_rota(
    solicitacao_id: int, dados: DecisaoPrivacidadeRequest, admin: dict = Depends(usuario_admin)
):
    return decidir_solicitacao_privacidade(admin["email"], solicitacao_id, dados.aprovar, dados.resposta)


@app.post("/admin/privacidade/solicitacoes/{solicitacao_id}/reverter")
def reverter_exclusao_rota(solicitacao_id: int, admin: dict = Depends(usuario_admin)):
    return reverter_exclusao(admin["email"], solicitacao_id)


# ---------------------------- as telas ----------------------------
# Em produção, este mesmo processo entrega as telas (o React compilado, em
# web/dist) em /app/: tela e API na mesma origem, então o front não precisa
# saber o endereço da API e o CORS nem entra em jogo. Na frente fica um proxy
# com HTTPS (deploy/Caddyfile).
#
# Qualquer endereço de tela (/app/aluno/materiais) devolve o index.html, e é
# o React Router que decide o que mostrar — senão o F5 numa tela interna daria
# 404. Arquivo que não existe (/app/x.js) dá 404 de verdade: devolver o
# index.html no lugar de um script quebraria a tela em silêncio.
#
# Só a pasta das telas é servida. Os arquivos enviados (uploads/) continuam
# fora: só saem pelas rotas que conferem permissão.
#
# Declarado por último: as rotas da API, acima, têm prioridade.
PASTA_TELAS = os.environ.get("DELTACARE_TELAS") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "dist"
)

if not os.path.isfile(os.path.join(PASTA_TELAS, "index.html")):
    print(
        f"[Delta Care] AVISO: as telas não estão compiladas em {PASTA_TELAS}. "
        "Rode `npm ci && npm run build` dentro de web/."
    )


@app.get("/app", include_in_schema=False)
@app.get("/app/{caminho:path}", include_in_schema=False)
def telas(caminho: str = ""):
    base = os.path.realpath(PASTA_TELAS)
    indice = os.path.join(base, "index.html")

    if not os.path.isfile(indice):
        return HTMLResponse(
            "<h1>As telas do Delta Care não estão compiladas</h1>"
            "<p>No servidor, rode <code>npm ci &amp;&amp; npm run build</code> dentro de <code>web/</code>.</p>",
            status_code=503,
        )

    alvo = os.path.realpath(os.path.join(base, caminho))
    # realpath resolve "..": o que cair fora da pasta das telas não existe aqui.
    if alvo != base and not alvo.startswith(base + os.sep):
        raise HTTPException(status_code=404)
    if caminho and os.path.isfile(alvo):
        # Os arquivos do build têm o conteúdo no nome (index-DKKVApli.js):
        # podem ficar no cache do navegador à vontade.
        return FileResponse(alvo, headers={"Cache-Control": "public, max-age=31536000, immutable"})
    if "." in os.path.basename(caminho):
        raise HTTPException(status_code=404)
    # O index.html nunca fica em cache: é ele que aponta para os arquivos novos.
    return FileResponse(indice, headers={"Cache-Control": "no-cache"})
