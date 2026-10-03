import { useEffect, useRef, useState } from "react"
import { useNavigate } from "react-router"

import { Botao } from "../../componentes/Botao"
import { Carregando, EstadoVazio } from "../../componentes/Cartao"
import { Markdown } from "../../componentes/Markdown"
import { SeletorDisciplina } from "../../componentes/SeletorDisciplina"
import { useApi } from "../../hooks/useApi"
import { Cabecalho } from "../../layout/Painel"
import { api, ERRO_DE_CONEXAO } from "../../lib/api"

/**
 * Chat de estudos. O assistente só responde com base no material liberado
 * na disciplina escolhida — isso é garantido no backend (chat_ia.py), não
 * aqui.
 */
export function Chat() {
  const { dados, carregando, erro } = useApi("/aluno/turmas")
  const turmas = dados?.turmas || []
  const [escolhida, setEscolhida] = useState(null)

  // Sem escolha ainda, a primeira (o servidor manda as do semestre antes).
  const turma = turmas.find((t) => t.id === escolhida) ?? turmas[0]

  return (
    <div className="flex min-h-[70vh] flex-col md:h-[calc(100dvh-2.5rem)]">
      <Cabecalho
        titulo="Chat de estudos"
        descricao="Tire dúvidas sobre o material que o professor disponibilizou — o assistente só responde com base nele."
      >
        {turmas.length > 0 && <SeletorDisciplina turmas={turmas} valor={turma?.id} aoMudar={setEscolhida} />}
      </Cabecalho>

      {carregando && <Carregando />}
      {erro && <EstadoVazio>{erro}</EstadoVazio>}
      {dados && turmas.length === 0 && (
        <EstadoVazio>Você ainda não está matriculado em nenhuma disciplina. Fale com a administração.</EstadoVazio>
      )}

      {/* key: trocar de disciplina monta uma conversa nova do zero — o estado
          da anterior (mensagens, resposta em andamento) não vaza para esta. */}
      {turma && (
        <Conversa key={turma.id} turma={turma} />
      )}
    </div>
  )
}

const BOAS_VINDAS =
  "Oi! Pode perguntar qualquer coisa sobre o material liberado nessa disciplina que eu ajudo — só não saio do que o professor disponibilizou."

function Conversa({ turma }) {
  const historico = useApi(`/chat/historico?turma_id=${turma.id}`)
  const [novas, setNovas] = useState([])
  const [pergunta, setPergunta] = useState("")
  const [gerando, setGerando] = useState(false)
  // O que vem depois de uma resposta que o material não cobriu por inteiro:
  // a oferta de levar a dúvida ao professor.
  const [depois, setDepois] = useState(null)
  const cancelamento = useRef(null)
  const rolagem = useRef(null)

  const mensagens = [...(historico.dados?.mensagens || []), ...novas]

  // Desce até a última mensagem sempre que chega uma nova. useRef guarda o
  // elemento da lista sem fazer a tela renderizar de novo.
  useEffect(() => {
    rolagem.current?.scrollTo({ top: rolagem.current.scrollHeight })
  }, [mensagens.length, gerando, depois])

  const adicionar = (papel, conteudo, fontes = [], lacuna = "") => setNovas((atual) => [...atual, { papel, conteudo, fontes, lacuna }])

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
        body: JSON.stringify({ turma_id: turma.id, pergunta: texto }),
        signal: cancelamento.current.signal,
      })
      const dados = await resposta.json()

      if (dados.sucesso) {
        adicionar("assistant", dados.resposta, dados.fontes, dados.lacuna)
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

  return (
    <section className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-cartao bg-superficie shadow-cartao">
      {/* role="log": o leitor de tela anuncia a resposta nova quando ela chega,
          sem o aluno ter que ir procurá-la na lista. */}
      <div ref={rolagem} role="log" aria-label={`Conversa sobre ${turma.nome}`}
        className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-5">
        {historico.carregando && <Carregando />}
        {historico.dados && mensagens.length === 0 && <Bolha papel="assistant" conteudo={BOAS_VINDAS} />}
        {mensagens.map((mensagem, indice) => <Bolha key={indice} {...mensagem} />)}
        {gerando && <Pensando />}
        {depois && <OfertaProfessor pergunta={depois.pergunta} />}
      </div>

      <form onSubmit={perguntar} className="border-t border-borda p-4">
        {/* Em qual disciplina se está perguntando, à vista: o assistente só lê
            o material dela, e perguntar do Cardiolex em Anatomia sem perceber
            dá "não cobre" para algo que a plataforma tem. */}
        <p className="mb-2 text-xs text-texto-secundario">
          Perguntando sobre o material de <strong className="text-texto">{turma.nome}</strong>.{" "}
          {/* Transparência: o aluno sabe o que o professor vê, antes de perguntar. */}
          Quando o material não responde, o professor vê o assunto da dúvida — nunca a pergunta nem o seu nome.
        </p>
        <div className="flex gap-2.5">
        <input
          value={pergunta}
          onChange={(evento) => setPergunta(evento.target.value)}
          placeholder={`Sua pergunta sobre ${turma.nome}...`}
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

function Bolha({ papel, conteudo, fontes, lacuna }) {
  const doAluno = papel === "user"

  return (
    <div
      className={`rounded-bloco px-4 py-3 text-sm leading-normal ${
        doAluno ? "max-w-[70%] self-end bg-primaria whitespace-pre-wrap text-white" : "max-w-[82%] self-start bg-fundo text-texto"
      }`}
    >
      {/* A pergunta do aluno é texto puro; a resposta da IA vem em Markdown. */}
      {doAluno ? conteudo : <Markdown texto={conteudo} />}
      {/* O que a pergunta pedia e o material não traz. Fica separado do texto
          da resposta, sempre igual, para o aluno não confundir "o material
          diz isto" com "isto é tudo". */}
      {lacuna && (
        <div className="mt-2.5 rounded-campo border-l-3 border-alerta bg-alerta-fundo px-3 py-2 text-[13px]">
          <strong>O material não traz:</strong> {lacuna}
        </div>
      )}
      {fontes?.length > 0 && <div className="mt-2 text-[11px] font-semibold opacity-70">Fonte(s): {fontes.join(", ")}</div>}
    </div>
  )
}

/**
 * "Pensando", com cronômetro. O modelo roda local e leva de 10 a 20 segundos:
 * sem sinal de progresso, parece travado, e o aluno manda a pergunta de novo.
 */
function Pensando() {
  const [segundos, setSegundos] = useState(0)

  useEffect(() => {
    const inicio = Date.now()
    const relogio = setInterval(() => setSegundos(Math.floor((Date.now() - inicio) / 1000)), 1000)
    // A limpeza roda quando o componente sai da tela (a resposta chegou).
    return () => clearInterval(relogio)
  }, [])

  return (
    <div className="flex items-center gap-2.5 self-start rounded-bloco bg-fundo px-4 py-3 text-[13px] text-texto-secundario" role="status">
      <span className="inline-flex gap-1" aria-hidden="true">
        {[0, 1, 2].map((i) => (
          <span key={i} className="size-1.5 animate-pulse rounded-full bg-primaria motion-reduce:animate-none" style={{ animationDelay: `${i * 0.2}s` }} />
        ))}
      </span>
      Consultando o material da disciplina
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
      <p className="text-[13px] leading-normal text-texto-secundario">
        Se for uma dúvida da matéria, você pode levá-la ao professor da disciplina.
      </p>
      <Botao variante="neutra" onClick={levar} className="py-2 text-[13px]">Perguntar a um professor</Botao>
    </div>
  )
}
