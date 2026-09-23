from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from database import configurar_banco
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
from chat_ia import buscar_historico, indexar_material, responder_pergunta

configurar_banco()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_headers=["*"],
    allow_methods=["*"],
)


class LoginRequest(BaseModel):
    email: str
    senha: str


class CadastroRequest(BaseModel):
    email: str
    senha: str
    tipo: str


class StaffRequest(BaseModel):
    admin_email: str
    email: str
    senha: str
    tipo: str


class RecuperacaoSenhaRequest(BaseModel):
    email: str


class RedefinicaoSenhaRequest(BaseModel):
    token: str
    nova_senha: str


class TurmaRequest(BaseModel):
    admin_email: str
    professor_email: str
    nome: str
    semestre: str


class TurmaExclusaoRequest(BaseModel):
    admin_email: str


class MaterialRequest(BaseModel):
    professor_email: str
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
    professor_email: str
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    assunto: Optional[str] = None
    topico: Optional[str] = None
    aula: Optional[str] = None
    semestre: Optional[str] = None
    rascunho: Optional[bool] = None
    data_liberacao: Optional[str] = None
    link_url: Optional[str] = None


class MaterialExclusaoRequest(BaseModel):
    professor_email: str


class MatriculaRequest(BaseModel):
    admin_email: str
    aluno_email: str
    turma_id: int


class PerguntaRequest(BaseModel):
    aluno_email: str
    turma_id: int
    pergunta: str


@app.get("/")
def inicio():
    return {"mensagem": "Backend funcionando :)"}


@app.post("/login")
def login(dados: LoginRequest):
    return realizar_login(dados.email, dados.senha)


@app.post("/cadastro")
def cadastro(dados: CadastroRequest):
    """Cadastro público — só cria conta de aluno."""
    return cadastrar_usuario(dados.email, dados.senha, dados.tipo)


@app.post("/admin/usuarios")
def criar_staff_rota(dados: StaffRequest):
    """Cria conta de professor ou admin. Só um admin logado pode chamar."""
    return criar_conta_staff(dados.admin_email, dados.email, dados.senha, dados.tipo)


@app.post("/recuperar-senha")
def recuperar_senha(dados: RecuperacaoSenhaRequest):
    return solicitar_recuperacao(dados.email)


@app.post("/redefinir-senha")
def redefinicao_senha(dados: RedefinicaoSenhaRequest):
    return redefinir_senha(dados.token, dados.nova_senha)


@app.get("/turmas")
def listar_turmas_rota(professor_email: str):
    """Turmas do professor logado (somente leitura — quem cria é o admin)."""
    return listar_turmas(professor_email)


@app.get("/admin/turmas")
def listar_turmas_admin_rota(admin_email: str):
    return listar_turmas_admin(admin_email)


@app.post("/admin/turmas")
def criar_turma_rota(dados: TurmaRequest):
    return criar_turma(dados.admin_email, dados.professor_email, dados.nome, dados.semestre)


@app.delete("/admin/turmas/{turma_id}")
def excluir_turma_rota(turma_id: int, dados: TurmaExclusaoRequest):
    return excluir_turma(dados.admin_email, turma_id)


@app.get("/admin/professores")
def listar_professores_rota(admin_email: str):
    return listar_professores(admin_email)


@app.post("/materiais")
def criar_material_rota(dados: MaterialRequest):
    resultado = criar_material(
        professor_email=dados.professor_email,
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
def listar_materiais_rota(professor_email: str, turma_id: Optional[int] = None):
    return listar_materiais(professor_email, turma_id)


@app.put("/materiais/{material_id}")
def atualizar_material_rota(material_id: int, dados: MaterialAtualizacaoRequest):
    campos = dados.model_dump(exclude={"professor_email"}, exclude_none=True)
    return atualizar_material(material_id, dados.professor_email, **campos)


@app.delete("/materiais/{material_id}")
def excluir_material_rota(material_id: int, dados: MaterialExclusaoRequest):
    return excluir_material(material_id, dados.professor_email)


@app.get("/materiais/{material_id}/arquivo")
def baixar_arquivo_material(material_id: int, professor_email: str):
    resultado = obter_arquivo_material(material_id, professor_email)

    if not resultado:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

    caminho, nome_original = resultado
    return FileResponse(caminho, filename=nome_original)


@app.post("/admin/matriculas")
def matricular_aluno_rota(dados: MatriculaRequest):
    return matricular_aluno(dados.admin_email, dados.aluno_email, dados.turma_id)


@app.delete("/admin/matriculas")
def desmatricular_aluno_rota(dados: MatriculaRequest):
    return desmatricular_aluno(dados.admin_email, dados.aluno_email, dados.turma_id)


@app.get("/admin/turmas/{turma_id}/alunos")
def listar_alunos_da_turma_rota(turma_id: int, admin_email: str):
    return listar_alunos_da_turma(admin_email, turma_id)


@app.get("/admin/alunos")
def listar_alunos_rota(admin_email: str):
    return listar_alunos(admin_email)


@app.get("/aluno/turmas")
def listar_turmas_do_aluno_rota(aluno_email: str):
    return listar_turmas_do_aluno(aluno_email)


@app.post("/chat/perguntar")
def perguntar_chat_rota(dados: PerguntaRequest):
    return responder_pergunta(dados.aluno_email, dados.turma_id, dados.pergunta)


@app.get("/chat/historico")
def historico_chat_rota(aluno_email: str, turma_id: int):
    return buscar_historico(aluno_email, turma_id)
