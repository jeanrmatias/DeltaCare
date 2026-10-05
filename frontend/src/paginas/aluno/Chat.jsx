import { useEffect, useRef, useState } from "react"
import { useNavigate } from "react-router"

import { Botao } from "../../componentes/Botao"
import { Carregando, EstadoVazio } from "../../componentes/Cartao"
import { Markdown } from "../../componentes/Markdown"
import { SeletorDisciplina } from "../../componentes/SeletorDisciplina"
import { useApi } from "../../hooks/useApi"
import { useDialogo } from "../../hooks/useDialogo"
import { Cabecalho } from "../../layout/Painel"
import { api, ERRO_DE_CONEXAO } from "../../lib/api"

/**
 * Chat de estudos. O assistente só responde com base no material liberado —
 * de uma disciplina escolhida ou, no modo automático (o padrão), de todas as
 * do aluno, e aí ele mesmo descobre de qual era a pergunta. Isso é garantido
 * no backend (chat_ia.py), não aqui.
 */
export function Chat() {
  const { dados, carregando, erro } = useApi("/aluno/turmas")
  const turmas = dados?.turmas || []
  // null é o modo automático: o aluno não precisa saber de qual disciplina é
  // a dúvida para perguntar.
  const [escolhida, setEscolhida] = useState(null)
  // Trocar de disciplina remonta a conversa (e o seletor, que mora nela): o
  // foco volta para ele, e quem navega pelo teclado não perde o lugar.
  const [trocou, setTrocou] = useState(false)
  function escolher(id) {
    setTrocou(true)
    setEscolhida(id)
  }

  const turma = turmas.find((t) => t.id === escolhida) ?? null

  return (
    <div className="flex min-h-[70vh] flex-col md:h-[calc(100dvh-2.5rem)]">
      <Cabecalho
        titulo="Chat de estudos"
        descricao="Tire dúvidas sobre o material que o professor disponibilizou — o assistente só responde com base nele."
      />

      {carregando && <Carregando />}
      {erro && <EstadoVazio>{erro}</EstadoVazio>}
      {dados && turmas.length === 0 && (
        <EstadoVazio>Você ainda não está matriculado em nenhuma disciplina. Fale com a administração.</EstadoVazio>
      )}

      {/* key: trocar de disciplina monta uma conversa nova do zero — o estado
          da anterior (mensagens, resposta em andamento) não vaza para esta. */}
      {turmas.length > 0 && (
        <Conversa key={turma?.id ?? "automatico"} turma={turma} turmas={turmas} aoMudar={escolher} focarSeletor={trocou} />
      )}
    </div>
  )
}

const BOAS_VINDAS =
  "Oi! Pode perguntar qualquer coisa sobre o material liberado nessa disciplina que eu ajudo — só não saio do que o professor disponibilizou."
const BOAS_VINDAS_AUTOMATICO =
  "Oi! Pergunte sobre qualquer disciplina sua: eu procuro no material de todas e digo de qual veio a resposta — só não saio do que os professores disponibilizaram."

