import assert from "node:assert/strict"
import { test } from "node:test"

import { csvDoRelatorio, nomeDoCsv } from "./relatorios.js"

const bloco = (aproveitamento, xp = null) => ({
  notas: { aproveitamento, corrigidas: 4 },
  entregas: { no_prazo: 3, atrasadas: 1, nao_entregues: 0 },
  engajamento: { alunos_ativos: 2, alunos: 3, dias_de_estudo_por_aluno: 1.5, materiais_abertos: 5, xp_medio: xp },
  chat: { perguntas: 6, completa: 4, parcial: 1, nenhuma: 1, sem_material: 0 },
})

const relatorio = {
  turma: { nome: "MED 3A", semestre: "2026/2" },
  meses: [{ rotulo: "out/2026", total: bloco(72.5, 97.7), disciplinas: [{ nome: "Cardiologia I; turma B", ...bloco(null) }] }],
}

test("CSV: ponto e vírgula, vírgula decimal e BOM para o Excel em português", () => {
  const [cabecalho, total, disciplina] = csvDoRelatorio(relatorio).replace("﻿", "").trim().split("\r\n")
  assert.ok(csvDoRelatorio(relatorio).startsWith("﻿"))
  assert.equal(cabecalho.split(";")[0], "Mês")
  assert.equal(total.split(";")[2], "72,5")
  assert.equal(total.split(";").at(-6), "97,7")
  // Sem nota fica vazio, não zero; nome com ponto e vírgula vai entre aspas.
  assert.ok(disciplina.startsWith('out/2026;"Cardiologia I; turma B";;4;'))
})

test("CSV: nome do arquivo sem acento nem barra", () => {
  assert.equal(nomeDoCsv({ nome: "MED 3A", semestre: "2026/2" }), "relatorio-med-3a-2026-2.csv")
  assert.equal(nomeDoCsv({ nome: "Fisiologia Avançada", semestre: "2027/1" }), "relatorio-fisiologia-avancada-2027-1.csv")
})
