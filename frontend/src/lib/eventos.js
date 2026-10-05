/**
 * Avisos entre partes da tela que não se conhecem.
 *
 * O sino de notificações mora no Painel; quem lê uma mensagem mora na página.
 * Em vez de passar uma função por vários níveis só para o sino recarregar, a
 * página dispara um evento do navegador e o sino escuta.
 */
const EVENTO_NOTIFICACOES = "deltacare:notificacoes"

export function avisarNotificacoes() {
  window.dispatchEvent(new Event(EVENTO_NOTIFICACOES))
}

export function aoMudarNotificacoes(funcao) {
  window.addEventListener(EVENTO_NOTIFICACOES, funcao)
  return () => window.removeEventListener(EVENTO_NOTIFICACOES, funcao)
}
