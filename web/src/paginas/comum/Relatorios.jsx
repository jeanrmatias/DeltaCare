import { useEffect, useState } from "react"

import { Botao } from "../../componentes/Botao"
import { Carregando, Cartao, EstadoVazio, Numero, Numeros } from "../../componentes/Cartao"
import { Selo } from "../../componentes/Selo"
import { Celula, Tabela } from "../../componentes/Tabela"
import { useApi } from "../../hooks/useApi"
import { useSessao } from "../../hooks/useSessao"
import { Cabecalho } from "../../layout/Painel"
import { dataEHora } from "../../lib/formatos"
import { csvDoRelatorio, nomeDoCsv } from "../../lib/relatorios"

const ou = (valor, sufixo = "") => (valor === null || valor === undefined ? "—" : `${valor}${sufixo}`)
const porcento = (parte, total) => (total ? `${Math.round((100 * parte) / total)}%` : "—")

// O painel "ao vivo" busca de novo a cada tanto. Não é instantâneo (seria
// preciso uma conexão aberta por pessoa olhando), mas, para acompanhar uma
// turma estudando, meio minuto é o mesmo que agora.
const ATUALIZA_A_CADA_MS = 30_000

/**
 * Relatórios da turma: o que está acontecendo agora, o mês a mês e — só para
 * a administração — em que disciplina os alunos mais têm dificuldade.
 *
 * Uma tela para os dois perfis, como Mensagens: o servidor já recorta o que
 * cada um vê (o professor, só as disciplinas dele). Nenhum aluno aparece
 * identificado; o professor que quer saber de um aluno tem a tela Desempenho.
 */
export function Relatorios() {
  const { usuario } = useSessao()
  const adm = usuario.tipo === "adm"
  const turmas = useApi("/relatorios/turmas")
  const lista = turmas.dados?.turmas || []
  const [aba, setAba] = useState("ao-vivo")
  const [escolhida, setEscolhida] = useState(null)
  const turma = escolhida ?? lista[0]?.id ?? null
  const abas = [["ao-vivo", "Ao vivo"], ["mensal", "Por mês"], ...(adm ? [["dificuldade", "Dificuldade por disciplina"]] : [])]

  return (
    <>
      <Cabecalho titulo="Relatórios" descricao={adm
        ? "Desempenho das turmas, agora e mês a mês, e onde os alunos mais têm dificuldade."
        : "Desempenho da turma nas suas disciplinas, agora e mês a mês."}>
        {aba !== "dificuldade" && lista.length > 0 && (
          <select aria-label="Turma" value={turma ?? ""} onChange={(e) => setEscolhida(Number(e.target.value))}
            className="rounded-campo border border-borda-campo bg-superficie px-3 py-2.5 text-sm outline-none focus:border-primaria">
            {lista.map((t) => <option key={t.id} value={t.id}>{t.nome} · {t.semestre}</option>)}
          </select>
        )}
      </Cabecalho>

      <div role="tablist" aria-label="Relatórios" className="mb-5 flex flex-wrap gap-1 border-b border-borda">
        {abas.map(([chave, rotulo]) => (
          <button key={chave} type="button" role="tab" aria-selected={aba === chave} onClick={() => setAba(chave)}
            className={`-mb-px border-b-2 px-3.5 py-2 text-sm font-semibold ${aba === chave ? "border-primaria text-primaria" : "border-transparent text-texto-secundario hover:text-texto"}`}>
            {rotulo}
          </button>
        ))}
      </div>

      <div role="tabpanel">
        {aba === "dificuldade" ? <Dificuldade /> : (
          <>
            {turmas.carregando && <Carregando />}
            {turmas.erro && <EstadoVazio>{turmas.erro}</EstadoVazio>}
            {turmas.dados && !lista.length && (
              <EstadoVazio>{adm ? "Nenhuma turma criada ainda. Os relatórios são por turma (ex.: MED 3A)." : "Nenhuma das suas disciplinas está numa turma ainda."}</EstadoVazio>
            )}
            {turma && aba === "ao-vivo" && <AoVivo key={turma} coorteId={turma} />}
            {turma && aba === "mensal" && <Mensal key={turma} coorteId={turma} />}
          </>
        )}
      </div>
    </>
  )
}

// =========================================================================
// Ao vivo
// =========================================================================

const EVENTO = { entrega: "Entrega", material: "Material aberto", pergunta: "Pergunta ao assistente" }

