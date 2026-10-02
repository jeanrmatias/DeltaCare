import { useState } from "react"

import { Botao } from "../../componentes/Botao"
import { Carregando, EstadoVazio, Numero, Numeros } from "../../componentes/Cartao"
import { MensagemDeFormulario } from "../../componentes/Campos"
import { Modal } from "../../componentes/Modal"
import { Selo } from "../../componentes/Selo"
import { SeletorDisciplina } from "../../componentes/SeletorDisciplina"
import { useApi } from "../../hooks/useApi"
import { useDialogo } from "../../hooks/useDialogo"
import { Cabecalho } from "../../layout/Painel"
import { api, ERRO_DE_CONEXAO } from "../../lib/api"
import { baixarArquivo } from "../../lib/arquivos"
import { dataEHora } from "../../lib/formatos"

/**
 * Atividades na visão do aluno: resolver, entregar e ver a nota.
 *
 * - **O progresso é salvo, não perdido.** Dá para fechar no meio de um quiz e
 *   voltar depois: o que foi marcado fica no servidor como entrega não enviada.
 * - **O prazo avisa, não impede.** Passado o prazo, a entrega continua
 *   possível e consta como atrasada. Quem decide o que fazer é o professor.
 */
export function Atividades() {
  const [turma, setTurma] = useState(null)
  const turmas = useApi("/aluno/turmas")
  const lista = useApi(turma ? `/aluno/atividades?turma_id=${turma}` : "/aluno/atividades")
  const [aberta, setAberta] = useState(null)

  const atividades = lista.dados?.atividades || []
  const contar = (...situacoes) => atividades.filter((a) => situacoes.includes(a.situacao)).length

  return (
    <>
      <Cabecalho titulo="Atividades" descricao="Quizzes e trabalhos das suas disciplinas.">
        {(turmas.dados?.turmas || []).length > 0 && (
          <SeletorDisciplina turmas={turmas.dados.turmas} valor={turma} aoMudar={setTurma} comTodas />
        )}
      </Cabecalho>

      {atividades.length > 0 && (
        <Numeros>
          <Numero rotulo="A fazer" valor={contar("pendente", "em andamento")} />
          <Numero rotulo="Entregues" valor={contar("entregue")} />
          <Numero rotulo="Corrigidas" valor={contar("corrigida")} destaque />
        </Numeros>
      )}

      {lista.carregando && <Carregando />}
      {lista.erro && <EstadoVazio>{lista.erro}</EstadoVazio>}
      {lista.dados && atividades.length === 0 && <EstadoVazio>Nenhuma atividade liberada até agora.</EstadoVazio>}

      <section className="flex flex-col gap-3">
        {atividades.map((atividade) => (
          <LinhaAtividade key={atividade.id} atividade={atividade} aoAbrir={() => setAberta(atividade)} />
        ))}
      </section>

      {aberta && (
        <Resolver
          atividade={aberta}
          aoFechar={() => setAberta(null)}
          aoEntregar={() => { setAberta(null); lista.recarregar() }}
        />
      )}
    </>
  )
}

const SITUACOES = {
  pendente: { rotulo: "A fazer", tom: "neutro", acao: "Começar" },
  "em andamento": { rotulo: "Em andamento", tom: "alerta", acao: "Continuar" },
  entregue: { rotulo: "Entregue", tom: "alerta", acao: "Ver" },
  corrigida: { rotulo: "Corrigida", tom: "sucesso", acao: "Ver" },
}

const venceu = (iso) => Boolean(iso) && new Date(iso) < new Date()
const temNota = (nota) => nota !== null && nota !== undefined

function LinhaAtividade({ atividade, aoAbrir }) {
  const situacao = SITUACOES[atividade.situacao] || SITUACOES.pendente
  const entregue = atividade.situacao === "entregue" || atividade.situacao === "corrigida"
  const detalhes = [atividade.tipo === "objetiva" && `${atividade.total_questoes} questão(ões)`, `vale ${atividade.pontos}`].filter(Boolean)

  let prazo = null
  if (atividade.atrasada) prazo = <p className="mt-1.5 text-[13px] font-semibold text-perigo">Entregue com atraso</p>
  else if (atividade.prazo && venceu(atividade.prazo) && !entregue)
    prazo = <p className="mt-1.5 text-[13px] font-semibold text-perigo">Prazo venceu em {dataEHora(atividade.prazo)} — ainda dá para entregar, constará como atrasada</p>
  else if (atividade.prazo) prazo = <p className="mt-1.5 text-[13px] text-texto-secundario">Prazo: {dataEHora(atividade.prazo)}</p>

  return (
    <article className="flex flex-col gap-4 rounded-cartao bg-superficie p-5 shadow-cartao md:flex-row md:items-start md:justify-between">
      <div className="min-w-0">
        <div className="mb-1.5 flex flex-wrap items-center gap-2">
          <Selo>{atividade.tipo === "objetiva" ? "Objetiva" : "Dissertativa"}</Selo>
          <Selo tom={situacao.tom}>{situacao.rotulo}</Selo>
        </div>
        <h3 className="text-base font-bold text-navy-900">{atividade.titulo}</h3>
        <p className="mt-1 text-xs font-medium text-primaria">{[atividade.turma_nome, atividade.assunto, atividade.topico].filter(Boolean).join(" · ")}</p>
        <p className="mt-1 text-[13px] text-texto-secundario">{detalhes.join(" · ")}</p>
        {prazo}
        {temNota(atividade.nota) && <p className="mt-1.5 text-sm text-texto"><strong className="text-sucesso">Nota {atividade.nota}</strong> de {atividade.pontos}</p>}
        {atividade.devolutiva && <Devolutiva texto={atividade.devolutiva} />}
      </div>
      <Botao onClick={aoAbrir} className="shrink-0 py-2 text-[13px]">{situacao.acao}</Botao>
    </article>
  )
}

