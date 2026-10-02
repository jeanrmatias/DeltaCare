import { useEffect, useRef } from "react"

/**
 * Janela sobreposta, com o <dialog> nativo do navegador: ele já prende o
 * foco dentro da janela, fecha com Esc e avisa leitores de tela que é um
 * modal — coisas que um <div> por cima da página não faz.
 *
 * Quem usa decide se está aberta: `<Modal aberto={x} aoFechar={...}>`.
 * `largura` é a classe de largura máxima (o visualizador é mais largo).
 */
export function Modal({ aberto, aoFechar, titulo, children, largura = "max-w-[480px]" }) {
  const dialogo = useRef(null)

  // O React não abre <dialog> sozinho: showModal() é uma chamada ao
  // navegador, por isso fica num efeito, sincronizando com `aberto`.
  useEffect(() => {
    const elemento = dialogo.current
    if (!elemento) return
    if (aberto && !elemento.open) elemento.showModal()
    if (!aberto && elemento.open) elemento.close()
  }, [aberto])

  return (
    <dialog
      ref={dialogo}
      onCancel={(evento) => {
        // Esc: quem fecha é o estado de quem usa, não o navegador sozinho.
        evento.preventDefault()
        aoFechar()
      }}
      onClick={(evento) => evento.target === dialogo.current && aoFechar()}
      className={`m-auto w-[calc(100%-2rem)] ${largura} rounded-cartao bg-superficie p-0 text-texto shadow-xl backdrop:bg-navy-900/45`}
    >
      {aberto && (
        <div className="p-6">
          {titulo && <h2 className="mb-3 text-lg font-bold text-navy-900">{titulo}</h2>}
          {children}
        </div>
      )}
    </dialog>
  )
}

/** A fileira de botões no pé de um modal. */
export function AcoesDoModal({ children }) {
  return <div className="mt-5 flex flex-col-reverse gap-2.5 sm:flex-row sm:justify-end">{children}</div>
}