function AoVivo({ coorteId }) {
  const { dados, carregando, erro, recarregar } = useApi(`/relatorios/ao-vivo?coorte_id=${coorteId}`)

  useEffect(() => {
    // Aba escondida não busca: ninguém está olhando, e o servidor agradece.
    const relogio = setInterval(() => { if (!document.hidden) recarregar() }, ATUALIZA_A_CADA_MS)
    return () => clearInterval(relogio)
  }, [recarregar])

  if (!dados && carregando) return <Carregando />
  if (erro) return <EstadoVazio>{erro}</EstadoVazio>
  if (!dados?.sucesso) return null
  const { agora, ultimas_24h: dia } = dados

  return (
    <div className="flex flex-col gap-5">
      <p className="text-[14px] text-texto-secundario" aria-live="polite">
        Atualiza sozinho a cada 30 segundos · última leitura: {dataEHora(dados.gerado_em)}
      </p>
      <Numeros>
        <Numero rotulo="Estudando na última hora" valor={agora.alunos_ativos} destaque={agora.alunos_ativos > 0} />
        <Numero rotulo="Alunos ativos em 24 h" valor={dia.alunos_ativos} />
        <Numero rotulo="Perguntas em 24 h" valor={dia.perguntas} />
        <Numero rotulo="Materiais abertos em 24 h" valor={dia.materiais_abertos} />
        <Numero rotulo="Entregas em 24 h" valor={dia.entregas} />
      </Numeros>

      <div className="grid gap-5 lg:grid-cols-2">
        <Cartao titulo="Atividades em aberto">
          {!dados.atividades_abertas.length ? <p className="text-sm text-texto-secundario">Nenhuma atividade com prazo por vir.</p> : (
            <ul className="flex flex-col gap-3">
              {dados.atividades_abertas.map((a) => (
                <li key={`${a.disciplina}-${a.titulo}`}>
                  <div className="flex justify-between gap-3 text-sm">
                    <span><strong className="text-navy-900">{a.titulo}</strong> · {a.disciplina}</span>
                    <span className="shrink-0 text-texto-secundario">{a.entregues}/{a.alunos}</span>
                  </div>
                  <Barra valor={a.alunos ? (100 * a.entregues) / a.alunos : 0} rotulo={`${a.entregues} de ${a.alunos} entregaram`} />
                  <p className="mt-1 text-xs text-texto-secundario">Prazo {dataEHora(a.prazo)} · aproveitamento até agora: {ou(a.aproveitamento, "%")}</p>
                </li>
              ))}
            </ul>
          )}
        </Cartao>

        <Cartao titulo="Acontecendo agora">
          {!dados.recentes.length ? <p className="text-sm text-texto-secundario">Nada registrado ainda nesta turma.</p> : (
            <ul className="flex flex-col divide-y divide-borda">
              {dados.recentes.map((e, indice) => (
                <li key={indice} className="flex justify-between gap-3 py-2 text-sm">
                  <span>{EVENTO[e.tipo]}{e.detalhe ? `: ${e.detalhe}` : ""} <span className="text-texto-secundario">· {e.disciplina}</span></span>
                  <span className="shrink-0 text-xs text-texto-secundario">{dataEHora(e.quando)}</span>
                </li>
              ))}
            </ul>
          )}
        </Cartao>
      </div>

      <Cartao titulo="O semestre até agora">
        <Tabela colunas={["Disciplina", { titulo: "Alunos", numero: true }, { titulo: "Aproveitamento", numero: true }, { titulo: "Entregas no prazo", numero: true }, { titulo: "Ativos em 7 dias", numero: true }]}>
          {dados.disciplinas.map((d) => (
            <tr key={d.id}>
              <Celula>{d.nome}</Celula>
              <Celula numero>{d.alunos}</Celula>
              <Celula numero>{ou(d.aproveitamento, "%")}</Celula>
              <Celula numero>{ou(d.no_prazo, "%")}</Celula>
              <Celula numero>{d.ativos_7_dias}</Celula>
            </tr>
          ))}
        </Tabela>
      </Cartao>
    </div>
  )
}

function Barra({ valor, rotulo }) {
  return (
    <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-fundo" role="img" aria-label={rotulo}>
      <div className="h-full rounded-full bg-marca" style={{ width: `${Math.min(100, Math.max(0, valor))}%` }} />
    </div>
  )
}

// =========================================================================
// Por mês
// =========================================================================

