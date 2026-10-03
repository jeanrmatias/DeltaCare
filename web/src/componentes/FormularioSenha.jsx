import { useState } from "react"

import { api, ERRO_DE_CONEXAO } from "../lib/api"
import { Botao } from "./Botao"
import { MensagemDeFormulario, Texto } from "./Campos"

/**
 * Trocar a própria senha: a atual, a nova e a confirmação. Usado na troca
 * obrigatória do primeiro acesso e no "Alterar senha" do perfil.
 *
 * A senha atual é pedida mesmo logado: com a sessão aberta num computador do
 * laboratório, outra pessoa trocaria a senha e tomaria a conta.
 */
export function FormularioSenha({ rotuloAtual = "Senha atual", aoTrocar, acoesExtras }) {
  const [atual, setAtual] = useState("")
  const [nova, setNova] = useState("")
  const [confirmacao, setConfirmacao] = useState("")
  const [mensagem, setMensagem] = useState("")
  const [enviando, setEnviando] = useState(false)

  async function enviar(evento) {
    evento.preventDefault()
    // Conferido aqui porque é erro de digitação, não regra: o servidor nem
    // precisa ver as duas.
    if (nova !== confirmacao) return setMensagem("A confirmação não é igual à nova senha.")
    setEnviando(true)
    try {
      const resultado = await (await api("/eu/senha", { method: "PUT", body: JSON.stringify({ senha_atual: atual, nova_senha: nova }) })).json()
      if (!resultado.sucesso) return setMensagem(resultado.mensagem)
      aoTrocar(resultado.mensagem)
    } catch (erro) {
      console.error("Erro ao trocar a senha:", erro)
      setMensagem(ERRO_DE_CONEXAO)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <form onSubmit={enviar} className="flex flex-col gap-4">
      <Texto rotulo={rotuloAtual} tipo="password" valor={atual} aoMudar={setAtual} obrigatorio />
      <Texto rotulo="Nova senha" tipo="password" valor={nova} aoMudar={setNova} placeholder="mínimo 8 caracteres" obrigatorio />
      <Texto rotulo="Repita a nova senha" tipo="password" valor={confirmacao} aoMudar={setConfirmacao} obrigatorio />
      <MensagemDeFormulario texto={mensagem} />
      <div className="flex flex-wrap justify-end gap-2.5">
        {acoesExtras}
        <Botao tipo="submit" desativado={enviando}>{enviando ? "Salvando..." : "Salvar nova senha"}</Botao>
      </div>
    </form>
  )
}
