/**
 * Tabela simples, com rolagem horizontal em tela estreita.
 *
 *     <Tabela colunas={["Aluno", { titulo: "Nota", numero: true }]}>
 *       {linhas.map((l) => <tr key={l.id}><Celula>...</Celula><Celula numero>...</Celula></tr>)}
 *     </Tabela>
 */
export function Tabela({ colunas, children }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-borda text-xs text-texto-secundario">
            {colunas.map((coluna) => {
              const { titulo, numero } = typeof coluna === "string" ? { titulo: coluna } : coluna
              return <th key={titulo} className={`px-3 py-2 font-semibold first:pl-0 last:pr-0 ${numero ? "text-right" : "text-left"}`}>{titulo}</th>
            })}
          </tr>
        </thead>
        <tbody className="[&>tr]:border-b [&>tr]:border-borda [&>tr:last-child]:border-b-0">{children}</tbody>
      </table>
    </div>
  )
}

export function Celula({ children, numero = false, detalhe }) {
  return (
    <td className={`px-3 py-2.5 align-top first:pl-0 last:pr-0 ${numero ? "text-right whitespace-nowrap" : ""}`}>
      {children}
      {detalhe && <span className="block text-xs text-texto-secundario">{detalhe}</span>}
    </td>
  )
}
