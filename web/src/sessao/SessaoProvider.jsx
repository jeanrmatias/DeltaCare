import { useCallback, useEffect, useMemo, useState } from "react"

import { api, lerSessao, limparSessao, quandoExigirTrocaDeSenha, quandoSessaoExpirar, salvarSessao } from "../lib/api"
import { SessaoContext } from "./contexto"

/**
 * Guarda quem está logado e oferece entrar e sair.
 *
 * O estado começa do que estiver no sessionStorage, então recarregar a página
 * (F5) não desloga. Quando a API responde 401, o aviso de `quandoSessaoExpirar`
 * zera o estado — e a RotaPrivada, que lê este estado, manda para o login.
 */
export function SessaoProvider({ children }) {
  const [usuario, setUsuario] = useState(() => lerSessao()?.usuario ?? null)

  // Marca (ou desmarca) que a senha ainda é a provisória — na memória e no
  // sessionStorage, para o F5 não esquecer.
  const marcarTrocaDeSenha = useCallback((exigida) => {
    const sessao = lerSessao()
    if (!sessao) return
    const dados = { ...sessao.usuario, trocar_senha: exigida }
    salvarSessao(dados, sessao.token)
    setUsuario(dados)
  }, [])

  useEffect(() => {
    quandoSessaoExpirar(() => setUsuario(null))
    quandoExigirTrocaDeSenha(() => marcarTrocaDeSenha(true))
    return () => {
      quandoSessaoExpirar(() => {})
      quandoExigirTrocaDeSenha(() => {})
    }
  }, [marcarTrocaDeSenha])

  const entrar = useCallback((respostaDoLogin) => {
    const { email, tipo, nome, token, trocar_senha } = respostaDoLogin
    const dados = { email, tipo, nome: nome || "", trocar_senha: Boolean(trocar_senha) }
    salvarSessao(dados, token)
    setUsuario(dados)
  }, [])

  const senhaTrocada = useCallback(() => marcarTrocaDeSenha(false), [marcarTrocaDeSenha])

  const sair = useCallback(async () => {
    // Avisa o backend para invalidar o token; se a chamada falhar, a sessão
    // local é limpa do mesmo jeito — ninguém pode ficar preso na conta.
    try {
      await api("/logout", { method: "POST" })
    } catch {
      /* segue para a limpeza local */
    }
    limparSessao()
    setUsuario(null)
  }, [])

  const valor = useMemo(() => ({ usuario, entrar, sair, senhaTrocada }), [usuario, entrar, sair, senhaTrocada])

  return <SessaoContext.Provider value={valor}>{children}</SessaoContext.Provider>
}
