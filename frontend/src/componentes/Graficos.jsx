/**
 * Os dois gráficos do desempenho, usados pelo aluno e pelo professor. Feitos
 * com divs e CSS — sem biblioteca de gráfico: são barras, e uma dependência
 * de centenas de KB para desenhar barras seria desproporcional.
 */
import { diaCurto } from "../lib/formatos"

/**
 * Tópicos ordenados por erro. Responde "o que revisar primeiro" — e a barra
 * fica vermelha a partir de 50%, onde a revisão deixa de ser opcional.
 * `detalhe(t)` escreve a linha de baixo (o aluno lê "você errou", o
 * professor lê "a turma errou").
 */
export function BarrasDeErro({ topicos, detalhe }) {
  return (
    <div className="flex flex-col gap-4">
      {topicos.map((topico) => (
        <div key={topico.topico}>
          <div className="mb-1.5 flex justify-between gap-3 text-sm">
            <span className="text-texto">{topico.topico}</span>
            <strong className="text-navy-900">{topico.percentual_erro}% de erro</strong>
          </div>
          <div className="h-2.5 overflow-hidden rounded-full bg-fundo">
            <div className={`h-full rounded-full ${topico.percentual_erro >= 50 ? "bg-marca-perigo" : "bg-alerta"}`}
              style={{ width: `${Math.max(topico.percentual_erro, 2)}%` }} />
          </div>
          <span className="mt-1 block text-xs text-texto-secundario">{detalhe(topico)}</span>
        </div>
      ))}
    </div>
  )
}

/** Uma coluna por atividade corrigida, na ordem. Verde a partir de 60%. */
export function Evolucao({ pontos }) {
  return (
    <div className="flex items-end gap-2 overflow-x-auto pb-1">
      {pontos.map((ponto, indice) => {
        const percentual = ponto.percentual ?? 0
        return (
          <div key={indice} title={`${ponto.titulo}: ${ponto.percentual}%`} className="flex min-w-11 flex-col items-center gap-1">
            <div className="flex h-36 w-7 items-end overflow-hidden rounded-campo bg-fundo">
              <div className={`w-full rounded-campo ${percentual >= 60 ? "bg-marca-sucesso" : "bg-alerta"}`} style={{ height: `${Math.max(percentual, 3)}%` }} />
            </div>
            <span className="text-[12px] font-semibold text-texto">{ponto.percentual}%</span>
            <span className="text-[11px] text-texto-secundario">{diaCurto(ponto.data)}</span>
          </div>
        )
      })}
    </div>
  )
}
