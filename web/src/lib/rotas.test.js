import assert from "node:assert/strict"
import test from "node:test"

import { rotaDoLink } from "./rotas.js"

test("link de notificação vira a rota do perfil de quem recebeu", () => {
  assert.equal(rotaDoLink("materiais.html", "aluno"), "/aluno/materiais")
  assert.equal(rotaDoLink("materiais.html", "professor"), "/professor/materiais")
  assert.equal(rotaDoLink("solicitacoes.html", "adm"), "/admin/privacidade")
})

test("o mesmo link leva a lugares diferentes conforme o perfil", () => {
  // Aluno não tem tela de avisos: o aviso aparece no início dele.
  assert.equal(rotaDoLink("avisos.html", "aluno"), "/aluno")
  assert.equal(rotaDoLink("avisos.html", "professor"), "/professor/avisos")
})

test("consulta do link é mantida, e link desconhecido não leva a lugar nenhum", () => {
  assert.equal(rotaDoLink("materiais.html?turma=3", "aluno"), "/aluno/materiais?turma=3")
  assert.equal(rotaDoLink("pagina-que-nao-existe.html", "aluno"), null)
  assert.equal(rotaDoLink("", "aluno"), null)
})
