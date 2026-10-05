/**
 * Contraste das cores do tema (WCAG AA), lido direto do src/index.css.
 *
 * Mudar um token é uma linha, e quebrar o contraste de todas as telas também.
 * Este teste confere os pares que as telas de fato usam: 4,5:1 para texto,
 * 3:1 para contorno de campo e ícone.
 */
import assert from "node:assert/strict"
import { readdirSync, readFileSync, statSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"
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
  [BRANCO, "navy-700", 4.5, "item ativo do menu"],
  // A cor exata da marca, onde não há texto pequeno em cima: 3:1 basta.
  ["marca", "superficie", 3, "barras e ícones na cor da marca"],
  ["marca", "fundo", 3, "anel de foco no fundo da página"],
  ["marca", "navy-900", 3, "anel de foco e barra do item ativo no menu"],
  ["marca-perigo", "superficie", 3, "barra de tópico com muito erro"],
  ["marca-sucesso", "superficie", 3, "barra de aproveitamento bom"],
]

test("as cores da marca continuam as do hospital", () => {
  // Elas não mudam: o produto é vendido para quem tem exatamente estas cores.
  assert.deepEqual(
    ["marca", "marca-cinza", "marca-perigo", "marca-sucesso", "fundo", "navy-900"].map(token),
    ["#2F70F2", "#64748B", "#EF4444", "#16A34A", "#F4F7FE", "#0D1D3A"],
  )
})

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

/** O texto de cada <Modal ...> do código, da abertura ao ">" que fecha a tag. */
function tagsDeModal(pasta) {
  const tags = []
  for (const nome of readdirSync(pasta)) {
    const caminho = join(pasta, nome)
    if (statSync(caminho).isDirectory()) { tags.push(...tagsDeModal(caminho)); continue }
    if (!nome.endsWith(".jsx") || nome === "Modal.jsx") continue
    const codigo = readFileSync(caminho, "utf8")
    for (let inicio = codigo.indexOf("<Modal "); inicio >= 0; inicio = codigo.indexOf("<Modal ", inicio + 1)) {
      // Até o ">" fora de chaves: dentro delas, "=>" é de uma função.
      let profundidade = 0
      let fim = inicio
      for (; fim < codigo.length; fim++) {
        if (codigo[fim] === "{") profundidade++
        else if (codigo[fim] === "}") profundidade--
        else if (codigo[fim] === ">" && profundidade === 0) break
      }
      tags.push([nome, codigo.slice(inicio, fim)])
    }
  }
  return tags
}

test("toda janela (Modal) tem nome para o leitor de tela", () => {
  const tags = tagsDeModal(fileURLToPath(new URL("../src", import.meta.url)))
  assert.ok(tags.length >= 5, "não achou os modais — o teste estaria passando por não olhar nada")
  for (const [arquivo, tag] of tags) assert.match(tag, /\b(titulo|rotulo)=/, `${arquivo}: ${tag.slice(0, 60)}...`)
})
