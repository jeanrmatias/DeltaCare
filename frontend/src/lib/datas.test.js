import assert from "node:assert/strict"
import test from "node:test"

import { formatarParaCampo, interpretarDataDigitada } from "./datas.js"

const AGORA = new Date(2026, 9, 2) // 02/10/2026

function partes(data) {
  return data && [data.getDate(), data.getMonth() + 1, data.getFullYear(), data.getHours(), data.getMinutes()]
}

test("aceita o jeito que as pessoas escrevem", () => {
  assert.deepEqual(partes(interpretarDataDigitada("05/03/2027 14:30", AGORA)), [5, 3, 2027, 14, 30])
  assert.deepEqual(partes(interpretarDataDigitada("5/3", AGORA)), [5, 3, 2026, 0, 0])
  assert.deepEqual(partes(interpretarDataDigitada("05/03/27", AGORA)), [5, 3, 2027, 0, 0])
  assert.deepEqual(partes(interpretarDataDigitada("5 3 2026 9:05", AGORA)), [5, 3, 2026, 9, 5])
  assert.deepEqual(partes(interpretarDataDigitada("5-3-2026", AGORA)), [5, 3, 2026, 0, 0])
})

test("recusa data que não existe, em vez de corrigir em silêncio", () => {
  assert.equal(interpretarDataDigitada("31/02/2026", AGORA), null)
  assert.equal(interpretarDataDigitada("10/13/2026", AGORA), null)
  assert.equal(interpretarDataDigitada("10/10/2026 25:00", AGORA), null)
  assert.equal(interpretarDataDigitada("amanhã", AGORA), null)
  assert.equal(interpretarDataDigitada("", AGORA), null)
})

test("o campo mostra dd/mm/aaaa hh:mm", () => {
  assert.equal(formatarParaCampo(new Date(2026, 2, 5, 9, 5)), "05/03/2026 09:05")
})
