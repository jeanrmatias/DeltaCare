import { useCallback, useRef, useState } from "react"

/**
 * Hook próprio: um envio de formulário por vez.
 *
 *     const [enviando, executar] = useEnvio()
 *     <form onSubmit={executar(criar)}> ... <Botao tipo="submit" desativado={enviando}>
 *
 * Sem isto, o duplo clique em "Criar disciplina" ou "Enviar aviso" mandava
 * duas requisições, e o servidor criava dois registros — dois avisos iguais
 * no mural dos alunos. A trava é uma ref, e não só o estado: dois cliques no
 * mesmo instante chegam antes de o estado novo renderizar, e os dois veriam
 * `enviando` ainda falso. O estado serve para o botão aparecer desativado.
 */
export function useEnvio() {
  const emAndamento = useRef(false)
  const [enviando, setEnviando] = useState(false)

  const executar = useCallback((acao) => async (evento) => {
    evento?.preventDefault?.()
    if (emAndamento.current) return
    emAndamento.current = true
    setEnviando(true)
    try {
      await acao(evento)
    } finally {
      emAndamento.current = false
      setEnviando(false)
    }
  }, [])

  return [enviando, executar]
}
