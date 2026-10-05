import { useContext } from "react"

import { SessaoContext } from "../sessao/contexto"

/**
 * Hook próprio: quem está logado, e as ações de entrar e sair.
 *
 *     const { usuario, sair } = useSessao()
 *
 * Falha alto se usado fora do SessaoProvider: sem isso, o componente receberia
 * `null` e quebraria longe daqui, com um erro que não diz o motivo.
 */
export function useSessao() {
  const sessao = useContext(SessaoContext)
  if (!sessao) throw new Error("useSessao precisa estar dentro do SessaoProvider")
  return sessao
}