function Conversa({ turma, turmas, aoMudar, focarSeletor }) {
  // Sem disciplina (turma null), a conversa do modo automático.
  const consulta = turma ? `?turma_id=${turma.id}` : ""
  const historico = useApi(`/chat/historico${consulta}`)
  const [novas, setNovas] = useState([])
  const [pergunta, setPergunta] = useState("")
  const [gerando, setGerando] = useState(false)
  // O que vem depois de uma resposta que o material não cobriu por inteiro:
  // a oferta de levar a dúvida ao professor.
  const [depois, setDepois] = useState(null)
  const cancelamento = useRef(null)
  const rolagem = useRef(null)
  const { confirmar, avisar } = useDialogo()

  const mensagens = [...(historico.dados?.mensagens || []), ...novas]

  // Desce até a última mensagem sempre que chega uma nova. useRef guarda o
  // elemento da lista sem fazer a tela renderizar de novo.
  useEffect(() => {
    rolagem.current?.scrollTo({ top: rolagem.current.scrollHeight })
  }, [mensagens.length, gerando, depois])

  const adicionar = (papel, conteudo, fontes = [], lacuna = "", disciplina = null) =>
    setNovas((atual) => [...atual, { papel, conteudo, fontes, lacuna, disciplina }])

  function perguntar(evento) {
    evento.preventDefault()
    enviar(pergunta.trim())
  }

  async function enviar(texto) {
    if (!texto || gerando) return

    adicionar("user", texto)
    setPergunta("")
    setDepois(null)
    setGerando(true)
    cancelamento.current = new AbortController()

    try {
      const resposta = await api("/chat/perguntar", {
        method: "POST",
        body: JSON.stringify({ turma_id: turma?.id ?? null, pergunta: texto }),
        signal: cancelamento.current.signal,
      })
      const dados = await resposta.json()

      if (dados.sucesso) {
        adicionar("assistant", dados.resposta, dados.fontes, dados.lacuna, dados.disciplina)
        // Coberta só em parte ou nada: o material tem uma lacuna, e quem pode
        // preenchê-la é o professor. Sem o campo (resposta antiga), vale a
        // regra de antes: sem fonte citada, não cobriu.
        const cobertura = dados.cobertura ?? (dados.fontes?.length ? "completa" : "nenhuma")
        if (cobertura !== "completa") setDepois({ pergunta: texto })
      } else {
        adicionar("assistant", dados.mensagem || "Não foi possível responder agora.")
      }
    } catch (erro) {
      // Cancelar não é erro: o navegador lança AbortError igual a uma falha de rede.
      if (erro.name === "AbortError") adicionar("assistant", "_Resposta interrompida._")
      else {
        console.error("Erro ao perguntar:", erro)
        adicionar("assistant", ERRO_DE_CONEXAO)
      }
    } finally {
      cancelamento.current = null
      setGerando(false)
    }
  }

  // Some o texto de verdade (regras/chat_ia.apagar_historico). O que fica é dito
  // aqui, antes de apagar, e não descoberto depois.
  async function apagar() {
    const sim = await confirmar(
      `Apagar a conversa ${turma ? `de ${turma.nome}` : "do modo automático"}? Não dá para desfazer.\n\n` +
      "Somem as suas perguntas e as respostas do assistente. O seu XP não muda, e o assunto das dúvidas " +
      "que o material não respondeu continua contando para o professor, sem o seu nome.",
      { titulo: "Apagar conversa", rotulo: "Apagar", perigo: true },
    )
    if (!sim) return
    try {
      const dados = await (await api(`/chat/historico${consulta}`, { method: "DELETE" })).json()
      if (!dados.sucesso) return await avisar(dados.mensagem || "Não foi possível apagar a conversa.", "Algo deu errado")
      setNovas([])
      setDepois(null)
      historico.recarregar()
    } catch (erro) {
      console.error("Erro ao apagar a conversa:", erro)
      await avisar(ERRO_DE_CONEXAO, "Algo deu errado")
    }
  }

  return (
    <section className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-cartao bg-superficie shadow-cartao">
      {/* role="log": o leitor de tela anuncia a resposta nova quando ela chega,
          sem o aluno ter que ir procurá-la na lista. */}
      <div ref={rolagem} role="log" aria-label={`Conversa sobre ${turma?.nome ?? "todas as suas disciplinas"}`}
        className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-5">
        {historico.carregando && <Carregando />}
        {historico.dados && mensagens.length === 0 && (
          <Bolha papel="assistant" conteudo={turma ? BOAS_VINDAS : BOAS_VINDAS_AUTOMATICO} />
        )}
        {mensagens.map((mensagem, indice) => <Bolha key={indice} {...mensagem} />)}
        {gerando && <Pensando automatico={!turma} />}
        {depois && <OfertaProfessor pergunta={depois.pergunta} />}
      </div>

      <form onSubmit={perguntar} className="border-t border-borda p-4">
        {/* A disciplina se escolhe aqui, junto da pergunta, e não no topo da
            página. O padrão é procurar em todas: escolher uma é para quem quer
            restringir — e perguntar de insuficiência cardíaca em Anatomia sem
            perceber dava "não cobre" para algo que a plataforma tem. */}
        <div className="mb-2 flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
          <label className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs font-medium text-texto-secundario">
            Perguntando sobre o material de
            <SeletorDisciplina turmas={turmas} valor={turma?.id} aoMudar={aoMudar} rotulo={null} autoFocus={focarSeletor}
              comTodas rotuloTodas="todas as minhas disciplinas (automático)" />
          </label>
          {mensagens.length > 0 && (
            <button type="button" onClick={apagar} disabled={gerando}
              className="rounded-campo py-1 text-xs font-medium text-texto-secundario underline-offset-2 hover:text-perigo hover:underline disabled:opacity-50">
              Apagar conversa
            </button>
          )}
        </div>
        {/* Transparência: o aluno sabe o que o professor vê, antes de perguntar. */}
        <p className="mb-3 text-xs text-texto-secundario">
          {turma
            ? "Quando o material não responde, o professor vê o assunto da dúvida — nunca a pergunta nem o seu nome."
            : "Quando o material responde só em parte, o professor da disciplina vê o assunto da dúvida — nunca a pergunta nem o seu nome."}
        </p>
        <div className="flex gap-2.5">
        <input
          value={pergunta}
          onChange={(evento) => setPergunta(evento.target.value)}
          placeholder={turma ? `Sua pergunta sobre ${turma.nome}...` : "Sua pergunta, de qualquer disciplina..."}
          aria-label="Sua pergunta"
          autoComplete="off"
          disabled={gerando}
          required
          className="min-w-0 flex-1 rounded-campo border border-borda-campo px-3.5 py-3 text-sm outline-none focus:border-primaria disabled:bg-fundo"
        />
        {gerando ? (
          <Botao variante="neutra" onClick={() => cancelamento.current?.abort()}>Parar</Botao>
        ) : (
          <Botao tipo="submit">Enviar</Botao>
        )}
        </div>
      </form>
    </section>
  )
}

