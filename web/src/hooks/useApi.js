import { useCallback, useEffect, useState } from "react"

import { api, ERRO_DE_CONEXAO, SenhaProvisoria, SessaoExpirada } from "../lib/api"

/**
 * Hook próprio: busca um dado da API quando a tela abre.
 *
 *     const { dados, carregando, erro, recarregar } = useApi("/aluno/favoritos")
 *
 * No front antigo cada tela repetia o mesmo bloco: chamar, converter o JSON,
 * mostrar "carregando", tratar "sem conexão". Aqui é uma linha.
 *
 * - `caminho` nulo não busca nada (útil quando depende de uma escolha).
 * - Resposta com `sucesso: false` vira `erro`, com a mensagem do servidor.
 * - Se o caminho mudar antes da resposta chegar, a resposta velha é
 *   descartada — senão a tela mostraria o dado da escolha anterior.
 * - Sessão expirada não vira mensagem: a RotaPrivada já está levando ao login.
 *
 * `carregando` não é um estado guardado: é calculado — "a última resposta
 * que chegou é de outro pedido". Guardar em estado obrigaria a ligá-lo dentro
 * do efeito, e isso custa uma renderização a mais a cada busca.
 */
export function useApi(caminho) {
  const [versao, setVersao] = useState(0)
  const [resposta, setResposta] = useState({ pedido: null, dados: null, erro: "" })

  // Identifica o pedido: o mesmo caminho pedido de novo (recarregar) é outro pedido.
  const pedido = caminho ? `${caminho}#${versao}` : null

  useEffect(() => {
    if (!pedido) return undefined
    let vigente = true

    api(caminho)
      .then((retorno) => retorno.json())
      .then((dados) => {
        if (!vigente) return
        const erro = dados && dados.sucesso === false ? dados.mensagem || ERRO_DE_CONEXAO : ""
        setResposta({ pedido, dados, erro })
      })
      .catch((erro) => {
        if (!vigente || erro instanceof SessaoExpirada || erro instanceof SenhaProvisoria) return
        console.error(`Erro ao buscar ${caminho}:`, erro)
        setResposta({ pedido, dados: null, erro: ERRO_DE_CONEXAO })
      })

    return () => {
      vigente = false
    }
  }, [pedido, caminho])

  const recarregar = useCallback(() => setVersao((v) => v + 1), [])
  const carregando = Boolean(pedido) && resposta.pedido !== pedido

  // Enquanto recarrega, o dado anterior continua na tela: piscar a lista
  // inteira a cada atualização seria pior do que mostrá-la por um instante.
  return { dados: resposta.dados, erro: carregando ? "" : resposta.erro, carregando, recarregar }
}
