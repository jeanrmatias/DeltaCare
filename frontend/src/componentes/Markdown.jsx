import { analisarMarkdown } from "../lib/markdown"

/**
 * Desenha a resposta da IA. Recebe texto, entende com analisarMarkdown e
 * monta os elementos com JSX — nunca com dangerouslySetInnerHTML. Por isso
 * HTML que venha no texto aparece como texto, e não vira elemento.
 */
export function Markdown({ texto }) {
  return analisarMarkdown(texto).map((bloco, indice) => <Bloco key={indice} bloco={bloco} />)
}

function Bloco({ bloco }) {
  switch (bloco.tipo) {
    case "titulo": {
      const Titulo = `h${bloco.nivel}`
      return <Titulo className="mt-3.5 mb-1.5 text-sm leading-snug font-bold first:mt-0"><Trechos trechos={bloco.trechos} /></Titulo>
    }
    case "lista": {
      const Lista = bloco.ordenada ? "ol" : "ul"
      return (
        <Lista className={`mb-2.5 pl-5 last:mb-0 ${bloco.ordenada ? "list-decimal" : "list-disc"}`}>
          {bloco.itens.map((item, i) => <li key={i} className="mb-1"><Trechos trechos={item} /></li>)}
        </Lista>
      )
    }
    case "tabela":
      return (
        // Rola na horizontal: tabela larga não estoura a bolha em tela estreita.
        <div className="mb-2.5 overflow-x-auto last:mb-0">
          <table className="w-full border-collapse text-[14px]">
            <thead>
              <tr>{bloco.cabecalho.map((celula, i) => <th key={i} className="border border-borda bg-superficie px-2.5 py-1.5 text-left font-semibold"><Trechos trechos={celula} /></th>)}</tr>
            </thead>
            <tbody>
              {bloco.linhas.map((linha, i) => (
                <tr key={i}>{linha.map((celula, j) => <td key={j} className="border border-borda px-2.5 py-1.5 align-top"><Trechos trechos={celula} /></td>)}</tr>
              ))}
            </tbody>
          </table>
        </div>
      )
    case "citacao":
      return (
        <blockquote className="mb-2.5 border-l-3 border-primaria pl-3 text-texto-secundario last:mb-0">
          {bloco.blocos.map((filho, i) => <Bloco key={i} bloco={filho} />)}
        </blockquote>
      )
    case "separador":
      return <hr className="my-3 border-borda" />
    default:
      return <p className="mb-2.5 last:mb-0"><Trechos trechos={bloco.trechos} /></p>
  }
}

function Trechos({ trechos }) {
  return trechos.map((trecho, i) => {
    if (trecho.tipo === "codigo") return <code key={i} className="rounded bg-superficie px-1 py-px font-mono text-[13.5px]">{trecho.texto}</code>
    if (trecho.tipo === "negrito") return <strong key={i}>{trecho.texto}</strong>
    if (trecho.tipo === "italico") return <em key={i}>{trecho.texto}</em>
    return trecho.texto
  })
}
