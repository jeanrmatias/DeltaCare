/**
 * O que as telas de privacidade do aluno e da administração dividem: o nome
 * de cada status e o nome do arquivo da cópia. As regras estão no servidor
 * (backend/regras/privacidade.py).
 */
export const STATUS_PRIVACIDADE = {
  pendente: { rotulo: "Aguardando a administração", tom: "alerta" },
  agendada: { rotulo: "Conta desativada", tom: "perigo" },
  concluida: { rotulo: "Concluído", tom: "sucesso" },
  recusada: { rotulo: "Recusado", tom: "neutro" },
  cancelada: { rotulo: "Cancelado", tom: "neutro" },
  revertida: { rotulo: "Exclusão revertida", tom: "neutro" },
}

export function statusPrivacidade(status) {
  return STATUS_PRIVACIDADE[status] || { rotulo: status, tom: "neutro" }
}

/** Com a data, para duas cópias não se sobrescreverem. */
export function nomeArquivoDaCopia(iso) {
  const dia = String(iso || "").slice(0, 10) || "copia"
  return `delta-care-meus-dados-${dia}.json`
}
