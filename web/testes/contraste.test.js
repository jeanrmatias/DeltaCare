/**
 * Contraste das cores do tema (WCAG AA), lido direto do src/index.css.
 *
 * Mudar um token é uma linha, e quebrar o contraste de todas as telas também.
 * Este teste confere os pares que as telas de fato usam: 4,5:1 para texto,
 * 3:1 para contorno de campo e ícone.
 */
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { test } from "node:test"

const css = readFileSync(new URL("../src/index.css", import.meta.url), "utf8")

function token(nome) {
  const achado = css.match(new RegExp(`--color-${nome}:\\s*(#[0-9A-Fa-f]{6})`))
  assert.ok(achado, `token --color-${nome} não encontrado`)
  return achado[1]
}

function luminancia(hex) {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
  const canal = (c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4)
  return 0.2126 * canal(r) + 0.7152 * canal(g) + 0.0722 * canal(b)
}

function contraste(a, b) {
  const [claro, escuro] = [luminancia(a), luminancia(b)].sort((x, y) => y - x)
  return (claro + 0.05) / (escuro + 0.05)
}

const BRANCO = "#FFFFFF"

// [frente, fundo, mínimo, onde aparece]
const PARES = [
  ["texto", "superficie", 4.5, "texto de cartão"],
  ["texto", "fundo", 4.5, "texto direto na página"],
  ["texto-secundario", "superficie", 4.5, "descrições nos cartões"],
  ["texto-secundario", "fundo", 4.5, "descrição do cabeçalho de cada página"],
  ["primaria", "superficie", 4.5, "links"],
  ["primaria", "fundo", 4.5, "links fora de cartão"],
  [BRANCO, "primaria", 4.5, "texto dos botões e do item ativo do menu"],
  [BRANCO, "primaria-escura", 4.5, "botão com o mouse em cima"],
  ["perigo", "superficie", 4.5, "mensagens de erro"],
  [BRANCO, "perigo", 4.5, "botão de excluir"],
  ["sucesso", "superficie", 4.5, "mensagens de sucesso"],
  ["texto-inverso", "navy-900", 4.5, "menu lateral"],
  ["borda-campo", "superficie", 3, "contorno dos campos"],
  ["borda-campo", "fundo", 3, "contorno dos campos fora de cartão"],
  ["alerta-forte", "superficie", 3, "estrela do favorito"],
]

for (const [frente, fundo, minimo, onde] of PARES) {
  test(`contraste: ${onde}`, () => {
    const a = frente.startsWith("#") ? frente : token(frente)
    const b = fundo.startsWith("#") ? fundo : token(fundo)
    const razao = contraste(a, b)
    assert.ok(razao >= minimo, `${frente} sobre ${fundo}: ${razao.toFixed(2)}:1, mínimo ${minimo}:1`)
  })
}

test("o anel de foco fica fora das camadas do Tailwind", () => {
  // Dentro de @layer, um `outline-none` numa utilitária apagaria o foco.
  const semComentarios = css.replace(/\/\*[\s\S]*?\*\//g, "")
  const semCamadas = semComentarios.replace(/@layer[^{]*\{(?:[^{}]|\{[^{}]*\})*\}/g, "")
  assert.match(semCamadas, /:focus-visible\s*\{[^}]*outline:\s*2px solid/)
})
