import { Cartao } from "../../componentes/Cartao"
import { coresDaFaixa } from "../../lib/faixas"

/**
 * O progresso do semestre: escudo com o nível, barra de XP, sequência de
 * dias, de onde veio o XP e a frequência dos últimos 14 dias.
 *
 * Todo número vem pronto do servidor (regras/aluno.py). A tela não sabe os
 * limites de nível nem de faixa: se soubesse, mudar a regra exigiria mudar os
 * dois lugares e lembrar dos dois.
 */
export function CartaoProgresso({ progresso }) {
  const percentual = Math.round((progresso.xp_no_nivel / progresso.xp_para_proximo_nivel) * 100)
  const faltamXp = progresso.xp_para_proximo_nivel - progresso.xp_no_nivel

  return (
    <Cartao className="mb-5">
      <div className="flex flex-wrap items-center gap-[22px] md:flex-nowrap">
        <Escudo nivel={progresso.nivel} faixa={progresso.faixa} percentual={percentual} />

        <div className="min-w-0 flex-1">
          <div className="mb-2 flex items-baseline justify-between gap-3">
            <strong className="text-[19px] text-navy-900">{progresso.xp} XP</strong>
            <span className="text-[12.5px] text-texto-secundario">
              faltam {faltamXp} XP para o nível {progresso.nivel + 1}
            </span>
          </div>
          <div className="h-2.5 overflow-hidden rounded-full bg-fundo">
            <div
              className="h-full rounded-full bg-linear-to-r from-primaria to-[#5B93FF] transition-[width] duration-500"
              style={{ width: `${percentual}%` }}
            />
          </div>
          <MetaDaFaixa progresso={progresso} />
          <Semestre progresso={progresso} />
        </div>

        {/* "0 dias seguidos" seria um lembrete de fracasso, não um incentivo. */}
        {progresso.sequencia > 0 && (
          <div className="flex shrink-0 flex-col items-center rounded-bloco bg-alerta-fundo px-4 py-2.5 text-[#92400E]">
            <strong className="text-[22px] leading-none">{progresso.sequencia}</strong>
            <span className="mt-0.5 text-[11px] font-semibold">dias seguidos</span>
          </div>
        )}
      </div>

      <div className="mt-[22px] grid gap-6 border-t border-borda pt-5 md:grid-cols-2">
        <Composicao itens={progresso.composicao || []} />
        <Frequencia dias={progresso.acompanhamento || []} totalDiasAtivos={progresso.dias_ativos || 0} />
      </div>
    </Cartao>
  )
}

// O mesmo polígono no anel e no escudo: com formas diferentes, a ponta de
// baixo do escudo ficaria longe do anel.
const FORMA_DE_ESCUDO = "polygon(50% 0%, 100% 14%, 100% 58%, 50% 100%, 0% 58%, 0% 14%)"

/**
 * O anel em volta do escudo enche conforme o avanço no nível: a forma
 * informa, em vez de só enfeitar.
 */
function Escudo({ nivel, faixa, percentual }) {
  const cores = coresDaFaixa(faixa?.chave)

  return (
    <div className="flex shrink-0 flex-col items-center gap-1.5">
      <div
        className="flex size-[78px] items-center justify-center p-[5px]"
        style={{
          clipPath: FORMA_DE_ESCUDO,
          background: `conic-gradient(${cores.clara} ${percentual}%, var(--color-borda) ${percentual}%)`,
        }}
      >
        <div
          className="flex size-full flex-col items-center justify-center gap-px text-white"
          style={{ clipPath: FORMA_DE_ESCUDO, background: `linear-gradient(150deg, ${cores.clara}, ${cores.escura})` }}
        >
          <span className="text-[9px] font-semibold tracking-widest uppercase opacity-70">Nível</span>
          <span className="text-2xl leading-none font-bold tabular-nums">{nivel}</span>
        </div>
      </div>
      {faixa && (
        <span className="text-[11px] font-bold tracking-[0.1em] uppercase" style={{ color: cores.clara }}>
          {faixa.nome}
        </span>
      )}
    </div>
  )
}

/**
 * "Faltam N níveis para Prata" — sem o próximo degrau visível, a faixa é só
 * um adjetivo. Em Platina não há próximo, e a frase muda em vez de prometer.
 */
function MetaDaFaixa({ progresso }) {
  const faixa = progresso.faixa
  if (!faixa) return null

  let texto = "Faixa máxima — e o nível continua subindo."
  if (faixa.proxima) {
    const faltam = faixa.nivel_da_proxima - progresso.nivel
    texto = faltam === 1 ? `Falta 1 nível para ${faixa.proxima}.` : `Faltam ${faltam} níveis para ${faixa.proxima}.`
  }
  return <span className="mt-1.5 block text-xs text-texto-secundario">{texto}</span>
}

/**
 * Nível e faixa são do semestre. Sem dizer isso, a virada de semestre
 * pareceria o sistema perdendo o XP — o total acumulado mostra que não.
 */
function Semestre({ progresso }) {
  if (!progresso.semestre) return null
  const total = progresso.xp_total ?? progresso.xp

  return (
    <span className="mt-1.5 block text-xs text-texto-secundario">
      Semestre {progresso.semestre}
      {total > progresso.xp && ` · ${total} XP desde o início`}
    </span>
  )
}

/** De onde veio o XP. XP sem origem explicada não engaja, irrita. */
function Composicao({ itens }) {
  return (
    <div>
      {itens.map((item) => (
        <div key={item.rotulo} className="flex items-center justify-between gap-3 py-[7px] text-[13px]">
          <span className="text-texto-secundario">{item.rotulo}</span>
          <span className="font-semibold whitespace-nowrap text-texto">
            {item.quantidade} · {item.xp} XP
          </span>
        </div>
      ))}
    </div>
  )
}

function Frequencia({ dias, totalDiasAtivos }) {
  const ativos = dias.filter((dia) => dia.ativo).length

  return (
    <div>
      <span className="mb-2.5 block text-xs font-semibold tracking-wide text-texto-secundario uppercase">Últimos 14 dias</span>
      <div className="mb-2.5 flex flex-wrap gap-[5px]">
        {dias.map((entrada) => {
          const rotulo = new Date(`${entrada.dia}T12:00:00`).toLocaleDateString("pt-BR", { day: "2-digit", month: "short" })
          const estado = entrada.ativo ? "com estudo" : "sem registro"
          return (
            <span
              key={entrada.dia}
              title={`${rotulo} — ${estado}`}
              aria-label={`${rotulo}, ${estado}`}
              className={`size-[18px] rounded border ${entrada.ativo ? "border-primaria bg-primaria" : "border-borda bg-fundo"}`}
            />
          )
        })}
      </div>
      <span className="text-xs text-texto-secundario">
        {ativos === 0
          ? "Nenhum estudo registrado nas últimas duas semanas."
          : `${ativos} de ${dias.length} dias com estudo · ${totalDiasAtivos} no total`}
      </span>
    </div>
  )
}
