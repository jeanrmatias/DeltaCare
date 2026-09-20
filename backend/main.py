from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import configurar_banco
from logica import (
    cadastrar_usuario,
    realizar_login,
    redefinir_senha,
    solicitar_recuperacao,
)

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


class RecuperacaoSenhaRequest(BaseModel):
    email: str


class RedefinicaoSenhaRequest(BaseModel):
    token: str
    nova_senha: str


@app.get("/")
def inicio():
    return {"mensagem": "Backend funcionando :)"}


@app.post("/login")
def login(dados: LoginRequest):
    return realizar_login(dados.email, dados.senha)


@app.post("/cadastro")
def cadastro(dados: CadastroRequest):
    return cadastrar_usuario(dados.email, dados.senha, dados.tipo)


@app.post("/recuperar-senha")
def recuperar_senha(dados: RecuperacaoSenhaRequest):
    return solicitar_recuperacao(dados.email)


@app.post("/redefinir-senha")
def redefinicao_senha(dados: RedefinicaoSenhaRequest):
    return redefinir_senha(dados.token, dados.nova_senha)