function Devolutiva({ texto }) {
  return <p className="mt-2 rounded-campo bg-fundo px-3 py-2 text-[13px] leading-relaxed whitespace-pre-wrap text-texto">{texto}</p>
}

const LIMITE_ANEXO = 15 * 1024 * 1024
const ACEITOS = ".pdf,.doc,.docx,.odt,.txt,.rtf,.png,.jpg,.jpeg,.webp,.xlsx,.csv,.ppt,.pptx,.odp"

/** O painel de resolver: questões ou resposta escrita, anexo e as duas ações. */
function Resolver({ atividade, aoFechar, aoEntregar }) {
  const { dados, carregando, erro } = useApi(`/aluno/atividades/${atividade.id}`)
  const subtitulo = [atividade.turma_nome, `vale ${atividade.pontos}`, atividade.prazo && `prazo ${dataEHora(atividade.prazo)}`].filter(Boolean).join(" · ")

  return (
    <Modal aberto aoFechar={aoFechar} largura="max-w-[720px]">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-navy-900">{atividade.titulo}</h2>
          <p className="text-xs text-texto-secundario">{subtitulo}</p>
        </div>
        <Botao variante="neutra" onClick={aoFechar} className="py-2">Fechar</Botao>
      </div>
      {carregando && <Carregando />}
      {erro && <p className="text-sm text-texto-secundario">{erro}</p>}
      {/* key: o formulário nasce com as respostas salvas desta atividade. */}
      {dados?.sucesso && <FormularioDeEntrega key={atividade.id} dados={dados} aoEntregar={aoEntregar} />}
    </Modal>
  )
}

