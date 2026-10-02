/** Recorte de tempo do desempenho, em dias (vazio: o semestre todo). */
export function SeletorPeriodo({ valor, aoMudar }) {
  return (
    <select aria-label="Período" value={valor} onChange={(evento) => aoMudar(evento.target.value)}
      className="rounded-campo border border-borda bg-superficie px-3 py-2.5 text-sm text-texto outline-none focus:border-primaria">
      <option value="">Todo o semestre</option>
      <option value="7">Últimos 7 dias</option>
      <option value="30">Últimos 30 dias</option>
      <option value="90">Últimos 90 dias</option>
    </select>
  )
}