const SOBRESCRITOS = ["¹", "²", "³", "⁴", "⁵", "⁶", "⁷", "⁸", "⁹"]

/**
 * Uma fala da conversa, num balão. A do assistente traz as fontes como nota de
 * rodapé de livro, numeradas: é o que diz que a resposta veio do material, e
 * não da cabeça do modelo. No modo automático, no topo, a disciplina de onde
 * a resposta saiu.
 */
function Bolha({ papel, conteudo, fontes, lacuna, disciplina }) {
  if (papel === "user") {
    return (
      <div className="max-w-[75%] self-end rounded-bloco rounded-br-sm bg-primaria px-4 py-2.5 text-sm leading-normal whitespace-pre-wrap text-white">
        {conteudo}
      </div>
    )
  }

  // Balão como o do aluno, espelhado: a ponta do lado de quem fala. Sem ele, a
  // resposta (que era só um fio na margem) parecia texto solto na página.
  return (
    <div className="max-w-[85%] self-start rounded-bloco rounded-bl-sm border border-borda bg-fundo px-4 py-3 text-[15px] leading-relaxed text-texto">
      {disciplina && (
        <p className="mb-1 text-xs font-semibold tracking-wide text-primaria uppercase">
          <span className="sr-only">Resposta do material de </span>{disciplina}
        </p>
      )}
      {/* A resposta da IA vem em Markdown. */}
      <Markdown texto={conteudo} />
      {/* O que a pergunta pedia e o material não traz, como anotação na
          margem: separado da resposta, para o aluno não confundir "o material
          diz isto" com "isto é tudo". */}
      {lacuna && (
        <aside className="mt-3 border-l-2 border-alerta bg-alerta-fundo/70 py-2 pr-3 pl-3 text-[15px] leading-snug">
          <span className="block font-titulo text-[13px] font-semibold text-[#92400E] italic">O material não traz</span>
          {lacuna}
        </aside>
      )}
      {fontes?.length > 0 && (
        <footer className="mt-3 text-[13px] leading-snug text-texto-secundario">
          <span aria-hidden="true" className="mb-1.5 block w-10 border-t border-borda-campo" />
          {fontes.map((fonte, indice) => (
            <p key={fonte}>
              <span aria-hidden="true" className="mr-1 font-titulo">{SOBRESCRITOS[indice] ?? `${indice + 1}.`}</span>
              <span className="sr-only">Fonte: </span>
              {fonte}
            </p>
          ))}
        </footer>
      )}
    </div>
  )
}

