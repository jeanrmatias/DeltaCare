import { useState } from "react"

import { Botao } from "../../componentes/Botao"
import { Carregando, EstadoVazio, Numero, Numeros } from "../../componentes/Cartao"
import { AreaDeTexto, MensagemDeFormulario } from "../../componentes/Campos"
import { AcoesDoModal, Modal } from "../../componentes/Modal"
import { Selo } from "../../componentes/Selo"
import { useApi } from "../../hooks/useApi"
import { useDialogo } from "../../hooks/useDialogo"
import { Cabecalho } from "../../layout/Painel"
import { api, ERRO_DE_CONEXAO } from "../../lib/api"
import { dataComAno } from "../../lib/formatos"
import { statusPrivacidade } from "../../lib/privacidade"

/**
 * Privacidade na visão da administração: os pedidos dos alunos sobre os
 * próprios dados. Só chega aqui o que precisa de decisão — correção e
 * exclusão; a cópia dos dados o aluno baixa sozinho.
 *
 * Pendentes primeiro, depois as contas desativadas (ainda reversíveis),
 * depois o histórico — a ordem vem do servidor.
 */
const FILTROS = [["", "Todos"], ["pendente", "Aguardando decisão"], ["agendada", "Contas desativadas"], ["concluida", "Concluídos"],
  ["recusada", "Recusados"], ["cancelada", "Cancelados"], ["revertida", "Exclusões revertidas"]]

