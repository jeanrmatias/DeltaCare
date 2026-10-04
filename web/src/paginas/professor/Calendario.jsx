import { useState } from "react"
import { Link } from "react-router"

import { Carregando, Cartao, EstadoVazio } from "../../componentes/Cartao"
import { useApi } from "../../hooks/useApi"
import { Cabecalho } from "../../layout/Painel"
import { DIAS_CURTOS, MESES } from "../../lib/datas"
import { rotaDoLink } from "../../lib/rotas"

/**
 * Calendário do professor. Materiais e Atividades respondem "o que eu
 * publiquei"; esta responde "o que acontece na semana que vem" — e é a única
 * que mostra os **prazos** fora de dentro da atividade.
 *
 * Daí o aviso de conflito no topo: dois prazos no mesmo dia é o que o
 * professor hoje só descobre quando os alunos reclamam.
 */
export function Calendario() {
  const turmas = useApi("/turmas")
  const [turma, setTurma] = useState(null)
  const [mes, setMes] = useState(() => primeiroDoMes(new Date()))
  const [escolhido, setEscolhido] = useState(null)

  const consulta = `ano=${mes.getFullYear()}&mes=${mes.getMonth() + 1}${turma ? `&turma_id=${turma}` : ""}`
  const { dados, carregando } = useApi(`/calendario?${consulta}`)

  const porDia = {}
  for (const evento of dados?.eventos || []) (porDia[evento.dia] ||= []).push(evento)

  // Sem escolha: hoje, se tiver evento; senão o primeiro dia com evento.
  const hoje = chaveDoDia(new Date())
  const dia = escolhido ?? (porDia[hoje] ? hoje : Object.keys(porDia).sort()[0] ?? null)
  const conflitos = dados?.resumo?.dias_com_dois_prazos || []
  const lista = turmas.dados?.turmas || []

  function mudarMes(passo) {
    setMes(new Date(mes.getFullYear(), mes.getMonth() + passo, 1))
    setEscolhido(null)
  }

  return (
    <>
      <Cabecalho titulo="Calendário" descricao="O semestre por data: o que foi publicado, o que está agendado e quando vence.">
        {lista.length > 0 && (
          <select aria-label="Disciplina" value={turma ?? ""} onChange={(e) => { setTurma(e.target.value ? Number(e.target.value) : null); setEscolhido(null) }}
            className="rounded-campo border border-borda-campo bg-superficie px-3 py-2.5 text-sm outline-none focus:border-primaria">
            <option value="">Todas as disciplinas</option>
            {lista.map((t) => <option key={t.id} value={t.id}>{t.nome} · {t.semestre}</option>)}
          </select>
        )}
      </Cabecalho>

      {turmas.dados && lista.length === 0 && <EstadoVazio>Você ainda não tem disciplinas atribuídas.</EstadoVazio>}

      {conflitos.length > 0 && (
        <p className="mb-5 rounded-campo border-l-3 border-alerta bg-alerta-fundo px-4 py-3 text-[14.5px] text-texto">
          {conflitos.length === 1
            ? `Atenção: há mais de uma entrega marcada para ${rotuloLongo(conflitos[0])}.`
            : `Atenção: há mais de uma entrega marcada nestes dias — ${conflitos.map(rotuloLongo).join(", ")}.`}
        </p>
      )}

      {lista.length > 0 && (
        <section className="grid gap-5 min-[1101px]:grid-cols-[1fr_380px]">
          <Cartao>
            <div className="mb-3 flex items-center justify-between">
              <button type="button" aria-label="Mês anterior" onClick={() => mudarMes(-1)} className="rounded-campo px-3 py-1 text-xl hover:bg-fundo">‹</button>
              <h2 className="text-base font-semibold text-navy-900">{MESES[mes.getMonth()]} de {mes.getFullYear()}</h2>
              <button type="button" aria-label="Próximo mês" onClick={() => mudarMes(1)} className="rounded-campo px-3 py-1 text-xl hover:bg-fundo">›</button>
            </div>
            <div className="grid grid-cols-7 gap-1.5 text-center">
              {DIAS_CURTOS.map((d) => <span key={d} className="text-xs font-semibold text-texto-secundario">{d}</span>)}
              {celulasDoMes(mes).map((chave, i) => chave ? (
                <button key={chave} type="button" onClick={() => setEscolhido(chave)} aria-pressed={chave === dia}
                  className={`flex min-h-12 flex-col items-center justify-start gap-1 rounded-campo pt-1.5 text-sm ${chave === dia ? "bg-primaria text-white"
                    : chave === hoje ? "border border-primaria text-primaria" : "hover:bg-fundo"}`}>
                  {Number(chave.slice(8))}
                  <span className="flex gap-0.5">
                    {[...new Set((porDia[chave] || []).map((e) => COR_DO_TIPO[e.tipo]).filter(Boolean))].map((cor) => (
                      <i key={cor} className={`size-1.5 rounded-full ${cor}`} />
                    ))}
                  </span>
                </button>
              ) : <span key={`vazio-${i}`} />)}
            </div>
            <div className="mt-4 flex flex-wrap gap-4 text-xs text-texto-secundario">
              <span className="flex items-center gap-1.5"><i className="size-2 rounded-full bg-marca" /> Material</span>
              <span className="flex items-center gap-1.5"><i className="size-2 rounded-full bg-marca-sucesso" /> Atividade</span>
              <span className="flex items-center gap-1.5"><i className="size-2 rounded-full bg-alerta" /> Prazo</span>
            </div>
          </Cartao>

          <Cartao titulo={dia ? rotuloLongo(dia) : "Nada neste mês"}>
            {carregando && <Carregando />}
            {!dia && dados && <p className="text-sm text-texto-secundario">Nenhum material, atividade ou prazo neste mês.</p>}
            {dia && !(porDia[dia] || []).length && <p className="text-sm text-texto-secundario">Nada marcado para este dia.</p>}
            <div className="flex flex-col gap-2.5">
              {(porDia[dia] || []).map((evento, i) => (
                <article key={i} className="flex items-start gap-3 rounded-bloco bg-fundo p-3">
                  <i className={`mt-1.5 size-2 shrink-0 rounded-full ${COR_DO_TIPO[evento.tipo] || "bg-marca"}`} />
                  <div className="min-w-0 flex-1">
                    <strong className="block text-sm text-texto">{evento.titulo}</strong>
                    <span className="block text-xs text-texto-secundario">{evento.detalhe}{evento.hora ? ` · ${evento.hora}` : ""}</span>
                    <span className="block text-xs font-medium text-primaria">{evento.turma_nome}</span>
                  </div>
                  {rotaDoLink(evento.link, "professor") && (
                    <Link to={rotaDoLink(evento.link, "professor")} className="shrink-0 rounded-campo border border-borda bg-superficie px-3 py-1.5 text-xs font-semibold hover:bg-fundo">Abrir</Link>
                  )}
                </article>
              ))}
            </div>
          </Cartao>
        </section>
      )}
    </>
  )
}

const COR_DO_TIPO = {
  material: "bg-marca",
  material_agendado: "bg-marca",
  atividade: "bg-marca-sucesso",
  atividade_agendada: "bg-marca-sucesso",
  prazo: "bg-alerta",
}

const primeiroDoMes = (data) => new Date(data.getFullYear(), data.getMonth(), 1)
const dois = (n) => String(n).padStart(2, "0")
const chaveDoDia = (data) => `${data.getFullYear()}-${dois(data.getMonth() + 1)}-${dois(data.getDate())}`

/** "2026-09-26" como data local — sem isto o dia volta um no fuso de Brasília. */
function rotuloLongo(dia) {
  const data = new Date(Number(dia.slice(0, 4)), Number(dia.slice(5, 7)) - 1, Number(dia.slice(8, 10)))
  return data.toLocaleDateString("pt-BR", { weekday: "long", day: "2-digit", month: "long" })
}

function celulasDoMes(mes) {
  const total = new Date(mes.getFullYear(), mes.getMonth() + 1, 0).getDate()
  return [
    ...Array(mes.getDay()).fill(null),
    ...Array.from({ length: total }, (_, i) => chaveDoDia(new Date(mes.getFullYear(), mes.getMonth(), i + 1))),
  ]
}