function FormularioDeEntrega({ dados, aoEntregar }) {
  const { atividade, questoes, entrega } = dados
  const objetiva = atividade.tipo === "objetiva"
  const entregue = Boolean(entrega.enviado_em)
  const anexo = atividade.anexo || "nenhum"

  const [respostas, setRespostas] = useState(() =>
    objetiva
      ? Array.isArray(entrega.respostas) ? [...entrega.respostas] : new Array(questoes.length).fill(null)
      : typeof entrega.respostas === "string" ? entrega.respostas : "",
  )
  const [arquivo, setArquivo] = useState(null)
  const [mensagem, setMensagem] = useState(() =>
    !entregue && venceu(atividade.prazo) ? { texto: "O prazo já venceu. A entrega será registrada como atrasada.", sucesso: false } : { texto: "" },
  )
  const [enviando, setEnviando] = useState(false)
  const { confirmar, avisar } = useDialogo()

  function escolherArquivo(evento) {
    const escolhido = evento.target.files?.[0]
    setArquivo(null)
    if (!escolhido) return
    // O limite vem escrito na tela, e é conferido antes do envio: descobrir
    // os 15MB depois de esperar o upload de um vídeo é frustração evitável.
    if (escolhido.size > LIMITE_ANEXO) {
      evento.target.value = ""
      return setMensagem({ texto: `"${escolhido.name}" passa de 15MB. Escolha um arquivo menor.` })
    }
    const leitor = new FileReader()
    leitor.onload = () => {
      setArquivo({ nome: escolhido.name, base64: leitor.result })
      setMensagem({ texto: `Anexo pronto: ${escolhido.name}`, sucesso: true })
    }
    leitor.onerror = () => setMensagem({ texto: "Não foi possível ler o arquivo. Tente escolher de novo." })
    leitor.readAsDataURL(escolhido)
  }

  async function enviar(definitivo) {
    if (definitivo) {
      if (anexo === "obrigatorio" && !arquivo) {
        return setMensagem({ texto: "Esta atividade exige um arquivo. Escolha o arquivo antes de entregar." })
      }
      const faltando = objetiva
        ? respostas.filter((r) => r === null || r === undefined).length
        : String(respostas).trim() || anexo === "obrigatorio" ? 0 : 1
      const pergunta = faltando > 0
        ? `Você deixou ${faltando} ${objetiva ? "questão(ões) sem responder" : "a resposta em branco"}. Entregar assim mesmo?`
        : "Depois de entregar não dá para alterar. Confirmar?"
      if (!(await confirmar(pergunta, { titulo: "Entregar atividade", rotulo: "Entregar" }))) return
    }

    const corpo = { respostas }
    if (definitivo && arquivo) Object.assign(corpo, { arquivo_base64: arquivo.base64, arquivo_nome: arquivo.nome })

    setEnviando(true)
    try {
      // Duas rotas: entregar é definitivo; salvar progresso guarda e deixa voltar.
      const resposta = definitivo
        ? await api(`/aluno/atividades/${atividade.id}/entrega`, { method: "POST", body: JSON.stringify(corpo) })
        : await api(`/aluno/atividades/${atividade.id}/progresso`, { method: "POST", body: JSON.stringify(corpo) })
      const resultado = await resposta.json()
      if (!resultado.sucesso) return setMensagem({ texto: resultado.mensagem || "Não foi possível enviar." })
      if (!definitivo) return setMensagem({ texto: resultado.mensagem, sucesso: true })
      aoEntregar()
      await avisar(resultado.mensagem, "Atividade entregue")
    } catch (falha) {
      console.error("Erro ao enviar:", falha)
      setMensagem({ texto: ERRO_DE_CONEXAO })
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {atividade.enunciado && <p className="text-sm leading-relaxed whitespace-pre-wrap text-texto">{atividade.enunciado}</p>}

      {objetiva ? (
        questoes.map((questao, indice) => (
          <fieldset key={indice} className="rounded-bloco border border-borda p-4" disabled={entregue}>
            <legend className="px-1 text-sm text-texto"><strong>{indice + 1}.</strong> {questao.enunciado}</legend>
            <div className="mt-2 flex flex-col gap-2">
              {questao.alternativas.map((alternativa, posicao) => (
                <label key={posicao} className="flex cursor-pointer items-start gap-2.5 rounded-campo px-2 py-1.5 text-sm hover:bg-fundo">
                  <input
                    type="radio"
                    name={`questao-${indice}`}
                    checked={respostas[indice] === posicao}
                    onChange={() => setRespostas((atual) => atual.map((r, i) => (i === indice ? posicao : r)))}
                    className="mt-0.5 accent-primaria"
                  />
                  <span>{alternativa}</span>
                </label>
              ))}
            </div>
          </fieldset>
        ))
      ) : (
        <textarea
          value={respostas}
          onChange={(evento) => setRespostas(evento.target.value)}
          disabled={entregue}
          rows={8}
          aria-label="Sua resposta"
          placeholder="Escreva sua resposta"
          className="w-full resize-y rounded-campo border border-borda px-3 py-2.5 text-sm outline-none focus:border-primaria disabled:bg-fundo"
        />
      )}

      {!entregue && anexo !== "nenhum" && (
        <label className="flex flex-col gap-1.5 text-[13px] font-medium text-texto">
          Arquivo da entrega ({anexo === "obrigatorio" ? "obrigatório" : "opcional"})
          <input type="file" accept={ACEITOS} onChange={escolherArquivo} className="text-sm font-normal" />
          <span className="text-xs font-normal text-texto-secundario">Até 15MB. PDF, documento, imagem, planilha ou apresentação.</span>
        </label>
      )}

      {entregue ? <Resultado atividade={atividade} entrega={entrega} /> : (
        <div className="flex flex-col-reverse gap-2.5 sm:flex-row sm:justify-end">
          <Botao variante="neutra" onClick={() => enviar(false)} desativado={enviando}>Salvar e continuar depois</Botao>
          <Botao onClick={() => enviar(true)} desativado={enviando}>Entregar</Botao>
        </div>
      )}
      <MensagemDeFormulario texto={mensagem.texto} sucesso={mensagem.sucesso} />
    </div>
  )
}

function Resultado({ atividade, entrega }) {
  const { avisar } = useDialogo()

  // Download autenticado. O front antigo usava um link direto, que não leva
  // o token: o aluno recebia 401 ao tentar rever o próprio anexo.
  async function baixarAnexo() {
    try {
      await baixarArquivo(`/entregas/${entrega.entrega_id}/arquivo`, entrega.arquivo_nome)
    } catch (erro) {
      console.error("Erro ao baixar anexo:", erro)
      await avisar("Não foi possível baixar o anexo.", "Algo deu errado")
    }
  }

  return (
    <div className="rounded-bloco bg-fundo p-4 text-sm text-texto">
      <p>
        <strong>Entregue</strong> em {dataEHora(entrega.enviado_em)}
        {entrega.atrasada && <span className="font-semibold text-perigo"> · com atraso</span>}
      </p>
      {temNota(entrega.nota)
        ? <p className="mt-1.5"><strong className="text-sucesso">Nota {entrega.nota}</strong> de {atividade.pontos}</p>
        : <p className="mt-1.5 text-texto-secundario">Aguardando correção do professor.</p>}
      {entrega.devolutiva && <Devolutiva texto={entrega.devolutiva} />}
      {entrega.arquivo_nome && entrega.entrega_id && (
        <button type="button" onClick={baixarAnexo} className="mt-2 text-[13px] font-semibold text-primaria hover:underline">
          Anexo enviado: {entrega.arquivo_nome}
        </button>
      )}
    </div>
  )
}
