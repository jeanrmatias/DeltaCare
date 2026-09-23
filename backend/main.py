from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from database import configurar_banco
from sessoes import (
    buscar_usuario_da_sessao,
    encerrar_sessao,
    limpar_sessoes_expiradas,
)
from logica import (
    cadastrar_usuario,
    criar_conta_staff,
    realizar_login,
    redefinir_senha,
    solicitar_recuperacao,
)
from logica_materiais import (
    atualizar_material,
    criar_material,
    excluir_material,
    listar_materiais,
    obter_arquivo_material,
)
from logica_turmas import (
    criar_turma,
    excluir_turma,
    listar_professores,
    listar_turmas,
    listar_turmas_admin,
)
from logica_matriculas import (
    desmatricular_aluno,
    listar_alunos,
    listar_alunos_da_turma,
    listar_turmas_do_aluno,
    matricular_aluno,
)
from logica_aluno import (
    listar_materiais_do_aluno,
    obter_arquivo_material_do_aluno,
    resumo_do_aluno,
)
from chat_ia import buscar_historico, indexar_material, responder_pergunta

configurar_banco()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_headers=["*"],
    allow_methods=["*"],
)

limpar_sessoes_expiradas()


# =========================================================================
# Autenticação
# =========================================================================
# Estas dependências são o único caminho pelo qual uma rota descobre quem está
# fazendo a requisição. Antes, a identidade vinha no corpo ou na query string
# (professor_email=...), o que significava que qualquer pessoa podia agir em
# nome de outra só trocando o e-mail. Agora vem do token da sessão.


def usuario_logado(authorization: Optional[str] = Header(default=None)) -> dict:
    """Valida o header `Authorization: Bearer <token>` e devolve o usuário."""
    token = ""

    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()

    usuario = buscar_usuario_da_sessao(token)

    if not usuario:
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada. Faça login de novo.")

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


class CadastroRequest(BaseModel):
    email: str
    senha: str
    tipo: str


class StaffRequest(BaseModel):
    email: str
    senha: str
    tipo: str


class RecuperacaoSenhaRequest(BaseModel):
    email: str


class RedefinicaoSenhaRequest(BaseModel):
    token: str
    nova_senha: str


class TurmaRequest(BaseModel):
    # professor_email continua aqui de propósito: é o professor que vai receber
    # a turma (o alvo da ação), não quem está fazendo a requisição.
    professor_email: str
    nome: str
    semestre: str


class MaterialRequest(BaseModel):
    turma_id: int
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


class MatriculaRequest(BaseModel):
    # aluno_email é o aluno sendo matriculado (alvo), não quem faz a requisição.
    aluno_email: str
    turma_id: int


class PerguntaRequest(BaseModel):
    turma_id: int
    pergunta: str


@app.get("/")
def inicio():
    return {"mensagem": "Backend funcionando :)"}


# ---------------------------- rotas públicas ----------------------------
# As únicas que não exigem token: sem elas ninguém conseguiria obter um.

@app.post("/login")
def login(dados: LoginRequest):
    return realizar_login(dados.email, dados.senha)


@app.post("/cadastro")
def cadastro(dados: CadastroRequest):
    """Cadastro público — só cria conta de aluno."""
    return cadastrar_usuario(dados.email, dados.senha, dados.tipo)


@app.post("/recuperar-senha")
def recuperar_senha(dados: RecuperacaoSenhaRequest):
    return solicitar_recuperacao(dados.email)


@app.post("/redefinir-senha")
def redefinicao_senha(dados: RedefinicaoSenhaRequest):
    return redefinir_senha(dados.token, dados.nova_senha)


# ---------------------------- sessão ----------------------------

@app.post("/logout")
def logout(authorization: Optional[str] = Header(default=None)):
    """Invalida o token atual. Não dá erro se já estiver deslogado."""
    if authorization and authorization.lower().startswith("bearer "):
        encerrar_sessao(authorization[7:].strip())
    return {"sucesso": True, "mensagem": "Sessão encerrada."}


@app.get("/eu")
def usuario_atual_rota(usuario: dict = Depends(usuario_logado)):
    """Quem sou eu, segundo o token. O front usa para validar a sessão."""
    return {"sucesso": True, "email": usuario["email"], "tipo": usuario["tipo"]}


# ---------------------------- administração ----------------------------

@app.post("/admin/usuarios")
def criar_staff_rota(dados: StaffRequest, admin: dict = Depends(usuario_admin)):
    """Cria conta de professor ou admin."""
    return criar_conta_staff(admin["email"], dados.email, dados.senha, dados.tipo)


@app.get("/admin/turmas")
def listar_turmas_admin_rota(admin: dict = Depends(usuario_admin)):
    return listar_turmas_admin(admin["email"])


@app.post("/admin/turmas")
def criar_turma_rota(dados: TurmaRequest, admin: dict = Depends(usuario_admin)):
    return criar_turma(admin["email"], dados.professor_email, dados.nome, dados.semestre)


@app.delete("/admin/turmas/{turma_id}")
def excluir_turma_rota(turma_id: int, admin: dict = Depends(usuario_admin)):
    return excluir_turma(admin["email"], turma_id)


@app.get("/admin/professores")
def listar_professores_rota(admin: dict = Depends(usuario_admin)):
    return listar_professores(admin["email"])


@app.post("/admin/matriculas")
def matricular_aluno_rota(dados: MatriculaRequest, admin: dict = Depends(usuario_admin)):
    return matricular_aluno(admin["email"], dados.aluno_email, dados.turma_id)


@app.delete("/admin/matriculas")
def desmatricular_aluno_rota(dados: MatriculaRequest, admin: dict = Depends(usuario_admin)):
    return desmatricular_aluno(admin["email"], dados.aluno_email, dados.turma_id)


@app.get("/admin/turmas/{turma_id}/alunos")
def listar_alunos_da_turma_rota(turma_id: int, admin: dict = Depends(usuario_admin)):
    return listar_alunos_da_turma(admin["email"], turma_id)


@app.get("/admin/alunos")
def listar_alunos_rota(admin: dict = Depends(usuario_admin)):
    return listar_alunos(admin["email"])


# ---------------------------- professor ----------------------------

@app.get("/turmas")
def listar_turmas_rota(professor: dict = Depends(usuario_professor)):
    """Turmas do professor logado (somente leitura — quem cria é o admin)."""
    return listar_turmas(professor["email"])


@app.post("/materiais")
def criar_material_rota(dados: MaterialRequest, professor: dict = Depends(usuario_professor)):
    resultado = criar_material(
        professor_email=professor["email"],
        turma_id=dados.turma_id,
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

    # Indexa o PDF pro chat de IA do aluno poder buscar nele depois. Se a
    # indexação falhar (ex.: Ollama fora do ar), o material
    # continua salvo normalmente — só não vai aparecer nas buscas do chat.
    if resultado.get("sucesso") and dados.tipo == "pdf":
        try:
            indexar_material(resultado["material_id"])
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

    caminho, nome_original = resultado
    return FileResponse(caminho, filename=nome_original)


@app.post("/chat/perguntar")
def perguntar_chat_rota(dados: PerguntaRequest, aluno: dict = Depends(usuario_aluno)):
    return responder_pergunta(aluno["email"], dados.turma_id, dados.pergunta)


@app.get("/chat/historico")
def historico_chat_rota(turma_id: int, aluno: dict = Depends(usuario_aluno)):
    return buscar_historico(aluno["email"], turma_id)
