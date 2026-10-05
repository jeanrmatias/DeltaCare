/**
 * Datas digitadas pelo professor (agendamento de material, prazo de
 * atividade). O campo aceita `dd/mm/aaaa hh:mm` e também o que as pessoas
 * escrevem de verdade: `5/3`, `05/03/26`, `5 3 2026 14:00`.
 */

export const MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
export const DIAS_CURTOS = ["dom", "seg", "ter", "qua", "qui", "sex", "sáb"]

/** O que foi digitado → Date, ou null se não der para entender. */
export function interpretarDataDigitada(texto, agora = new Date()) {
  const limpo = String(texto || "").trim()
  if (!limpo) return null

  // A hora sai antes de quebrar em partes: senão "14:00" virava dia e mês.
  const horaCrua = limpo.match(/(\d{1,2}):(\d{2})/)
  const semHora = horaCrua ? limpo.replace(horaCrua[0], " ") : limpo
  const partes = semHora.split(/[\s/.-]+/).filter(Boolean)
  if (partes.length < 2) return null

  const dia = Number(partes[0])
  const mes = Number(partes[1])
  if (!Number.isInteger(dia) || !Number.isInteger(mes) || dia < 1 || dia > 31 || mes < 1 || mes > 12) return null

  let ano = agora.getFullYear()
  if (partes.length >= 3 && /^\d+$/.test(partes[2])) {
    ano = Number(partes[2])
    if (ano < 100) ano += 2000
  }

  let hora = 0
  let minuto = 0
  if (horaCrua) {
    hora = Number(horaCrua[1])
    minuto = Number(horaCrua[2])
    if (hora > 23 || minuto > 59) return null
  }

  const data = new Date(ano, mes - 1, dia, hora, minuto, 0, 0)
  // 31/02 vira 03/03 no Date: aqui é recusado, e não corrigido em silêncio.
  if (data.getDate() !== dia || data.getMonth() !== mes - 1) return null
  return data
}

const dois = (n) => String(n).padStart(2, "0")

/**
 * O dia escolhido no calendário ("2026-10-20", vindo da URL) numa hora
 * daquele dia, em ISO — para abrir o formulário já com a data. Qualquer outra
 * coisa na URL vira null: o formulário não abre com data inventada.
 */
export function dataDoCalendario(dia, hora) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(dia || "")) return null
  const data = new Date(`${dia}T${hora}:00`)
  return Number.isNaN(data.getTime()) ? null : data.toISOString()
}

export function formatarParaCampo(data) {
  if (!data) return ""
  return `${dois(data.getDate())}/${dois(data.getMonth() + 1)}/${data.getFullYear()} ${dois(data.getHours())}:${dois(data.getMinutes())}`
}

export function mesmoDia(a, b) {
  return Boolean(a && b) && a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate()
}

/** ISO do banco → Date, ou null. */
export function lerIso(iso) {
  if (!iso) return null
  const data = new Date(iso)
  return Number.isNaN(data.getTime()) ? null : data
}
