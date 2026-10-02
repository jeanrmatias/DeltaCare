/**
 * As peças de layout que toda tela usa: o cartão branco, o número em
 * destaque e o aviso de "não há nada aqui".
 */

export function Cartao({ titulo, children, className = "" }) {
  return (
    <section className={`rounded-cartao bg-superficie p-5 shadow-cartao ${className}`}>
      {titulo && <h2 className="mb-4 text-[15px] font-semibold text-navy-900">{titulo}</h2>}
      {children}
    </section>
  )
}

/** Um número com rótulo, nas fileiras do topo das telas. */
export function Numero({ rotulo, valor, destaque = false }) {
  return (
    <article className="flex flex-col gap-2.5 rounded-cartao bg-superficie px-5 py-[18px] shadow-cartao">
      <span className="text-[13px] font-medium text-texto-secundario">{rotulo}</span>
      <strong className={`text-[26px] font-bold ${destaque ? "text-sucesso" : "text-navy-900"}`}>{valor}</strong>
    </article>
  )
}

export function Numeros({ children }) {
  return <section className="mb-5 grid grid-cols-[repeat(auto-fit,minmax(170px,1fr))] gap-4">{children}</section>
}

/** O que a tela diz quando não há o que mostrar — ou quando não conseguiu buscar. */
export function EstadoVazio({ children }) {
  return (
    <p className="mt-6 rounded-cartao border border-dashed border-borda bg-superficie p-8 text-center text-sm text-texto-secundario">
      {children}
    </p>
  )
}

export function Carregando() {
  return <p className="py-6 text-center text-sm text-texto-secundario" role="status">Carregando...</p>
}
