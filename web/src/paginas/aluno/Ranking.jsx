import { useState } from "react"

import { Carregando, Cartao, EstadoVazio } from "../../componentes/Cartao"
import { useApi } from "../../hooks/useApi"
import { useDialogo } from "../../hooks/useDialogo"
import { Cabecalho } from "../../layout/Painel"
import { api, ERRO_DE_CONEXAO } from "../../lib/api"
import { coresDaFaixa } from "../../lib/faixas"

/**
 * Ranking da turma, pelo XP do semestre: onde o aluno está (só ele vê), o
 * topo da turma e quem mais evoluiu na semana.
 *
 * O fundo da lista não aparece para ninguém — é a decisão central do módulo,
 * e ela é do servidor (regras/ranking.py). Esta tela só desenha o que chega,
 * e o que não chega não tem como vazar.
 */
export function Ranking() {
  const [coorte, setCoorte] = useState(null)
  const { dados, carregando, erro, recarregar } = useApi(`/aluno/ranking${coorte ? `?coorte_id=${coorte}` : ""}`)
  const pronto = dados?.sucesso && dados.coorte

  return (
    <>
      <Cabecalho titulo="Ranking" descricao={`Pelo XP do semestre.${pronto ? ` ${dados.coorte.nome} · semestre ${dados.semestre}` : ""}`}>
        {/* Só para quem está em mais de uma turma no semestre. */}
        {pronto && dados.coortes.length > 1 && (
          <select aria-label="Turma" value={dados.coorte.id} onChange={(evento) => setCoorte(evento.target.value)}
            className="rounded-campo border border-borda-campo bg-superficie px-3 py-2.5 text-sm outline-none focus:border-primaria">
            {dados.coortes.map((c) => <option key={c.id} value={c.id}>{c.nome}</option>)}
          </select>
        )}
      </Cabecalho>

      {carregando && !dados && <Carregando />}
      {erro && <EstadoVazio>{erro}</EstadoVazio>}
      {dados && !erro && !pronto && <EstadoVazio>{dados.mensagem || "Não foi possível carregar o ranking."}</EstadoVazio>}

      {pronto && (
        <div className="flex max-w-3xl flex-col gap-5">
          <MinhaPosicao dados={dados} aoMudar={recarregar} />

          <Cartao titulo="Topo da turma">
            <p className="-mt-2 mb-3 text-[13px] text-texto-secundario">Só o topo é mostrado. A posição de cada um, só a própria pessoa vê.</p>
            {dados.topo.length === 0 ? <p className="text-sm text-texto-secundario">Ninguém pontuou neste semestre ainda.</p> : (
              <ol className="flex flex-col gap-1.5">
                {dados.topo.map((linha) => (
                  <Linha key={linha.posicao} eu={linha.eu}>
                    <span className="w-8 shrink-0 text-sm font-bold text-navy-900">{linha.posicao}º</span>
                    <span className={`min-w-0 flex-1 truncate text-sm ${linha.nome ? "text-texto" : "text-texto-secundario italic"}`}>
                      {linha.nome ? (linha.eu ? `${linha.nome} (você)` : linha.nome) : "Colega que preferiu não aparecer"}
                    </span>
                    <SeloDeFaixa faixa={linha.faixa} />
                    <span className="w-20 shrink-0 text-right text-sm font-semibold text-texto">{linha.xp} XP</span>
                  </Linha>
                ))}
              </ol>
            )}
          </Cartao>

          <Cartao titulo={`Quem mais evoluiu nos últimos ${dados.dias_da_evolucao} dias`}>
            {dados.evoluiu.length === 0 ? <p className="text-sm text-texto-secundario">Ninguém estudou nesta semana ainda. Pode ser você.</p> : (
              <ol className="flex flex-col gap-1.5">
                {dados.evoluiu.map((linha, indice) => (
                  <Linha key={indice} eu={linha.eu}>
                    <span className="min-w-0 flex-1 truncate text-sm text-texto">{linha.eu ? `${linha.nome} (você)` : linha.nome}</span>
                    <span className="text-sm font-semibold text-sucesso">+{linha.xp_semana} XP</span>
                  </Linha>
                ))}
              </ol>
            )}
          </Cartao>
        </div>
      )}
    </>
  )
}

function Linha({ eu, children }) {
  return <li className={`flex items-center gap-3 rounded-campo px-3 py-2 ${eu ? "bg-primaria/10" : "bg-fundo"}`}>{children}</li>
}

function SeloDeFaixa({ faixa }) {
  const cores = coresDaFaixa(faixa?.chave)
  return (
    <span className="shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold tracking-wider text-white uppercase" style={{ background: cores.escura }}>
      {faixa?.nome}
    </span>
  )
}

function MinhaPosicao({ dados, aoMudar }) {
  const { eu, total, dias_da_evolucao: dias } = dados
  const [enviando, setEnviando] = useState(false)
  const { avisar } = useDialogo()

  async function alternar(evento) {
    const aparecer = evento.target.checked
    setEnviando(true)
    try {
      const resultado = await (await api("/aluno/ranking/visibilidade", { method: "PUT", body: JSON.stringify({ aparecer }) })).json()
      if (!resultado.sucesso) await avisar(resultado.mensagem || "Não foi possível mudar a visibilidade.", "Algo deu errado")
      aoMudar()
    } catch (erro) {
      console.error("Erro ao mudar a visibilidade:", erro)
      await avisar(ERRO_DE_CONEXAO, "Algo deu errado")
    } finally {
      setEnviando(false)
    }
  }

  return (
    <Cartao titulo="Sua posição">
      <div className="flex items-center gap-3">
        <strong className="text-2xl text-navy-900">{eu.xp > 0 ? `${eu.posicao}º de ${total}` : "Ainda sem pontos"}</strong>
        <SeloDeFaixa faixa={eu.faixa} />
      </div>
      <p className="mt-1.5 text-[13px] text-texto-secundario">
        {eu.xp > 0
          ? `${eu.xp} XP neste semestre · ${eu.xp_semana} nos últimos ${dias} dias`
          : "Abra um material, pergunte ao assistente ou entregue uma atividade para entrar no ranking."}
      </p>
      <label className="mt-4 flex items-center gap-2.5 text-sm text-texto">
        <input type="checkbox" checked={eu.aparece} onChange={alternar} disabled={enviando} className="size-4 accent-primaria" />
        Aparecer no ranking da turma
      </label>
      <p className="mt-1.5 text-[13px] text-texto-secundario">
        {eu.aparece
          ? "Os colegas veem seu nome se você estiver no topo."
          : "Os colegas veem \"colega que preferiu não aparecer\" no seu lugar. Sua posição continua visível só para você."}
      </p>
    </Cartao>
  )
}
