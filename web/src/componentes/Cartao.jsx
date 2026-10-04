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
    <article className="flex flex-col gap-2 rounded-cartao bg-superficie px-4 py-3.5 shadow-cartao sm:gap-2.5 sm:px-5 sm:py-[18px]">
      <span className="text-[13px] font-medium text-texto-secundario">{rotulo}</span>
      <strong className={`text-[22px] font-bold sm:text-[26px] ${destaque ? "text-sucesso" : "text-navy-900"}`}>{valor}</strong>
    </article>
  )
}

export function Numeros({ children }) {
  // Dois por linha no celular: um embaixo do outro, três números ocupavam a tela inteira.
  return <section className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-[repeat(auto-fit,minmax(170px,1fr))] sm:gap-4">{children}</section>
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
