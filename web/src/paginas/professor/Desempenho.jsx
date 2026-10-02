import { useState } from "react"

import { Carregando, Cartao, EstadoVazio, Numero, Numeros } from "../../componentes/Cartao"
import { BarrasDeErro } from "../../componentes/Graficos"
import { SeletorPeriodo } from "../../componentes/SeletorPeriodo"
import { Celula, Tabela } from "../../componentes/Tabela"
import { useApi } from "../../hooks/useApi"
import { Cabecalho } from "../../layout/Painel"
import { diaCurto } from "../../lib/formatos"

const ou = (valor, sufixo = "") => (valor === null || valor === undefined ? "—" : `${valor}${sufixo}`)

/**
 * Desempenho na visão do professor. A tela existe por um número: **o erro
 * por tópico**. Média da turma diz que foi mal; erro por tópico diz onde foi
 * mal, e é isso que muda a aula seguinte.
 *
 * Disciplina sem atividade mostra estado vazio, e não gráfico de zeros:
 * número inventado aqui levaria a retrabalhar o assunto errado.
 */
export function DesempenhoProfessor() {
  const turmas = useApi("/turmas")
  const lista = turmas.dados?.turmas || []
  const [escolhida, setEscolhida] = useState(null)
  const [periodo, setPeriodo] = useState("")
  const turma = escolhida ?? lista[0]?.id ?? null
  const { dados, carregando, erro } = useApi(turma ? `/desempenho?turma_id=${turma}${periodo ? `&dias=${periodo}` : ""}` : null)
  const comAtividades = dados?.sucesso && dados.atividades.length > 0

  return (
    <>
      <Cabecalho titulo="Desempenho" descricao="Como a turma está indo e qual tópico precisa voltar na aula.">
        {lista.length > 0 && (
          <select aria-label="Disciplina" value={turma ?? ""} onChange={(e) => setEscolhida(Number(e.target.value))}
            className="rounded-campo border border-borda bg-superficie px-3 py-2.5 text-sm outline-none focus:border-primaria">
            {lista.map((t) => <option key={t.id} value={t.id}>{t.nome} · {t.semestre}</option>)}
          </select>
        )}
        <SeletorPeriodo valor={periodo} aoMudar={setPeriodo} />
      </Cabecalho>

      {(turmas.carregando || carregando) && <Carregando />}
      {(turmas.erro || erro) && <EstadoVazio>{turmas.erro || erro}</EstadoVazio>}
      {turmas.dados && lista.length === 0 && <EstadoVazio>Você ainda não tem disciplinas atribuídas.</EstadoVazio>}
      {dados?.sucesso && !comAtividades && <EstadoVazio>Nenhuma atividade publicada nesta disciplina no período escolhido.</EstadoVazio>}

      {comAtividades && (
        <div className="flex flex-col gap-5">
          <Numeros>
            <Numero rotulo="Alunos" valor={dados.resumo.total_alunos} />
            <Numero rotulo="Atividades publicadas" valor={dados.resumo.atividades} />
            <Numero rotulo="Média da turma" valor={ou(dados.resumo.media_percentual, "%")} destaque />
            <Numero rotulo="Taxa de entrega" valor={ou(dados.resumo.taxa_entrega, "%")} />
          </Numeros>

          {dados.topicos.length > 0 && (
            <Cartao titulo="Tópicos que a turma mais erra">
              <p className="-mt-2 mb-4 text-[13px] text-texto-secundario">Conta apenas questões objetivas, somando todos os alunos. Questão em branco entra como erro.</p>
              <BarrasDeErro topicos={dados.topicos} detalhe={(t) => `${t.erros} erro(s) em ${t.total} questão(ões) respondidas`} />
            </Cartao>
          )}

          <Cartao titulo="Por atividade">
            <Tabela colunas={["Atividade", { titulo: "Entregues", numero: true }, { titulo: "Pendentes", numero: true }, { titulo: "Média", numero: true }, { titulo: "Menor – maior", numero: true }]}>
              {dados.atividades.map((a) => (
                <tr key={a.id ?? a.titulo}>
                  <Celula detalhe={`${a.tipo === "objetiva" ? "Objetiva" : "Dissertativa"} · vale ${a.pontos}`}>{a.titulo}</Celula>
                  <Celula numero>{a.entregues}</Celula>
                  <Celula numero>{a.pendentes}</Celula>
                  <Celula numero>{ou(a.media)}</Celula>
                  <Celula numero>{ou(a.menor)} – {ou(a.maior)}</Celula>
                </tr>
              ))}
            </Tabela>
          </Cartao>

          <Cartao titulo="Por aluno">
            <Tabela colunas={["Aluno", { titulo: "Entregues", numero: true }, { titulo: "Atrasadas", numero: true }, { titulo: "Aproveitamento", numero: true }, { titulo: "Última entrega", numero: true }]}>
              {dados.alunos.map((a) => (
                <tr key={a.aluno_email}>
                  <Celula detalhe={a.aluno_email}>{a.aluno_nome}</Celula>
                  <Celula numero>{a.entregues}</Celula>
                  <Celula numero>{a.atrasadas > 0 ? <span className="font-semibold text-perigo">{a.atrasadas}</span> : 0}</Celula>
                  <Celula numero>{ou(a.aproveitamento, "%")}</Celula>
                  <Celula numero>{diaCurto(a.ultima_entrega)}</Celula>
                </tr>
              ))}
            </Tabela>
          </Cartao>
        </div>
      )}
    </>
  )
}