/**
 * "Pensando", com cronômetro. O modelo roda local e leva de 10 a 20 segundos:
 * sem sinal de progresso, parece travado, e o aluno manda a pergunta de novo.
 */
function Pensando({ automatico = false }) {
  const [segundos, setSegundos] = useState(0)

  useEffect(() => {
    const inicio = Date.now()
    const relogio = setInterval(() => setSegundos(Math.floor((Date.now() - inicio) / 1000)), 1000)
    // A limpeza roda quando o componente sai da tela (a resposta chegou).
    return () => clearInterval(relogio)
  }, [])

  return (
    <div className="flex items-center gap-2.5 self-start rounded-bloco bg-fundo px-4 py-3 text-[14px] text-texto-secundario" role="status">
      <span className="inline-flex gap-1" aria-hidden="true">
        {[0, 1, 2].map((i) => (
          <span key={i} className="size-1.5 animate-pulse rounded-full bg-marca motion-reduce:animate-none" style={{ animationDelay: `${i * 0.2}s` }} />
        ))}
      </span>
      {automatico ? "Procurando no material das suas disciplinas" : "Consultando o material da disciplina"}
      {/* aria-hidden: dentro de um role="status", o cronômetro seria lido em
          voz alta a cada segundo. */}
      {segundos >= 3 && <span aria-hidden="true" className="tabular-nums opacity-60">{segundos}s</span>}
    </div>
  )
}

/**
 * Quando o material não cobriu a pergunta, oferece levá-la a um professor.
 *
 * O "se" não é enfeite: a plataforma não sabe se a pergunta é da matéria.
 * Afirmar "pergunte ao professor" seria conselho sem sentido metade das
 * vezes; com a condicional, quem decide é quem perguntou. Não é uma bolha:
 * não é o assistente falando, é a plataforma oferecendo um caminho.
 *
 * Também não diz *qual* professor. A pergunta feita em Anatomia pode ser de
 * outra matéria, e o palpite da plataforma já mandou uma de crânio para
 * Cardiologia no teste piloto. Quem sabe de quem é a dúvida é o aluno: a
 * pergunta vai pronta para Mensagens, e lá ele escolhe a conversa.
 */
function OfertaProfessor({ pergunta }) {
  const navegar = useNavigate()

  function levar() {
    try {
      // A pergunta vai junto para não ser redigitada. sessionStorage, e não
      // a URL: pode ser longa e não tem por que ficar no histórico.
      sessionStorage.setItem("deltacare_rascunho_mensagem", JSON.stringify({ texto: pergunta }))
    } catch {
      /* sem sessionStorage a conversa abre igual, só sem o texto pronto */
    }
    navegar("/aluno/mensagens")
  }

  return (
    <div className="flex max-w-[70%] flex-col items-start gap-2.5 self-start rounded-bloco border border-dashed border-borda px-3.5 py-3">
      <p className="text-[14px] leading-normal text-texto-secundario">
        Se for uma dúvida da matéria, você pode levá-la ao professor da disciplina.
      </p>
      <Botao variante="neutra" onClick={levar} className="py-2 text-[14px]">Perguntar a um professor</Botao>
    </div>
  )
}