function Mensal({ coorteId }) {
  const { dados, carregando, erro } = useApi(`/relatorios/mensal?coorte_id=${coorteId}`)
  const [disciplina, setDisciplina] = useState("total")

  if (carregando) return <Carregando />
  if (erro) return <EstadoVazio>{erro}</EstadoVazio>
  if (!dados?.sucesso) return null
  if (!dados.meses.length) return <EstadoVazio>Ainda não há registro de estudo nesta turma: nenhuma entrega, material aberto ou pergunta ao assistente.</EstadoVazio>

  const bloco = (mes) => (disciplina === "total" ? mes.total : mes.disciplinas.find((d) => String(d.id) === disciplina))

  function baixar() {
    const url = URL.createObjectURL(new Blob([csvDoRelatorio(dados)], { type: "text/csv;charset=utf-8" }))
    const link = Object.assign(document.createElement("a"), { href: url, download: nomeDoCsv(dados.turma) })
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <label className="flex flex-col gap-1.5 text-[14px] font-medium text-texto">
          Ver
          <select value={disciplina} onChange={(e) => setDisciplina(e.target.value)}
            className="rounded-campo border border-borda-campo bg-superficie px-3 py-2 text-sm font-normal outline-none focus:border-primaria">
            <option value="total">A turma inteira</option>
            {dados.disciplinas.map((d) => <option key={d.id} value={String(d.id)}>{d.nome}</option>)}
          </select>
        </label>
        <Botao variante="neutra" onClick={baixar}>Baixar planilha (CSV)</Botao>
      </div>

      <Cartao titulo="Aproveitamento por mês">
        <BarrasDoMes meses={dados.meses.map((m) => ({ rotulo: m.rotulo, valor: bloco(m).notas.aproveitamento, detalhe: `${bloco(m).notas.corrigidas} nota(s)` }))}
          limite={dados.limite_dificuldade} />
      </Cartao>

      <Cartao titulo="Mês a mês">
        <Tabela colunas={["Mês", { titulo: "Aproveitamento", numero: true }, { titulo: "Entregas no prazo", numero: true },
          { titulo: "Não entregues", numero: true }, { titulo: "Alunos ativos", numero: true }, { titulo: "Dias de estudo", numero: true },
          ...(disciplina === "total" ? [{ titulo: "XP médio", numero: true }] : []), { titulo: "Perguntas", numero: true },
          { titulo: "Material respondeu", numero: true }]}>
          {dados.meses.map((mes) => {
            const { notas, entregas, engajamento, chat } = bloco(mes)
            const devidas = entregas.no_prazo + entregas.atrasadas + entregas.nao_entregues
            const respondidas = chat.completa + chat.parcial + chat.nenhuma + chat.sem_material
            return (
              <tr key={mes.mes}>
                <Celula>{mes.rotulo}</Celula>
                <Celula numero detalhe={`${notas.corrigidas} nota(s)`}>{ou(notas.aproveitamento, "%")}</Celula>
                <Celula numero detalhe={entregas.atrasadas ? `${entregas.atrasadas} atrasada(s)` : null}>{porcento(entregas.no_prazo, devidas)}</Celula>
                <Celula numero>{entregas.nao_entregues}</Celula>
                <Celula numero>{engajamento.alunos_ativos}/{engajamento.alunos}</Celula>
                <Celula numero detalhe="por aluno ativo">{ou(engajamento.dias_de_estudo_por_aluno)}</Celula>
                {disciplina === "total" && <Celula numero>{ou(engajamento.xp_medio)}</Celula>}
                <Celula numero>{chat.perguntas}</Celula>
                <Celula numero detalhe={chat.parcial ? `${chat.parcial} em parte` : null}>{porcento(chat.completa, respondidas)}</Celula>
              </tr>
            )
          })}
        </Tabela>
      </Cartao>

      <Cartao titulo="Como cada número é calculado">
        <ul className="list-disc space-y-1.5 pl-5 text-[14px] leading-relaxed text-texto-secundario">
          <li><strong>Aproveitamento:</strong> média de nota sobre pontos das atividades corrigidas, no mês em que o aluno entregou.</li>
          <li><strong>Entregas:</strong> atividades com prazo no mês, uma por aluno matriculado — no prazo, atrasada, ou não entregue (prazo vencido). Atividade sem prazo não entra; aluno que saiu da instituição também não.</li>
          <li><strong>Alunos ativos:</strong> quem abriu material, perguntou ao assistente ou entregou atividade no mês. Dias de estudo: quantos dias diferentes, em média, por aluno ativo.</li>
          <li><strong>XP médio:</strong> o XP do mês por aluno da turma, pelas mesmas regras da tela inicial do aluno.</li>
          <li><strong>Material respondeu:</strong> das perguntas ao assistente, as que o material cobriu por inteiro. O texto das perguntas nunca aparece aqui.</li>
        </ul>
      </Cartao>
    </div>
  )
}

