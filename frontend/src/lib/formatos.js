/**
 * Formatos de exibição usados em várias telas.
 */

/** "02 de out." — data curta, para listas. Vazio se a data não for válida. */
export function dataCurta(iso) {
  if (!iso) return ""
  const data = new Date(iso)
  if (Number.isNaN(data.getTime())) return ""
  return data.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" })
}

export const ROTULOS_TIPO_MATERIAL = {
  pdf: "PDF",
  documento: "Documento",
  video: "Vídeo",
  link: "Link",
}

/** "1 material liberado" / "3 materiais liberados" / "Nenhum material liberado ainda". */
export function contagemDeMateriais(total) {
  if (!total) return "Nenhum material liberado ainda"
  return total === 1 ? "1 material liberado" : `${total} materiais liberados`
}

/** Status de material, como o professor vê; `tom` é a cor do Selo. */
export const STATUS_DO_MATERIAL = {
  publicado: { rotulo: "Publicado", tom: "sucesso" },
  rascunho: { rotulo: "Rascunho", tom: "neutro" },
  agendado: { rotulo: "Agendado", tom: "alerta" },
}

/** "02 de out. de 2026" — com o ano, para o que pode ser de outro semestre. */
export function dataComAno(iso) {
  const data = new Date(iso)
  return Number.isNaN(data.getTime()) ? "" : data.toLocaleDateString("pt-BR", { day: "2-digit", month: "short", year: "numeric" })
}

/** "02 de out." aceitando data pura ("2026-10-02") sem o fuso puxar para o dia anterior. */
export function diaCurto(iso) {
  if (!iso) return "—"
  const data = /^\d{4}-\d{2}-\d{2}$/.test(iso)
    ? new Date(Number(iso.slice(0, 4)), Number(iso.slice(5, 7)) - 1, Number(iso.slice(8, 10)))
    : new Date(iso)
  return Number.isNaN(data.getTime()) ? "—" : data.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" })
}

/** "02 de out., 23:59" — para prazos e entregas. */
export function dataEHora(iso) {
  const data = new Date(iso)
  return !iso || Number.isNaN(data.getTime()) ? "" : data.toLocaleString("pt-BR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })
}
