import assert from "node:assert/strict"
import test from "node:test"

import { questaoParaEnvio, removerAlternativa } from "./questoes.js"

const QUESTAO = { enunciado: "Qual diurético é a base na congestão?", alternativas: ["Hidroclorotiazida", "Espironolactona", "Furosemida"], correta: 2 }

test("remover uma alternativa antes da correta não muda a resposta certa", () => {
  const nova = removerAlternativa(QUESTAO, 0)

  assert.deepEqual(nova.alternativas, ["Espironolactona", "Furosemida"])
  assert.equal(nova.alternativas[nova.correta], "Furosemida")
})

test("remover uma alternativa depois da correta também não", () => {
  const nova = removerAlternativa({ ...QUESTAO, correta: 0 }, 2)

  assert.equal(nova.alternativas[nova.correta], "Hidroclorotiazida")
})

test("remover a correta deixa a questão sem marcação, e não marca outra", () => {
  assert.equal(removerAlternativa(QUESTAO, 2).correta, null)
})

test("a alternativa em branco vai para o servidor na posição dela", () => {
  // O servidor tira o branco e acerta o índice; filtrar aqui deslocava a marcação.
  const enviada = questaoParaEnvio({ enunciado: " Diurético? ", alternativas: ["", " Furosemida ", "Espironolactona"], correta: 1 })

  assert.deepEqual(enviada, { enunciado: "Diurético?", alternativas: ["", "Furosemida", "Espironolactona"], correta: 1 })
})
