import { useCallback, useEffect, useMemo, useState } from "react"

import { api, lerSessao, limparSessao, quandoSessaoExpirar, salvarSessao } from "../lib/api"
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

  useEffect(() => {
    quandoSessaoExpirar(() => setUsuario(null))
    return () => quandoSessaoExpirar(() => {})
  }, [])

  const entrar = useCallback((respostaDoLogin) => {
    const { email, tipo, nome, token } = respostaDoLogin
    const dados = { email, tipo, nome: nome || "" }
    salvarSessao(dados, token)
    setUsuario(dados)
  }, [])

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

  const valor = useMemo(() => ({ usuario, entrar, sair }), [usuario, entrar, sair])

  return <SessaoContext.Provider value={valor}>{children}</SessaoContext.Provider>
}
