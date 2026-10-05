/**
 * Entende o Markdown das respostas da IA e devolve uma lista de blocos —
 * dados, não HTML. Quem desenha é o componente <Markdown>.
 *
 * A divisão é de propósito: esta parte é testável no Node sem navegador, e a
 * parte que desenha nunca recebe HTML. O texto vem do modelo, que leu PDFs
 * enviados por professores; se virasse HTML, um <script> escondido num PDF
 * viraria código na tela do aluno. Com o React, todo texto é escapado.
 *
 * Cobre o que os modelos costumam devolver: títulos, negrito, itálico,
 * código, listas, tabelas, citações e separadores. O que não for reconhecido
 * vira parágrafo — nunca some da tela.
 */

/** Texto de uma linha → trechos: texto, código, negrito, itálico. */
export function analisarInline(texto) {
  const padrao = /`([^`]+)`|\*\*([^*]+)\*\*|\*([^*\n]+)\*|_([^_\n]+)_/g
  const trechos = []
  let fim = 0
  let achado

  while ((achado = padrao.exec(texto)) !== null) {
    if (achado.index > fim) trechos.push({ tipo: "texto", texto: texto.slice(fim, achado.index) })
    const [, codigo, negrito, italico, italicoSublinhado] = achado
    if (codigo !== undefined) trechos.push({ tipo: "codigo", texto: codigo })
    else if (negrito !== undefined) trechos.push({ tipo: "negrito", texto: negrito })
    else trechos.push({ tipo: "italico", texto: italico ?? italicoSublinhado })
    fim = padrao.lastIndex
  }
  if (fim < texto.length) trechos.push({ tipo: "texto", texto: texto.slice(fim) })
  return trechos
}

const celulas = (linha) => linha.trim().replace(/^\||\|$/g, "").split("|").map((c) => analisarInline(c.trim()))
const ehSeparadorDeTabela = (linha) => /^\s*\|?[\s:|-]+\|[\s:|-]*$/.test(linha) && linha.includes("-")

const ITEM_SOLTO = /^\s*[-*+]\s+(.*)$/
const ITEM_NUMERADO = /^\s*\d+[.)]\s+(.*)$/
const TITULO = /^\s*(#{1,6})\s+(.*)$/
const CITACAO = /^\s*>\s?/

function comecaOutroBloco(linha) {
  return !linha.trim() || ITEM_SOLTO.test(linha) || ITEM_NUMERADO.test(linha) || TITULO.test(linha) ||
    CITACAO.test(linha) || linha.trim().startsWith("|")
}

/** O texto inteiro → blocos. */
export function analisarMarkdown(texto) {
  const linhas = String(texto || "").split("\n")
  const blocos = []
  let i = 0

  while (i < linhas.length) {
    const linha = linhas[i]

    if (!linha.trim()) { i += 1; continue }

    if (linha.trim().startsWith("|") && i + 1 < linhas.length && ehSeparadorDeTabela(linhas[i + 1])) {
      const cabecalho = celulas(linha)
      const corpo = []
      i += 2
      while (i < linhas.length && linhas[i].trim().startsWith("|")) corpo.push(celulas(linhas[i++]))
      blocos.push({ tipo: "tabela", cabecalho, linhas: corpo })
      continue
    }

    const titulo = linha.match(TITULO)
    if (titulo) {
      // "#" vira h3: dentro da bolha do chat, um h1 gritaria mais que a tela.
      blocos.push({ tipo: "titulo", nivel: Math.min(titulo[1].length + 2, 6), trechos: analisarInline(titulo[2]) })
      i += 1
      continue
    }

    if (/^\s*([-*_])\1{2,}\s*$/.test(linha)) { blocos.push({ tipo: "separador" }); i += 1; continue }

    const padraoDaLista = ITEM_SOLTO.test(linha) ? ITEM_SOLTO : ITEM_NUMERADO.test(linha) ? ITEM_NUMERADO : null
    if (padraoDaLista) {
      const itens = []
      while (i < linhas.length && padraoDaLista.test(linhas[i])) {
        itens.push(analisarInline(linhas[i].match(padraoDaLista)[1]))
        i += 1
      }
      blocos.push({ tipo: "lista", ordenada: padraoDaLista === ITEM_NUMERADO, itens })
      continue
    }

    if (CITACAO.test(linha)) {
      const conteudo = []
      while (i < linhas.length && CITACAO.test(linhas[i])) conteudo.push(linhas[i++].replace(CITACAO, ""))
      blocos.push({ tipo: "citacao", blocos: analisarMarkdown(conteudo.join("\n")) })
      continue
    }

    // Parágrafo: junta as linhas até uma em branco ou o começo de outro bloco.
    // A primeira entra sempre — senão uma linha como "|sem tabela" (que
    // "parece" começar outro bloco mas não começa) travaria o laço.
    const pedacos = [linha.trim()]
    i += 1
    while (i < linhas.length && !comecaOutroBloco(linhas[i])) pedacos.push(linhas[i++].trim())
    blocos.push({ tipo: "paragrafo", trechos: analisarInline(pedacos.join(" ")) })
  }

  return blocos
}
