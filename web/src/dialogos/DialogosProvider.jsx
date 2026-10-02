import { useCallback, useMemo, useState } from "react"

import { Botao } from "../componentes/Botao"
import { AcoesDoModal, Modal } from "../componentes/Modal"
import { DialogosContext } from "./contexto"

/**
 * Confirmar e avisar, como funções que devolvem uma Promise:
 *
 *     const { confirmar, avisar } = useDialogo()
 *     if (await confirmar("Apagar esta anotação?", { perigo: true })) ...
 *
 * É o mesmo jeito de usar do dialogo.js antigo. Por baixo, um único modal
 * mora aqui, e cada chamada guarda o "resolver" da Promise para quando a
 * pessoa clicar.
 */
export function DialogosProvider({ children }) {
  const [atual, setAtual] = useState(null)

  const abrir = useCallback(
    (opcoes) => new Promise((resolver) => setAtual({ ...opcoes, resolver })),
    [],
  )

  const confirmar = useCallback(
    (mensagem, { titulo = "Confirmar", rotulo = "Confirmar", perigo = false } = {}) =>
      abrir({ tipo: "confirmar", mensagem, titulo, rotulo, perigo }),
    [abrir],
  )

  const avisar = useCallback(
    (mensagem, titulo = "Aviso") => abrir({ tipo: "avisar", mensagem, titulo, rotulo: "Entendi" }),
    [abrir],
  )

  function responder(valor) {
    atual?.resolver(valor)
    setAtual(null)
  }

  const valor = useMemo(() => ({ confirmar, avisar }), [confirmar, avisar])

  return (
    <DialogosContext.Provider value={valor}>
      {children}
      <Modal aberto={Boolean(atual)} aoFechar={() => responder(false)} titulo={atual?.titulo}>
        <p className="text-sm leading-relaxed whitespace-pre-wrap text-texto">{atual?.mensagem}</p>
        <AcoesDoModal>
          {atual?.tipo === "confirmar" && <Botao variante="neutra" onClick={() => responder(false)}>Cancelar</Botao>}
          <Botao variante={atual?.perigo ? "perigo" : "primaria"} onClick={() => responder(true)}>
            {atual?.rotulo}
          </Botao>
        </AcoesDoModal>
      </Modal>
    </DialogosContext.Provider>
  )
}