/** Uma barra por mês; abaixo do limite de dificuldade ela fica amarela. */
function BarrasDoMes({ meses, limite }) {
  return (
    <div className="flex items-end gap-3 overflow-x-auto pb-1">
      {meses.map((m) => (
        <div key={m.rotulo} className="flex min-w-14 flex-col items-center gap-1" role="img"
          aria-label={`${m.rotulo}: ${m.valor === null ? "sem nota" : `${m.valor}%`}`}>
          <div className="flex h-36 w-8 items-end overflow-hidden rounded-campo bg-fundo">
            {m.valor !== null && (
              <div className={`w-full rounded-campo ${m.valor >= limite ? "bg-marca-sucesso" : "bg-alerta"}`} style={{ height: `${Math.max(m.valor, 3)}%` }} />
            )}
          </div>
          <span className="text-[12px] font-semibold text-texto">{ou(m.valor, "%")}</span>
          <span className="text-[12px] text-texto-secundario">{m.rotulo}</span>
          <span className="text-[11px] text-texto-secundario">{m.detalhe}</span>
        </div>
      ))}
    </div>
  )
}

// =========================================================================
// Dificuldade por disciplina (administração)
// =========================================================================

function Dificuldade() {
  const { dados, carregando, erro } = useApi("/admin/relatorios/dificuldade")

  if (carregando) return <Carregando />
  if (erro) return <EstadoVazio>{erro}</EstadoVazio>
  if (!dados?.sucesso) return null
  if (!dados.disciplinas.length) return <EstadoVazio>Nenhuma disciplina no semestre {dados.semestre}.</EstadoVazio>

  return (
    <div className="flex flex-col gap-5">
      <p className="max-w-3xl text-[14px] leading-relaxed text-texto-secundario">
        Disciplinas do semestre {dados.semestre}, da de <strong>menor aproveitamento</strong> para a de maior. Não há nota composta: atraso,
        entrega que não veio e pergunta que o material não respondeu aparecem ao lado, cada uma com o seu número — uma disciplina pode ter
        nota boa e metade das entregas faltando. Sem nome de aluno.
      </p>
      <section className="flex flex-col gap-3">
        {dados.disciplinas.map((d, posicao) => (
          <article key={d.id} className="rounded-cartao bg-superficie p-5 shadow-cartao">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="text-[17px] font-semibold text-navy-900">{d.aproveitamento !== null ? `${posicao + 1}. ` : ""}{d.nome}</h3>
                <p className="text-[14px] text-texto-secundario">{[d.turma, d.professor, `${d.alunos} aluno(s)`].filter(Boolean).join(" · ")}</p>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {d.aproveitamento === null && <Selo>Sem nota corrigida</Selo>}
                {d.aproveitamento !== null && d.poucos_dados && <Selo tom="alerta">Poucas notas ({d.corrigidas})</Selo>}
                {d.aproveitamento !== null && d.aproveitamento < dados.limite_dificuldade && <Selo tom="perigo">Abaixo de {dados.limite_dificuldade}%</Selo>}
              </div>
            </div>
            <dl className="mt-3 grid grid-cols-[repeat(auto-fit,minmax(150px,1fr))] gap-3 text-sm">
              <Dado rotulo="Aproveitamento" valor={ou(d.aproveitamento, "%")} detalhe={`${d.corrigidas} nota(s)`} />
              <Dado rotulo={`Alunos abaixo de ${dados.limite_dificuldade}%`} valor={d.alunos_com_nota ? `${d.alunos_com_dificuldade} de ${d.alunos_com_nota}` : "—"} />
              <Dado rotulo="Não entregues" valor={ou(d.nao_entregues, "%")} detalhe={d.atrasadas ? `${d.atrasadas}% atrasadas` : null} />
              <Dado rotulo="Material não respondeu" valor={ou(d.perguntas_sem_resposta_completa, "%")} detalhe={`${d.perguntas} pergunta(s) ao assistente`} />
              <Dado rotulo="Tópico com mais erro" valor={d.topico_mais_errado ? d.topico_mais_errado.topico : "—"}
                detalhe={d.topico_mais_errado ? `${d.topico_mais_errado.percentual_erro}% de erro` : null} />
            </dl>
          </article>
        ))}
      </section>
    </div>
  )
}

function Dado({ rotulo, valor, detalhe }) {
  return (
    <div>
      <dt className="text-xs text-texto-secundario">{rotulo}</dt>
      <dd className="font-semibold text-navy-900">{valor}</dd>
      {detalhe && <dd className="text-xs text-texto-secundario">{detalhe}</dd>}
    </div>
  )
}
