import { useState } from "react"

import { useDialogo } from "../hooks/useDialogo"
import { api, ERRO_DE_CONEXAO } from "../lib/api"

/**
 * A estrela de favorito. Só muda depois que o servidor confirma: pintar
 * antes e desfazer se der erro faria a estrela piscar sem o aluno entender.
 * `aoMudar(favorito)` avisa quem usa (a tela de Favoritos tira o item).
 */
export function BotaoFavorito({ material, aoMudar }) {
  const [favorito, setFavorito] = useState(Boolean(material.favorito))
  const [enviando, setEnviando] = useState(false)
  const { avisar } = useDialogo()

  async function alternar() {
    setEnviando(true)
    try {
      const resposta = await api(`/aluno/favoritos/${material.id}`, { method: favorito ? "DELETE" : "PUT" })
      const dados = await resposta.json()
      if (!dados.sucesso) {
        await avisar(dados.mensagem || "Não foi possível mudar o favorito.", "Algo deu errado")
        return
      }
      setFavorito(dados.favorito)
      aoMudar?.(dados.favorito)
    } catch (erro) {
      console.error("Erro no favorito:", erro)
      await avisar(ERRO_DE_CONEXAO, "Algo deu errado")
    } finally {
      setEnviando(false)
    }
  }

  const rotulo = favorito ? "Tirar dos favoritos" : "Guardar nos favoritos"

  return (
    <button
      type="button"
      onClick={alternar}
      disabled={enviando}
      aria-pressed={favorito}
      aria-label={rotulo}
      title={rotulo}
      className={`text-xl leading-none transition hover:scale-110 disabled:opacity-50 ${favorito ? "text-alerta-forte" : "text-texto-secundario"}`}
    >
      {favorito ? "★" : "☆"}
    </button>
  )
}
