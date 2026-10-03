import { useState } from "react"

import { Botao } from "../../componentes/Botao"
import { Carregando, EstadoVazio, Numero, Numeros } from "../../componentes/Cartao"
import { AreaDeTexto, MensagemDeFormulario } from "../../componentes/Campos"
import { AcoesDoModal, Modal } from "../../componentes/Modal"
import { Selo } from "../../componentes/Selo"
import { useApi } from "../../hooks/useApi"
import { Cabecalho } from "../../layout/Painel"
import { api, ERRO_DE_CONEXAO } from "../../lib/api"
import { dataComAno } from "../../lib/formatos"

/**
 * Denúncias na visão de quem trata: a fila da administração. Abertas
 * primeiro — quem abre esta tela vem trabalhar, não ler histórico.
 */
const PROXIMOS_PASSOS = {
  aberta: [["em_analise", "Pôr em análise"], ["concluida", "Concluir"], ["arquivada", "Arquivar"]],
  em_analise: [["concluida", "Concluir"], ["arquivada", "Arquivar"]],
  concluida: [["em_analise", "Reabrir"]],
  arquivada: [["em_analise", "Reabrir"]],
  // Quem reportou voltou atrás. O problema pode ser real mesmo assim.
  retirada: [["arquivada", "Arquivar"], ["em_analise", "Apurar mesmo assim"]],
}
const TOM = { aberta: "neutro", em_analise: "alerta", concluida: "sucesso", arquivada: "neutro", retirada: "neutro" }
const FILTROS = [["", "Todas"], ["aberta", "Abertas"], ["em_analise", "Em análise"], ["concluida", "Concluídas"], ["arquivada", "Arquivadas"], ["retirada", "Retiradas"]]

export function DenunciasAdmin() {
  const [status, setStatus] = useState("")
  const { dados, carregando, erro, recarregar } = useApi(`/admin/denuncias${status ? `?status=${status}` : ""}`)
  const [tratando, setTratando] = useState(null)
  const denuncias = dados?.denuncias || []

  return (
    <>
      <Cabecalho titulo="Denúncias" descricao="Conteúdo reportado por alunos e professores.">
        <select aria-label="Status" value={status} onChange={(e) => setStatus(e.target.value)}
          className="rounded-campo border border-borda-campo bg-superficie px-3 py-2.5 text-sm outline-none focus:border-primaria">
          {FILTROS.map(([valor, rotulo]) => <option key={valor} value={valor}>{rotulo}</option>)}
        </select>
      </Cabecalho>

      {dados?.resumo && (
        <Numeros>
          <Numero rotulo="Abertas" valor={dados.resumo.abertas} />
          <Numero rotulo="Em análise" valor={dados.resumo.em_analise} />
          <Numero rotulo="Concluídas" valor={dados.resumo.concluidas} destaque />
          <Numero rotulo="Arquivadas" valor={dados.resumo.arquivadas} />
          <Numero rotulo="Retiradas" valor={dados.resumo.retiradas} />
        </Numeros>
      )}

      {carregando && <Carregando />}
      {erro && <EstadoVazio>{erro}</EstadoVazio>}
      {dados?.sucesso && !denuncias.length && (
        <EstadoVazio>{status ? "Nenhuma denúncia com esse status." : "Nenhuma denúncia por aqui. Quando alguém reportar um conteúdo, ele aparece nesta fila."}</EstadoVazio>
      )}

      <section className="flex flex-col gap-3">
        {denuncias.map((denuncia) => (
          <article key={denuncia.id} className="flex flex-col gap-3 rounded-cartao bg-superficie p-5 shadow-cartao md:flex-row md:items-start md:justify-between">
            <div className="min-w-0">
              <div className="mb-1.5 flex flex-wrap gap-2">
                <Selo>{denuncia.motivo_rotulo}</Selo>
                <Selo tom={TOM[denuncia.status]}>{denuncia.status_rotulo}</Selo>
              </div>
              <h3 className="font-bold text-navy-900">{denuncia.material_titulo}</h3>
              <p className="mt-1 text-xs font-medium text-primaria">
                {[denuncia.autor_nome, denuncia.turma_nome, dataComAno(denuncia.criado_em)].filter(Boolean).join(" · ")}
              </p>
              {denuncia.descricao && <p className="mt-1.5 text-[13px] text-texto-secundario">{denuncia.descricao}</p>}
              {denuncia.acao && (
                <div className="mt-2.5 rounded-campo bg-fundo px-3 py-2 text-[13px]">
                  <strong className="text-navy-900">Ação registrada</strong>
                  <p className="mt-0.5 text-texto">{denuncia.acao}</p>
                </div>
              )}
            </div>
            <div className="flex shrink-0 flex-wrap gap-2">
              {(PROXIMOS_PASSOS[denuncia.status] || []).map(([proximo, rotulo]) => (
                <Botao key={proximo} variante="neutra" pequeno onClick={() => setTratando({ denuncia, status: proximo })}>{rotulo}</Botao>
              ))}
            </div>
          </article>
        ))}
      </section>

      {tratando && <ModalTratar {...tratando} aoFechar={() => setTratando(null)} aoSalvar={() => { setTratando(null); recarregar() }} />}
    </>
  )
}

function ModalTratar({ denuncia, status, aoFechar, aoSalvar }) {
  // Concluir e arquivar exigem dizer o que foi feito: é a resposta que quem
  // reportou recebe. O servidor confere; a tela avisa antes.
  const encerra = status === "concluida" || status === "arquivada"
  const [acao, setAcao] = useState(denuncia.acao || "")
  const [mensagem, setMensagem] = useState("")

  async function salvar(evento) {
    evento.preventDefault()
    try {
      const resultado = await (await api(`/admin/denuncias/${denuncia.id}`, { method: "POST", body: JSON.stringify({ status, acao: acao.trim() }) })).json()
      if (!resultado.sucesso) return setMensagem(resultado.mensagem)
      aoSalvar()
    } catch (erro) {
      console.error("Erro ao tratar denúncia:", erro)
      setMensagem(ERRO_DE_CONEXAO)
    }
  }

  return (
    <Modal aberto aoFechar={aoFechar} titulo={encerra ? "Encerrar denúncia" : "Atualizar denúncia"}>
      <p className="mb-4 text-sm text-texto-secundario">
        {encerra ? "Quem reportou recebe esta resposta pelo sino." : "A pessoa que reportou é avisada da mudança de status."}
      </p>
      <form onSubmit={salvar}>
        <AreaDeTexto rotulo={encerra ? "O que foi feito" : "Observação (opcional)"} valor={acao} aoMudar={setAcao} linhas={4} obrigatorio={encerra} />
        <MensagemDeFormulario texto={mensagem} />
        <AcoesDoModal>
          <Botao variante="neutra" onClick={aoFechar}>Cancelar</Botao>
          <Botao tipo="submit">Salvar</Botao>
        </AcoesDoModal>
      </form>
    </Modal>
  )
}
