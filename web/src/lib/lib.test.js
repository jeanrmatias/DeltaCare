/**
 * Testes do que não depende de React: endereço da API, sessão guardada e
 * nome de exibição. Rodam no Node puro (npm test), sem biblioteca de teste.
 */
import assert from "node:assert/strict"
import test from "node:test"

import { enderecoDaApi, lerSessao, limparSessao, salvarSessao } from "./api.js"
import { iniciaisDe, nomeExibicao } from "./usuario.js"

function armazenamentoFalso() {
  const dados = {}
  return {
    getItem: (chave) => dados[chave] ?? null,
    setItem: (chave, valor) => { dados[chave] = String(valor) },
    removeItem: (chave) => { delete dados[chave] },
  }
}

test("em produção a API é a mesma origem da página", () => {
  const local = { port: "", protocol: "https:", hostname: "deltacare.moinhos.org.br", origin: "https://deltacare.moinhos.org.br" }
  assert.equal(enderecoDaApi(local), "https://deltacare.moinhos.org.br")
})

test("no Vite e no servidor antigo a API fica na 8000 do mesmo computador", () => {
  for (const port of ["5173", "5500"]) {
    const local = { port, protocol: "http:", hostname: "localhost", origin: `http://localhost:${port}` }
    assert.equal(enderecoDaApi(local), "http://localhost:8000")
  }
})

test("endereço definido explicitamente vence a dedução", () => {
  const local = { port: "", protocol: "https:", hostname: "a.com", origin: "https://a.com" }
  assert.equal(enderecoDaApi(local, "https://api.b.com/"), "https://api.b.com")
})

test("sessão sem token não conta como sessão", () => {
  // Usuário guardado sem token é resto de uma sessão quebrada: tratá-lo como
  // logado abriria a tela e faria toda chamada voltar 401.
  const armazenamento = armazenamentoFalso()
  armazenamento.setItem("deltacare_usuario", JSON.stringify({ tipo: "aluno" }))

  assert.equal(lerSessao(armazenamento), null)
})

test("sessão salva volta igual, e sair limpa tudo", () => {
  const armazenamento = armazenamentoFalso()
  salvarSessao({ email: "a@b.com", tipo: "aluno", nome: "Ana" }, "tok123", armazenamento)

  assert.deepEqual(lerSessao(armazenamento), { usuario: { email: "a@b.com", tipo: "aluno", nome: "Ana" }, token: "tok123" })
  limparSessao(armazenamento)
  assert.equal(lerSessao(armazenamento), null)
})

test("sessão corrompida não derruba a tela", () => {
  const armazenamento = armazenamentoFalso()
  armazenamento.setItem("deltacare_usuario", "{quebrado")
  armazenamento.setItem("deltacare_token", "tok")

  assert.equal(lerSessao(armazenamento), null)
})

test("nome de exibição: cadastrado, ou apelido a partir do e-mail", () => {
  assert.equal(nomeExibicao({ nome: "  Marina Duarte " }), "Marina Duarte")
  assert.equal(nomeExibicao({ nome: "", email: "ana.paula@x.com" }), "Ana Paula")
  assert.equal(nomeExibicao(null), "")
})

test("iniciais: primeira e última palavra", () => {
  assert.equal(iniciaisDe("Marina Duarte"), "MD")
  assert.equal(iniciaisDe("Ana Beatriz Rocha"), "AR")
  assert.equal(iniciaisDe("Pedro"), "PE")
  assert.equal(iniciaisDe(""), "--")
})
