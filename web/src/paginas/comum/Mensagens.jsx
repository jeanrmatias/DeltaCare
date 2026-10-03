import { useEffect, useRef, useState } from "react"

import { Botao } from "../../componentes/Botao"
import { Carregando, EstadoVazio } from "../../componentes/Cartao"
import { MensagemDeFormulario } from "../../componentes/Campos"
import { useApi } from "../../hooks/useApi"
import { useSessao } from "../../hooks/useSessao"
import { Cabecalho } from "../../layout/Painel"
import { api, ERRO_DE_CONEXAO } from "../../lib/api"
import { avisarNotificacoes } from "../../lib/eventos"
import { iniciaisDe } from "../../lib/usuario"

/**
 * Conversa entre professor e aluno. Um componente para os dois perfis: a tela
 * é a mesma, e o servidor já devolve a lista certa conforme quem está logado.
 * Duas telas seriam dois lugares para consertar o mesmo bug.
 *
 * É o canal do que o assistente de IA recusa: o que o material não cobre
 * tem para onde ir.
 */
export function Mensagens() {
  const { usuario } = useSessao()
  const professor = usuario.tipo === "professor"
  const { dados, carregando, erro, recarregar } = useApi("/mensagens/conversas")
  const conversas = dados?.conversas || []
  const [ativa, setAtiva] = useState(null)
  const [rascunho, setRascunho] = useState(lerRascunho)

  // Abre sozinha a primeira — mas não quando há não lidas, para o professor
  // escolher por onde começar, nem quando chega uma pergunta do chat: de quem
  // é a dúvida, quem sabe é o aluno (ver OfertaProfessor, no Chat).
  const inicial = !rascunho && !dados?.nao_lidas ? conversas[0] : null
  const aberta = conversas.find((c) => mesma(c, ativa)) ?? (ativa ? null : inicial)

  return (
    <>
      <Cabecalho titulo="Mensagens" descricao={professor ? "Conversas com os alunos das suas disciplinas." : "Converse com os professores das suas disciplinas."} />

      {carregando && <Carregando />}
      {erro && <EstadoVazio>{erro}</EstadoVazio>}
      {dados && conversas.length === 0 && (
        <EstadoVazio>{professor ? "Nenhum aluno matriculado nas suas disciplinas ainda." : "Você ainda não está matriculado em nenhuma disciplina."}</EstadoVazio>
      )}

      {conversas.length > 0 && (
        <div className="grid gap-5 md:grid-cols-[320px_1fr]">
          <nav aria-label="Conversas" className="flex max-h-[70vh] flex-col overflow-y-auto rounded-cartao bg-superficie p-2 shadow-cartao">
            {conversas.map((conversa) => (
              <ItemConversa key={chave(conversa)} conversa={conversa} ativa={mesma(conversa, aberta)} aoAbrir={() => setAtiva(conversa)} />
            ))}
          </nav>

          {aberta ? (
            <Conversa
              key={chave(aberta)}
              conversa={aberta}
              professor={professor}
              textoInicial={rascunho?.texto ?? ""}
              aoMudar={recarregar}
              aoEnviar={() => setRascunho(null)}
            />
          ) : (
            <EstadoVazio>
              {rascunho ? "Escolha com qual professor falar. A sua pergunta do chat vai junto." : "Escolha uma conversa."}
            </EstadoVazio>
          )}
        </div>
      )}
    </>
  )
}

const chave = (conversa) => `${conversa.turma_id}:${conversa.contraparte_email}`
const mesma = (a, b) => Boolean(a && b) && chave(a) === chave(b)

/**
 * A pergunta que o chat de estudos mandou para cá, quando o material não a
 * cobriu: redigitar seria atrito puro. Consumida de uma vez — voltar a esta
 * tela depois é para ver a resposta, não para reabrir o mesmo rascunho.
 */
function lerRascunho() {
  try {
    const bruto = sessionStorage.getItem("deltacare_rascunho_mensagem")
    sessionStorage.removeItem("deltacare_rascunho_mensagem")
    const rascunho = bruto ? JSON.parse(bruto) : null
    return rascunho?.texto ? rascunho : null
  } catch {
    return null
  }
}

/** Hora se for hoje; senão, a data (e a hora, na conversa aberta). */
function quando(iso, comHora = false) {
  const data = new Date(iso)
  if (!iso || Number.isNaN(data.getTime())) return ""
  if (data.toDateString() === new Date().toDateString()) return data.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })
  return comHora
    ? data.toLocaleString("pt-BR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })
    : data.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" })
}

