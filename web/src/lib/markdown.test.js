import assert from "node:assert/strict"
import test from "node:test"

import { analisarInline, analisarMarkdown } from "./markdown.js"

test("negrito, itálico e código viram trechos marcados", () => {
  assert.deepEqual(analisarInline("Dose de **12,5 mg** em _bolus_ lento, ver `DCM-3`."), [
    { tipo: "texto", texto: "Dose de " },
    { tipo: "negrito", texto: "12,5 mg" },
    { tipo: "texto", texto: " em " },
    { tipo: "italico", texto: "bolus" },
    { tipo: "texto", texto: " lento, ver " },
    { tipo: "codigo", texto: "DCM-3" },
    { tipo: "texto", texto: "." },
  ])
})

test("tabela com cabeçalho, separador e linhas", () => {
  const [tabela] = analisarMarkdown("| Estágio | Conduta |\n|:---|---:|\n| DCM-2 | Cardiolex |\n| DCM-3 | Suporte |")

  assert.equal(tabela.tipo, "tabela")
  assert.equal(tabela.cabecalho.length, 2)
  assert.equal(tabela.linhas.length, 2)
  assert.equal(tabela.linhas[1][0][0].texto, "DCM-3")
})

test("tabela pela metade vira parágrafo, e não trava", () => {
  // No front antigo, esta entrada fazia o laço do parágrafo não avançar.
  const blocos = analisarMarkdown("A dose é 12,5 mg.\n| Estágio | Conduta")

  assert.deepEqual(blocos.map((b) => b.tipo), ["paragrafo", "paragrafo"])
})

test("listas, títulos, citação e separador", () => {
  const blocos = analisarMarkdown("# Conduta\n- avaliar\n- medicar\n1. primeiro\n2. segundo\n> atenção\n---\nfim")

  assert.deepEqual(blocos.map((b) => b.tipo), ["titulo", "lista", "lista", "citacao", "separador", "paragrafo"])
  assert.equal(blocos[0].nivel, 3)
  assert.equal(blocos[1].ordenada, false)
  assert.equal(blocos[2].ordenada, true)
  assert.equal(blocos[2].itens.length, 2)
})

test("linhas seguidas viram um parágrafo só", () => {
  const blocos = analisarMarkdown("primeira linha\nsegunda linha\n\noutro parágrafo")

  assert.equal(blocos.length, 2)
  assert.equal(blocos[0].trechos[0].texto, "primeira linha segunda linha")
})