export function PrivacidadeAdmin() {
  const [status, setStatus] = useState("")
  const { dados, carregando, erro, recarregar } = useApi(`/admin/privacidade/solicitacoes${status ? `?status=${status}` : ""}`)
  const [recusando, setRecusando] = useState(null)
  const { confirmar, avisar } = useDialogo()
  const contagem = dados?.contagem || {}
  const pedidos = dados?.solicitacoes || []

  async function decidir(pedido, aprovar, resposta = "") {
    try {
      const resultado = await (await api(`/admin/privacidade/solicitacoes/${pedido.id}`, { method: "PUT", body: JSON.stringify({ aprovar, resposta }) })).json()
      await avisar(resultado.mensagem, resultado.sucesso ? "Pronto" : "Algo deu errado")
      recarregar()
      return resultado.sucesso
    } catch (falha) {
      console.error("Erro ao decidir pedido:", falha)
      await avisar(ERRO_DE_CONEXAO, "Algo deu errado")
      return false
    }
  }

  async function aprovar(pedido) {
    const nome = pedido.aluno.nome || pedido.aluno.email
    const exclusao = pedido.tipo === "exclusao"
    const texto = exclusao
      ? `A conta de ${nome} será desativada agora, e os dados pessoais anonimizados ao fim do prazo. Até lá, dá para reverter.`
      : `Trocar ${pedido.campo_rotulo.toLowerCase()} de ${nome} para "${pedido.valor_novo}"?`
    if (await confirmar(texto, { titulo: pedido.tipo_rotulo, rotulo: "Aprovar", perigo: exclusao })) decidir(pedido, true)
  }

  async function reverter(pedido) {
    const nome = pedido.aluno.nome || pedido.aluno.email
    if (!(await confirmar(`A conta de ${nome} volta a entrar normalmente.`, { titulo: "Reverter exclusão", rotulo: "Reverter" }))) return
    try {
      const resultado = await (await api(`/admin/privacidade/solicitacoes/${pedido.id}/reverter`, { method: "POST" })).json()
      if (!resultado.sucesso) await avisar(resultado.mensagem, "Algo deu errado")
      recarregar()
    } catch (falha) {
      console.error("Erro ao reverter:", falha)
      await avisar(ERRO_DE_CONEXAO, "Algo deu errado")
    }
  }

  return (
    <>
      <Cabecalho titulo="Privacidade" descricao="Pedidos dos alunos sobre os próprios dados (LGPD).">
        <select aria-label="Status" value={status} onChange={(e) => setStatus(e.target.value)}
          className="rounded-campo border border-borda-campo bg-superficie px-3 py-2.5 text-sm outline-none focus:border-primaria">
          {FILTROS.map(([valor, rotulo]) => <option key={valor} value={valor}>{rotulo}</option>)}
        </select>
      </Cabecalho>

      {dados?.sucesso && (
        <>
          <Numeros>
            <Numero rotulo="Aguardando decisão" valor={contagem.pendente || 0} />
            <Numero rotulo="Contas desativadas" valor={contagem.agendada || 0} />
            <Numero rotulo="Concluídos" valor={contagem.concluida || 0} destaque />
          </Numeros>
          <p className="mb-5 max-w-3xl text-[14px] leading-relaxed text-texto-secundario">
            A cópia dos dados o aluno baixa sozinho, por isso não aparece aqui. Correção e exclusão esperam a sua decisão.
            Exclusão aprovada desativa a conta na hora; os dados pessoais são anonimizados {dados.prazo_anonimizacao_dias} dias
            depois, e até lá dá para reverter.
          </p>
        </>
      )}

      {carregando && <Carregando />}
      {erro && <EstadoVazio>{erro}</EstadoVazio>}
      {dados?.sucesso && !pedidos.length && <EstadoVazio>Nenhum pedido por aqui.</EstadoVazio>}

      <section className="flex flex-col gap-3">
        {pedidos.map((pedido) => {
          const situacao = statusPrivacidade(pedido.status)
          const aluno = pedido.aluno || {}
          return (
            <article key={pedido.id} className="flex flex-col gap-3 rounded-cartao bg-superficie p-5 shadow-cartao md:flex-row md:items-start md:justify-between">
              <div className="min-w-0">
                <div className="mb-1.5 flex flex-wrap items-center gap-2">
                  <span className="text-xs font-semibold text-texto-secundario">
                    {aluno.anonimizado ? (aluno.tipo === "professor" ? "Professor removido" : "Aluno removido") : `${aluno.nome || aluno.email} · ${aluno.email}`}
                    {aluno.tipo === "professor" && !aluno.anonimizado && " · professor"} · {dataComAno(pedido.criado_em)}
                  </span>
                  <Selo tom={situacao.tom}>{situacao.rotulo}</Selo>
                </div>
                <h2 className="text-[17px] font-semibold text-navy-900">{pedido.campo_rotulo ? `${pedido.tipo_rotulo}: ${pedido.campo_rotulo}` : pedido.tipo_rotulo}</h2>
                {/* O valor de hoje ao lado do pedido: aprovar sem ver o que vai ser trocado é aprovar no escuro. */}
                {pedido.tipo === "correcao" && pedido.valor_novo && (
                  <p className="mt-1 text-[14px] text-texto">Hoje: <strong>{pedido.valor_atual || "(vazio)"}</strong> → Pedido: <strong>{pedido.valor_novo}</strong></p>
                )}
                {pedido.origem === "administracao" && <p className="mt-1 text-[14px] text-texto-secundario">Excluída pela administração.</p>}
                {pedido.motivo && (
                  <p className="mt-1 text-[14px] text-texto-secundario">{pedido.origem === "administracao" ? "Motivo registrado" : "Motivo do aluno"}: {pedido.motivo}</p>
                )}
                {pedido.resposta && <p className="mt-1 text-[14px] text-texto-secundario">Resposta: {pedido.resposta}</p>}
                {pedido.status === "agendada" && pedido.anonimizar_em && (
                  <p className="mt-1 text-[14px] font-semibold text-perigo">Anonimização em {dataComAno(pedido.anonimizar_em)}.</p>
                )}
              </div>
              <div className="flex shrink-0 flex-wrap gap-2">
                {pedido.status === "pendente" && (
                  <>
                    <Botao pequeno onClick={() => aprovar(pedido)}>Aprovar</Botao>
                    <Botao variante="neutra" pequeno onClick={() => setRecusando(pedido)}>Recusar</Botao>
                  </>
                )}
                {pedido.status === "agendada" && <Botao variante="neutra" pequeno onClick={() => reverter(pedido)}>Reverter exclusão</Botao>}
              </div>
            </article>
          )
        })}
      </section>

      {recusando && (
        <ModalRecusa pedido={recusando} aoFechar={() => setRecusando(null)}
          aoRecusar={async (resposta) => { if (await decidir(recusando, false, resposta)) setRecusando(null) }} />
      )}
    </>
  )
}

function ModalRecusa({ pedido, aoFechar, aoRecusar }) {
  const [resposta, setResposta] = useState("")
  const [mensagem, setMensagem] = useState("")

  return (
    <Modal aberto aoFechar={aoFechar} titulo={`Recusar: ${pedido.tipo_rotulo}`}>
      <form onSubmit={(e) => {
        e.preventDefault()
        if (resposta.trim()) aoRecusar(resposta.trim())
        else setMensagem("Diga ao aluno por que o pedido foi recusado.")
      }}>
        <AreaDeTexto rotulo="Motivo da recusa (o aluno vai ler)" valor={resposta} aoMudar={setResposta} linhas={4} maximo={500} obrigatorio />
        <MensagemDeFormulario texto={mensagem} />
        <AcoesDoModal>
          <Botao variante="neutra" onClick={aoFechar}>Cancelar</Botao>
          <Botao tipo="submit">Recusar</Botao>
        </AcoesDoModal>
      </form>
    </Modal>
  )
}
