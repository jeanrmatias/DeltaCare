import { api, ERRO_DE_CONEXAO } from "../lib/api"
import { useDialogo } from "./useDialogo"

/** Confirma e apaga. Resolve `true` se apagou. Usado pelo painel e pela tela de Anotações. */
export function useApagarAnotacao() {
  const { confirmar, avisar } = useDialogo()

  return async function apagar(anotacao) {
    const sim = await confirmar("Apagar esta anotação? Não dá para desfazer.", { titulo: "Apagar anotação", rotulo: "Apagar", perigo: true })
    if (!sim) return false
    try {
      const dados = await (await api(`/aluno/anotacoes/${anotacao.id}`, { method: "DELETE" })).json()
      if (!dados.sucesso) {
        await avisar(dados.mensagem || "Não foi possível apagar.", "Algo deu errado")
        return false
      }
      return true
    } catch (erro) {
      console.error("Erro ao apagar anotação:", erro)
      await avisar(ERRO_DE_CONEXAO, "Algo deu errado")
      return false
    }
  }
}
