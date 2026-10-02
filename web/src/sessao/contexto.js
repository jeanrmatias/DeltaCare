import { createContext } from "react"

/**
 * Onde a sessão fica disponível para a árvore inteira de componentes.
 *
 * Sem um Context, o usuário logado teria que descer de componente em
 * componente por props, até a sidebar e o rodapé. Quem preenche é o
 * SessaoProvider; quem lê é o hook useSessao.
 */
export const SessaoContext = createContext(null)
