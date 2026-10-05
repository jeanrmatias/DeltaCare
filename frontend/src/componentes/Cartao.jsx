/**
 * As peças de layout que toda tela usa: o cartão branco, o número em
 * destaque e o aviso de "não há nada aqui".
 */

export function Cartao({ titulo, children, className = "" }) {
  return (
    <section className={`rounded-cartao bg-superficie p-5 shadow-cartao ${className}`}>
      {titulo && <h2 className="mb-4 text-[18px] font-semibold text-navy-900">{titulo}</h2>}
      {children}
    </section>
  )
}

/** Um número com rótulo, numa faixa (Numeros): o número na serifada, grande; o rótulo embaixo. */
export function Numero({ rotulo, valor, destaque = false }) {
  return (
    <article className="flex flex-1 flex-col gap-1.5 bg-superficie px-5 py-4 last:odd:col-span-2">
      <strong className={`font-numero text-[28px] leading-none font-semibold sm:text-[32px] ${destaque ? "text-sucesso" : "text-navy-900"}`}>{valor}</strong>
      <span className="text-[14px] text-texto-secundario">{rotulo}</span>
    </article>
  )
}

/**
 * Os números do topo das telas, numa faixa só, separados por filetes — e não
 * uma caixa com sombra para cada um, que era o traço mais reconhecível de
 * painel genérico. O filete é o fundo aparecendo pelo vão de 1px (gap-px).
 * No celular, dois por linha; o último, se sobrar sozinho, ocupa a linha.
 */
export function Numeros({ children }) {
  return (
    <section className="mb-5 grid grid-cols-2 gap-px overflow-hidden rounded-cartao bg-borda shadow-cartao sm:flex">
      {children}
    </section>
  )
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
