/**
 * Conversa com o backend. É o mesmo contrato do auth.js do front antigo, num
 * módulo só: o endereço da API, o token no header e o que fazer quando a
 * sessão expira.
 *
 * O token é o que prova a identidade: o backend nunca confia no e-mail ou no
 * perfil que vêm do navegador. O que fica guardado aqui (nome, tipo) serve só
 * para a tela decidir o que desenhar — adulterar isso não dá acesso a nada.
 *
 * **Não há modo de contingência.** Se o backend não responder, a chamada
 * falha e a tela diz isso. Mostrar dado fictício quando o servidor cai seria
 * pior do que não mostrar nada.
 */

/**
 * Onde está a API, deduzido do endereço da página.
 *
 * Em desenvolvimento as telas ficam no Vite (5173) ou no servidor antigo
 * (5500), e a API na 8000 do mesmo computador. Em produção a própria API
 * entrega as telas: mesma origem. `window.DELTACARE_API_URL` vence tudo,
 * para o caso de API num domínio separado.
 */
export function enderecoDaApi(local, sobrescrito) {
  if (sobrescrito) return sobrescrito.replace(/\/+$/, "")
  if (local.port === "5173" || local.port === "5500") {
    return `${local.protocol}//${local.hostname}:8000`
  }
  return local.origin
}

export const API_URL =
  typeof window === "undefined" ? "" : enderecoDaApi(window.location, window.DELTACARE_API_URL)

// As mesmas chaves do front antigo: quem já tinha sessão aberta nele continuou logado.
const CHAVE_USUARIO = "deltacare_usuario"
const CHAVE_TOKEN = "deltacare_token"

/**
 * sessionStorage, e não localStorage, de propósito: o token some ao fechar a
 * aba. Num computador compartilhado de laboratório, a próxima pessoa não
 * herda a conta de quem esqueceu de sair.
 */
export function lerSessao(armazenamento = globalThis.sessionStorage) {
  try {
    const usuario = JSON.parse(armazenamento.getItem(CHAVE_USUARIO) || "null")
    const token = armazenamento.getItem(CHAVE_TOKEN) || ""
    return usuario && token ? { usuario, token } : null
  } catch {
    return null
  }
}

export function salvarSessao(usuario, token, armazenamento = globalThis.sessionStorage) {
  try {
    armazenamento.setItem(CHAVE_USUARIO, JSON.stringify(usuario))
    armazenamento.setItem(CHAVE_TOKEN, token)
  } catch (erro) {
    console.error("Não foi possível salvar a sessão:", erro)
  }
}

export function limparSessao(armazenamento = globalThis.sessionStorage) {
  try {
    armazenamento.removeItem(CHAVE_USUARIO)
    armazenamento.removeItem(CHAVE_TOKEN)
  } catch {
    /* armazenamento indisponível: nada a limpar */
  }
}

/** Lançado quando o backend responde 401: o token venceu ou foi encerrado. */
export class SessaoExpirada extends Error {
  constructor() {
    super("Sessão expirada")
    this.name = "SessaoExpirada"
  }
}

// Quem avisa a interface que a sessão acabou. O SessaoProvider registra a
// função dele aqui; o módulo não conhece React, só chama o aviso.
let aoExpirar = () => {}

export function quandoSessaoExpirar(funcao) {
  aoExpirar = funcao
}

// Quem avisa que o servidor está exigindo a troca da senha provisória.
let aoExigirTrocaDeSenha = () => {}

export function quandoExigirTrocaDeSenha(funcao) {
  aoExigirTrocaDeSenha = funcao
}

/** Lançado quando o servidor recusa porque a senha ainda é a provisória. */
export class SenhaProvisoria extends Error {
  constructor() {
    super("Troque a senha provisória antes de continuar.")
    this.name = "SenhaProvisoria"
  }
}

/** Chama a API com o token da sessão. */
export async function api(caminho, opcoes = {}) {
  const cabecalhos = { ...(opcoes.headers || {}) }
  const sessao = lerSessao()

  if (sessao) cabecalhos.Authorization = `Bearer ${sessao.token}`
  if (opcoes.body && !cabecalhos["Content-Type"]) cabecalhos["Content-Type"] = "application/json"

  const resposta = await fetch(`${API_URL}${caminho}`, { ...opcoes, headers: cabecalhos })

  if (resposta.status === 401) {
    limparSessao()
    aoExpirar()
    throw new SessaoExpirada()
  }
  if (resposta.status === 403) {
    // A senha provisória é exigida pelo servidor em toda rota. Se ele recusar
    // por isso (sessão de antes, outra aba), a tela leva à troca.
    const corpo = await resposta.clone().json().catch(() => null)
    if (corpo?.detail?.codigo === "trocar_senha") {
      aoExigirTrocaDeSenha()
      throw new SenhaProvisoria()
    }
  }
  return resposta
}

/** Chama uma rota pública (login, recuperação de senha) com corpo JSON. */
export async function apiPublica(caminho, corpo) {
  return fetch(`${API_URL}${caminho}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(corpo),
  })
}

export const ERRO_DE_CONEXAO = "Não foi possível conectar ao servidor. Tente novamente."
