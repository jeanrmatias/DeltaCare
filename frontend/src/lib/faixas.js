/**
 * As cores de cada faixa: clara no anel e no escudo; escura no texto (o nome
 * sobre fundo claro, o selo com letra branca), que precisa de 4,5:1. Um lugar só — o cartão de progresso e o ranking usam as mesmas.
 */
export const CORES_DA_FAIXA = {
  bronze: { clara: "#C87C3C", escura: "#7A4420" },
  prata: { clara: "#9FAEBC", escura: "#5A6672" },
  ouro: { clara: "#E0A62A", escura: "#8A6410" },
  platina: { clara: "#6FD3D8", escura: "#2E5F63" },
}

export function coresDaFaixa(chave) {
  return CORES_DA_FAIXA[chave] || { clara: "var(--color-primaria)", escura: "var(--color-navy-900)" }
}
