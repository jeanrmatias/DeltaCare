/**
 * Selo pequeno de status. `tom` escolhe a cor, não o significado: quem usa
 * decide que "agendado" é alerta e "publicado" é sucesso.
 */
const TONS = {
  neutro: "bg-fundo text-texto-secundario",
  alerta: "bg-alerta-fundo text-[#92610A]",
  sucesso: "bg-sucesso-fundo text-[#157A3C]",
  perigo: "bg-perigo-fundo text-[#B42318]",
}

export function Selo({ tom = "neutro", children }) {
  return (
    <span className={`inline-block shrink-0 rounded-campo px-2 py-0.5 text-[11px] font-bold whitespace-nowrap ${TONS[tom]}`}>
      {children}
    </span>
  )
}

