import { useState } from "react"

import { Carregando, Cartao, EstadoVazio, Numero, Numeros } from "../../componentes/Cartao"
import { BarrasDeErro, Evolucao } from "../../componentes/Graficos"
import { SeletorDisciplina } from "../../componentes/SeletorDisciplina"
import { SeletorPeriodo } from "../../componentes/SeletorPeriodo"
import { useApi } from "../../hooks/useApi"
import { Cabecalho } from "../../layout/Painel"
import { diaCurto } from "../../lib/formatos"

/**
 * Desempenho do aluno. A pergunta que a tela responde não é "quanto eu
 * tirei" — isso está em Atividades —, é **"o que eu reviso primeiro"**: a
 * lista de tópicos ordenada por erro.
 *
 * O aproveitamento é ponderado pelos pontos, não média das notas: uma
 * atividade que vale 30 pesa mais que uma de 10. Média simples daria um
 * número mais bonito e menos verdadeiro. (A conta é do servidor.)
 */
export function Desempenho() {
  const [turma, setTurma] = useState(null)
  const [periodo, setPeriodo] = useState("")
  const turmas = useApi("/aluno/turmas")

  const consulta = new URLSearchParams()
  if (turma) consulta.set("turma_id", turma)
  if (periodo) consulta.set("dias", periodo)
  const { dados, carregando, erro } = useApi(`/aluno/desempenho${consulta.size ? `?${consulta}` : ""}`)
  const temNotas = dados?.sucesso && dados.notas.length > 0

  return (
    <>
      <Cabecalho titulo="Desempenho" descricao="Suas notas, sua evolução e em que assunto você mais erra.">
        {(turmas.dados?.turmas || []).length > 0 && <SeletorDisciplina turmas={turmas.dados.turmas} valor={turma} aoMudar={setTurma} comTodas />}
        <SeletorPeriodo valor={periodo} aoMudar={setPeriodo} />
      </Cabecalho>

      {carregando && <Carregando />}
      {erro && <EstadoVazio>{erro}</EstadoVazio>}
      {dados?.sucesso && !temNotas && <EstadoVazio>Você ainda não entregou nenhuma atividade no período escolhido.</EstadoVazio>}

      {temNotas && (
        <div className="flex flex-col gap-5">
          <Numeros>
            <Numero rotulo="Aproveitamento" valor={dados.resumo.aproveitamento == null ? "—" : `${dados.resumo.aproveitamento}%`} destaque />
            <Numero rotulo="Entregues" valor={dados.resumo.entregues} />
            <Numero rotulo="Aguardando correção" valor={dados.resumo.aguardando} />
            <Numero rotulo="Entregues com atraso" valor={dados.resumo.atrasadas} />
          </Numeros>

          {dados.topicos.length > 0 && (
            <Cartao titulo="Onde você mais erra">
              <p className="-mt-2 mb-4 text-[13px] text-texto-secundario">Sai das questões objetivas que você respondeu. Serve para decidir o que revisar primeiro.</p>
              <BarrasDeErro topicos={dados.topicos} detalhe={(t) => `${t.erros} de ${t.total} questão(ões) você errou`} />
            </Cartao>
          )}

          {dados.evolucao.length >= 2 && (
            <Cartao titulo="Evolução">
              <p className="-mt-2 mb-4 text-[13px] text-texto-secundario">Cada coluna é uma atividade corrigida, na ordem em que você entregou.</p>
              <Evolucao pontos={dados.evolucao} />
            </Cartao>
          )}

          <Cartao titulo="Suas notas">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-borda text-left text-xs text-texto-secundario">
                    <th className="py-2 pr-3 font-semibold">Atividade</th>
                    <th className="px-3 py-2 text-right font-semibold">Nota</th>
                    <th className="px-3 py-2 text-right font-semibold">%</th>
                    <th className="py-2 pl-3 text-right font-semibold">Entregue em</th>
                  </tr>
                </thead>
                <tbody>
                  {[...dados.notas].reverse().map((nota, indice) => (
                    <tr key={indice} className="border-b border-borda last:border-b-0">
                      <td className="py-2.5 pr-3">
                        {nota.titulo}
                        <span className="block text-xs text-texto-secundario">{[nota.turma_nome, nota.topico].filter(Boolean).join(" · ")}</span>
                      </td>
                      <td className="px-3 py-2.5 text-right whitespace-nowrap">
                        {nota.nota == null ? <span className="text-xs text-texto-secundario">aguardando correção</span> : <><strong>{nota.nota}</strong> de {nota.pontos}</>}
                      </td>
                      <td className="px-3 py-2.5 text-right">{nota.percentual == null ? "—" : `${nota.percentual}%`}</td>
                      <td className="py-2.5 pl-3 text-right whitespace-nowrap">
                        {diaCurto(nota.enviado_em)}
                        {nota.atrasada && <span className="block text-xs font-semibold text-perigo">atrasada</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Cartao>
        </div>
      )}
    </>
  )
}
