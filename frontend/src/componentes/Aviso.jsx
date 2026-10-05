/**
 * Um aviso: selo de urgente, título, texto e a linha de rodapé. Usado no
 * mural das telas iniciais e na tela de Avisos. Urgente recente ganha fundo
 * de destaque (`em_destaque` vem do servidor: urgente dos últimos 7 dias).
 */
export function Aviso({ aviso, rodape, children }) {
  return (
    <article className={`rounded-campo px-3.5 py-3 ${aviso.em_destaque ? "bg-alerta-fundo shadow-[inset_3px_0_0_var(--color-alerta)]" : "bg-fundo"}`}>
      <div className="flex flex-wrap items-center gap-2">
        {aviso.urgente && <span className="rounded-full bg-alerta px-2 py-0.5 text-[12px] font-bold tracking-wider text-white uppercase">Urgente</span>}
        <h3 className="text-[16px] font-semibold text-texto">{aviso.titulo}</h3>
      </div>
      <p className="mt-1.5 text-sm leading-normal [overflow-wrap:anywhere] whitespace-pre-wrap text-texto">{aviso.conteudo}</p>
      <p className="mt-2 text-xs text-texto-secundario">{rodape}</p>
      {children}
    </article>
  )
}
