import { useContext } from "react"

import { DialogosContext } from "../dialogos/contexto"

/**
 * Hook próprio: `confirmar` e `avisar` em qualquer tela.
 *
 *     const { confirmar, avisar } = useDialogo()
 */
export function useDialogo() {
  const dialogos = useContext(DialogosContext)
  if (!dialogos) throw new Error("useDialogo precisa estar dentro do DialogosProvider")
  return dialogos
}
