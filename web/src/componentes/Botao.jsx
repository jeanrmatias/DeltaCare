/**
 * Botão do sistema. `variante` muda a cor; o resto é igual em todo lugar.
 *
 * - primaria: a ação principal da tela (uma por tela, idealmente)
 * - neutra: ações secundárias
 * - perigo: o que apaga ou desativa algo
 *
 * `pequeno` é para botões dentro de listas, ao lado de cada item.
 */
const VARIANTES = {
  primaria: "bg-primaria text-white hover:bg-primaria-escura",
  neutra: "bg-superficie text-texto border border-borda hover:bg-fundo",
  perigo: "bg-perigo text-white hover:brightness-95",
}

export function Botao({ children, variante = "primaria", tipo = "button", largo = false, pequeno = false, desativado = false, onClick, className = "" }) {
  return (
    <button
      type={tipo}
      onClick={onClick}
      disabled={desativado}
      className={[
        "rounded-campo font-semibold transition active:scale-[0.98]",
        pequeno ? "px-3.5 py-2 text-[13px]" : "px-4 py-3 text-sm",
        "disabled:cursor-not-allowed disabled:bg-texto-secundario disabled:text-white disabled:active:scale-100",
        VARIANTES[variante],
        largo ? "w-full" : "",
        className,
      ].join(" ")}
    >
      {children}
    </button>
  )
}
