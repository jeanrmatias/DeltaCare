import { useState } from "react"

import { useApi } from "../hooks/useApi"
import { useDialogo } from "../hooks/useDialogo"
import { api, ERRO_DE_CONEXAO } from "../lib/api"
import { Botao } from "./Botao"
import { Escolha, MensagemDeFormulario, Texto } from "./Campos"
import { AcoesDoModal, Modal } from "./Modal"

/**
 * Reportar um material de onde ele aparece. A tela de Denúncias serve para
 * acompanhar; reportar acontece no item, que é onde a pessoa está quando
 * percebe o problema.
 *
 * Os motivos vêm do servidor (`GET /denuncias`), e não de uma cópia aqui:
 * duas listas iguais em lugares diferentes viram duas listas diferentes no
 * dia em que alguém acrescenta um motivo.
 */
export function ModalReportar({ material, aoFechar }) {
  const { dados, erro } = useApi("/denuncias")
  const motivos = dados?.motivos || []
  const [motivo, setMotivo] = useState("")
  const [descricao, setDescricao] = useState("")
  const [mensagem, setMensagem] = useState("")
  const [enviando, setEnviando] = useState(false)
  const { avisar } = useDialogo()

  async function enviar(evento) {
    evento.preventDefault()
    setEnviando(true)
    try {
      const resposta = await api("/denuncias", {
        method: "POST",
        body: JSON.stringify({ material_id: material.id, motivo: motivo || motivos[0]?.valor, descricao: descricao.trim() }),
      })
      const resultado = await resposta.json()
      if (!resultado.sucesso) return setMensagem(resultado.mensagem || "Não foi possível registrar a denúncia.")
      aoFechar()
      await avisar(resultado.mensagem, "Denúncia registrada")
    } catch (falha) {
      console.error("Erro ao reportar material:", falha)
      setMensagem(ERRO_DE_CONEXAO)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <Modal aberto aoFechar={aoFechar} titulo="Reportar conteúdo">
      <p className="mb-4 text-sm text-texto-secundario">"{material.titulo}" será enviado para a administração analisar.</p>
      {erro && <p className="text-sm text-perigo">{erro}</p>}
      {motivos.length > 0 && (
        <form onSubmit={enviar} className="flex flex-col gap-4">
          <Escolha rotulo="Motivo" valor={motivo || motivos[0].valor} aoMudar={setMotivo} opcoes={motivos} />
          <Texto rotulo="O que está errado" valor={descricao} aoMudar={setDescricao} maximo={1000}
            placeholder="Quanto mais específico, mais rápido resolve" />
          <MensagemDeFormulario texto={mensagem} />
          <AcoesDoModal>
            <Botao variante="neutra" onClick={aoFechar}>Cancelar</Botao>
            <Botao tipo="submit" desativado={enviando}>{enviando ? "Enviando..." : "Enviar denúncia"}</Botao>
          </AcoesDoModal>
        </form>
      )}
    </Modal>
  )
}
