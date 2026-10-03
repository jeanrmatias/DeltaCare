import { useEffect, useId, useRef, useState } from "react"

import { DIAS_CURTOS, formatarParaCampo, interpretarDataDigitada, lerIso, MESES, mesmoDia } from "../lib/datas"
import { Icone } from "./Icone"

/**
 * Data e hora, para agendar material e dar prazo de atividade.
 *
 * Substitui o <input type="datetime-local">: o calendário dele muda de cara
 * em cada navegador e digitar nele é desconfortável. Aqui são duas portas:
 * digitar (`5/3 14:00` serve) ou escolher no calendário, com atalhos.
 *
 * Controlado: `valor` é ISO (ou null) e `aoMudar` recebe ISO (ou null) — o
 * formato que o backend guarda.
 */
export function SeletorDataHora({ rotulo, valor, aoMudar, dica }) {
  const id = useId()
  const area = useRef(null)
  const selecionada = lerIso(valor)
  const [texto, setTexto] = useState(() => formatarParaCampo(selecionada))
  const [invalida, setInvalida] = useState(false)
  const [aberto, setAberto] = useState(false)
  const [mesVisivel, setMesVisivel] = useState(() => primeiroDoMes(selecionada || new Date()))

  // Valor trocado por fora (o "Limpar" de quem usa, outro item para editar):
  // o texto acompanha. É o padrão do React para ajustar estado quando a prop
  // muda — guardar o valor anterior em estado e comparar na renderização.
  const [valorAnterior, setValorAnterior] = useState(valor)
  if (valorAnterior !== valor) {
    setValorAnterior(valor)
    const formatado = formatarParaCampo(selecionada)
    if (formatarParaCampo(interpretarDataDigitada(texto)) !== formatado) setTexto(formatado)
  }

  useEffect(() => {
    if (!aberto) return undefined
    const fora = (evento) => !area.current?.contains(evento.target) && setAberto(false)
    document.addEventListener("click", fora)
    return () => document.removeEventListener("click", fora)
  }, [aberto])

  function digitar(novo) {
    setTexto(novo)
    const lida = interpretarDataDigitada(novo)
    setInvalida(!lida && novo.trim().length >= 5)
    if (lida) setMesVisivel(primeiroDoMes(lida))
    aoMudar(lida ? lida.toISOString() : null)
  }

  function escolher(data) {
    setTexto(formatarParaCampo(data))
    setInvalida(false)
    aoMudar(data.toISOString())
  }

  function escolherDia(dia) {
    // Mantém a hora que já estava escolhida: trocar o dia não zera o horário.
    const base = selecionada || new Date(dia.getFullYear(), dia.getMonth(), dia.getDate(), 0, 0)
    escolher(new Date(dia.getFullYear(), dia.getMonth(), dia.getDate(), base.getHours(), base.getMinutes()))
  }

  function atalho(dias) {
    const alvo = new Date()
    alvo.setDate(alvo.getDate() + dias)
    setMesVisivel(primeiroDoMes(alvo))
    escolherDia(alvo)
  }

  function limpar() {
    setTexto("")
    setInvalida(false)
    aoMudar(null)
    setAberto(false)
  }

  return (
    <div ref={area} className="relative"
      onKeyDown={(evento) => { if (evento.key === "Escape" && aberto) { evento.stopPropagation(); setAberto(false) } }}>
      {rotulo && <label htmlFor={id} className="mb-1.5 block text-[13px] font-medium text-texto">{rotulo}</label>}
      <div className={`flex rounded-campo border bg-superficie focus-within:border-primaria ${invalida ? "border-perigo" : "border-borda"}`}>
        <input id={id} value={texto} onChange={(evento) => digitar(evento.target.value)}
          onBlur={() => selecionada && setTexto(formatarParaCampo(selecionada))}
          placeholder="dd/mm/aaaa hh:mm" autoComplete="off" inputMode="numeric" aria-invalid={invalida}
          className="min-w-0 flex-1 rounded-campo bg-transparent px-3 py-2.5 text-sm outline-none" />
        <button type="button" onClick={() => { setMesVisivel(primeiroDoMes(selecionada || new Date())); setAberto((a) => !a) }}
          aria-label="Abrir calendário" aria-expanded={aberto} className="px-3 text-texto-secundario hover:text-primaria">
          <Icone nome="calendario" tamanho={16} />
        </button>
      </div>
      {invalida && <span className="mt-1 block text-xs text-perigo">Data não reconhecida. Use dd/mm/aaaa hh:mm.</span>}
      {dica && !invalida && <span className="mt-1 block text-xs text-texto-secundario">{dica}</span>}

      {aberto && (
        <div className="absolute z-30 mt-2 w-[min(290px,calc(100vw-3rem))] rounded-cartao bg-superficie p-4 shadow-xl">
          <div className="mb-3 flex items-center justify-between">
            <button type="button" aria-label="Mês anterior" onClick={() => setMesVisivel(somarMeses(mesVisivel, -1))}
              className="rounded-campo px-2 py-1 text-lg hover:bg-fundo">‹</button>
            <strong className="text-sm text-navy-900">{MESES[mesVisivel.getMonth()]} de {mesVisivel.getFullYear()}</strong>
            <button type="button" aria-label="Próximo mês" onClick={() => setMesVisivel(somarMeses(mesVisivel, 1))}
              className="rounded-campo px-2 py-1 text-lg hover:bg-fundo">›</button>
          </div>
          <div className="grid grid-cols-7 gap-1 text-center">
            {DIAS_CURTOS.map((d) => <span key={d} className="text-[11px] font-semibold text-texto-secundario">{d}</span>)}
            {diasDoMes(mesVisivel).map((dia, i) => dia ? (
              <button key={i} type="button" onClick={() => escolherDia(dia)}
                className={`rounded-campo py-1.5 text-[13px] ${mesmoDia(dia, selecionada) ? "bg-primaria font-bold text-white"
                  : mesmoDia(dia, new Date()) ? "border border-primaria text-primaria" : "hover:bg-fundo"}`}>
                {dia.getDate()}
              </button>
            ) : <span key={i} />)}
          </div>
          <label className="mt-3 flex items-center gap-2 text-[13px] text-texto">
            Hora
            <input type="time" value={selecionada ? formatarParaCampo(selecionada).slice(11) : ""}
              onChange={(evento) => {
                const [h, m] = evento.target.value.split(":").map(Number)
                if (Number.isNaN(h)) return
                const base = selecionada || new Date()
                escolher(new Date(base.getFullYear(), base.getMonth(), base.getDate(), h, m || 0))
              }}
              className="rounded-campo border border-borda-campo px-2 py-1 text-sm" />
          </label>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {[["Hoje", 0], ["Amanhã", 1], ["Em 7 dias", 7]].map(([nome, dias]) => (
              <button key={nome} type="button" onClick={() => atalho(dias)} className="rounded-campo bg-fundo px-2.5 py-1 text-xs font-semibold text-texto hover:bg-borda">{nome}</button>
            ))}
            <button type="button" onClick={limpar} className="rounded-campo px-2.5 py-1 text-xs font-semibold text-perigo hover:bg-perigo-fundo">Limpar</button>
          </div>
        </div>
      )}
    </div>
  )
}

const primeiroDoMes = (data) => new Date(data.getFullYear(), data.getMonth(), 1)
const somarMeses = (data, n) => new Date(data.getFullYear(), data.getMonth() + n, 1)

/** As células do mês: null para os dias em branco antes do dia 1. */
function diasDoMes(mes) {
  const total = new Date(mes.getFullYear(), mes.getMonth() + 1, 0).getDate()
  return [
    ...Array(mes.getDay()).fill(null),
    ...Array.from({ length: total }, (_, i) => new Date(mes.getFullYear(), mes.getMonth(), i + 1)),
  ]
}
