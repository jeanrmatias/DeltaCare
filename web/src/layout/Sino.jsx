import { useCallback, useEffect, useRef, useState } from "react"
import { useNavigate } from "react-router"

import { Icone } from "../componentes/Icone"
import { useSessao } from "../hooks/useSessao"
import { api } from "../lib/api"
import { aoMudarNotificacoes } from "../lib/eventos"
import { rotaDoLink } from "../lib/rotas"

// Um minuto: nada aqui é urgente a ponto de valer mais tráfego.
const INTERVALO = 60_000

/**
 * O sino de notificações, com o número de não lidas vindo do servidor e o
 * painel com os eventos que aconteceram de fato. Fica no Painel, então vale
 * para todas as telas logadas.
 */
export function Sino() {
  const { usuario } = useSessao()
  const navegar = useNavigate()
  const [dados, setDados] = useState({ notificacoes: [], nao_lidas: 0 })
  const [aberto, setAberto] = useState(false)
  const area = useRef(null)

  const carregar = useCallback(async () => {
    try {
      const resposta = await (await api("/notificacoes")).json()
      if (resposta.sucesso) setDados({ notificacoes: resposta.notificacoes || [], nao_lidas: resposta.nao_lidas || 0 })
    } catch {
      /* o sino é complemento: falhar aqui não atrapalha a tela */
    }
  }, [])

  // Busca ao abrir a tela, a cada minuto, e quando outra parte avisa (ler
  // uma conversa zera a notificação dela). A limpeza desliga tudo ao sair.
  useEffect(() => {
    const primeira = setTimeout(carregar, 0)
    const relogio = setInterval(carregar, INTERVALO)
    const desligar = aoMudarNotificacoes(carregar)
    return () => { clearTimeout(primeira); clearInterval(relogio); desligar() }
  }, [carregar])

  // Fecha clicando fora ou com Esc.
  useEffect(() => {
    if (!aberto) return undefined
    const fora = (evento) => !area.current?.contains(evento.target) && setAberto(false)
    const esc = (evento) => evento.key === "Escape" && setAberto(false)
    document.addEventListener("click", fora)
    document.addEventListener("keydown", esc)
    return () => { document.removeEventListener("click", fora); document.removeEventListener("keydown", esc) }
  }, [aberto])

  async function abrirNotificacao(notificacao) {
    if (!notificacao.lida) await api(`/notificacoes/${notificacao.id}/lida`, { method: "POST" }).catch(() => {})
    setAberto(false)
    carregar()
    const destino = rotaDoLink(notificacao.link, usuario.tipo)
    if (destino) navegar(destino)
  }

  async function marcarTodas() {
    await api("/notificacoes/lidas", { method: "POST" }).catch(() => {})
    carregar()
  }

  const rotulo = dados.nao_lidas ? `Notificações: ${dados.nao_lidas} não lida(s)` : "Notificações"

  return (
    <div ref={area} className="relative">
      <button type="button" onClick={() => setAberto((atual) => !atual)} aria-label={rotulo} aria-expanded={aberto}
        className="relative flex size-10 items-center justify-center rounded-full bg-superficie text-texto shadow-cartao hover:text-primaria">
        <Icone nome="sino" />
        {dados.nao_lidas > 0 && (
          <span className="absolute -top-0.5 -right-0.5 flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-perigo px-1 text-[10px] font-bold text-white">
            {dados.nao_lidas > 9 ? "9+" : dados.nao_lidas}
          </span>
        )}
      </button>

      {aberto && (
        <div role="region" aria-label="Notificações"
          className="absolute right-0 z-20 mt-2 w-[min(340px,calc(100vw-2rem))] overflow-hidden rounded-cartao bg-superficie shadow-xl">
          <div className="flex items-center justify-between border-b border-borda px-4 py-3">
            <strong className="text-sm text-navy-900">Notificações</strong>
            <button type="button" onClick={marcarTodas} className="text-xs font-semibold text-primaria hover:underline">Marcar todas como lidas</button>
          </div>
          <ul className="max-h-[60vh] overflow-y-auto">
            {dados.notificacoes.length === 0 && <li className="px-4 py-6 text-center text-sm text-texto-secundario">Nenhuma notificação por aqui.</li>}
            {dados.notificacoes.map((notificacao) => (
              <li key={notificacao.id} className="border-b border-borda last:border-b-0">
                <button type="button" onClick={() => abrirNotificacao(notificacao)}
                  className={`flex w-full flex-col gap-0.5 px-4 py-3 text-left hover:bg-fundo ${notificacao.lida ? "" : "bg-primaria/5"}`}>
                  <strong className="text-[13px] text-texto">{notificacao.titulo}</strong>
                  <span className="text-[13px] text-texto-secundario">{notificacao.mensagem}</span>
                  <time className="text-[11px] text-texto-secundario">{haQuanto(notificacao.criado_em)}</time>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

function haQuanto(iso) {
  const data = new Date(iso)
  if (!iso || Number.isNaN(data.getTime())) return ""
  const minutos = Math.floor((Date.now() - data.getTime()) / 60000)
  if (minutos < 1) return "agora"
  if (minutos < 60) return `há ${minutos} min`
  if (minutos < 1440) return `há ${Math.floor(minutos / 60)} h`
  if (minutos < 2880) return "ontem"
  return data.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" })
}