function ItemConversa({ conversa, ativa, aoAbrir }) {
  const previa = conversa.ultima_mensagem ? `${conversa.ultima_minha ? "Você: " : ""}${conversa.ultima_mensagem}` : "Nenhuma mensagem ainda"

  return (
    <button type="button" onClick={aoAbrir} aria-current={ativa || undefined}
      className={`flex w-full items-start gap-2.5 rounded-bloco p-2.5 text-left transition ${ativa ? "bg-fundo" : "hover:bg-fundo"}`}>
      <span className="flex size-[34px] shrink-0 items-center justify-center rounded-full bg-primaria text-[13px] font-bold text-white">{iniciaisDe(conversa.titulo)}</span>
      <span className="flex min-w-0 flex-1 flex-col">
        <strong className="truncate text-sm text-texto">{conversa.titulo}</strong>
        <span className="truncate text-xs text-texto-secundario">{conversa.subtitulo}</span>
        <span className="truncate text-xs text-texto-secundario">{previa}</span>
      </span>
      <span className="flex shrink-0 flex-col items-end gap-1">
        <span className="text-[11px] text-texto-secundario">{quando(conversa.ultima_em)}</span>
        {conversa.nao_lidas > 0 && (
          <span className="inline-flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-perigo px-[5px] text-[11px] font-bold text-white">{conversa.nao_lidas}</span>
        )}
      </span>
    </button>
  )
}

function Conversa({ conversa, professor, textoInicial, aoMudar, aoEnviar }) {
  const caminho = `/mensagens?turma_id=${conversa.turma_id}${professor ? `&aluno_email=${encodeURIComponent(conversa.contraparte_email)}` : ""}`
  const { dados, carregando, erro, recarregar } = useApi(caminho)
  const [texto, setTexto] = useState(textoInicial)
  const [mensagem, setMensagem] = useState("")
  const [enviando, setEnviando] = useState(false)
  const caixa = useRef(null)
  const mensagens = dados?.mensagens || []

  // Abrir marca como lida no servidor: a lista e o sino precisam saber.
  useEffect(() => {
    if (!dados?.sucesso) return
    if (conversa.nao_lidas) aoMudar()
    avisarNotificacoes()
    // Só quando chega a conversa; aoMudar e nao_lidas mudam por causa disto.
  }, [dados]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    caixa.current?.scrollTo({ top: caixa.current.scrollHeight })
  }, [mensagens.length])

  async function enviar(evento) {
    evento?.preventDefault()
    const conteudo = texto.trim()
    if (!conteudo || enviando) return

    setEnviando(true)
    try {
      const corpo = { turma_id: conversa.turma_id, conteudo, ...(professor && { aluno_email: conversa.contraparte_email }) }
      const resultado = await (await api("/mensagens", { method: "POST", body: JSON.stringify(corpo) })).json()
      if (!resultado.sucesso) return setMensagem(resultado.mensagem)
      setTexto("")
      setMensagem("")
      recarregar()
      aoMudar()
      aoEnviar?.()
    } catch (falha) {
      console.error("Erro ao enviar mensagem:", falha)
      setMensagem(ERRO_DE_CONEXAO)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <section className="flex min-h-[60vh] flex-col overflow-hidden rounded-cartao bg-superficie shadow-cartao md:h-[70vh]">
      <header className="border-b border-borda px-5 py-3.5">
        <h2 className="text-[15px] font-bold text-navy-900">{conversa.titulo}</h2>
        <p className="text-xs text-texto-secundario">{conversa.subtitulo}</p>
      </header>

      <div ref={caixa} role="log" aria-label="Mensagens da conversa" className="flex min-h-0 flex-1 flex-col gap-2.5 overflow-y-auto p-5">
        {carregando && <Carregando />}
        {erro && <p className="text-sm text-texto-secundario">{erro}</p>}
        {dados?.sucesso && mensagens.length === 0 && <p className="m-auto text-sm text-texto-secundario">Nenhuma mensagem ainda. Escreva a primeira.</p>}
        {mensagens.map((m, indice) => (
          <div key={m.id ?? indice}
            className={`max-w-[75%] rounded-bloco px-3.5 py-2.5 text-sm ${m.minha ? "self-end bg-primaria text-white" : "self-start bg-fundo text-texto"}`}>
            <p className="whitespace-pre-wrap [overflow-wrap:anywhere]">{m.conteudo}</p>
            <span className="mt-1 block text-right text-[11px] opacity-70">{quando(m.criado_em, true)}</span>
          </div>
        ))}
      </div>

      <form onSubmit={enviar} className="border-t border-borda p-4">
        <div className="flex gap-2.5">
          <textarea
            value={texto}
            onChange={(evento) => setTexto(evento.target.value)}
            onKeyDown={(evento) => {
              // Enter envia; Shift+Enter quebra a linha.
              if (evento.key === "Enter" && !evento.shiftKey) {
                evento.preventDefault()
                enviar()
              }
            }}
            rows={2}
            autoFocus={Boolean(textoInicial)}
            aria-label="Mensagem"
            placeholder="Escreva sua mensagem"
            className="min-w-0 flex-1 resize-none rounded-campo border border-borda-campo px-3 py-2.5 text-sm outline-none focus:border-primaria"
          />
          <Botao tipo="submit" desativado={enviando}>Enviar</Botao>
        </div>
        <MensagemDeFormulario texto={mensagem} />
      </form>
    </section>
  )
}
