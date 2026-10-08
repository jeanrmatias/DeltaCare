import { useState } from "react"
import { useSearchParams } from "react-router"

import { Botao } from "../../componentes/Botao"
import { Carregando, Cartao, EstadoVazio } from "../../componentes/Cartao"
import { AreaDeTexto, Escolha, MensagemDeFormulario, Texto } from "../../componentes/Campos"
import { ChecklistTurmas } from "../../componentes/ChecklistTurmas"
import { AcoesDoModal, Modal } from "../../componentes/Modal"
import { Selo } from "../../componentes/Selo"
import { SeletorDataHora } from "../../componentes/SeletorDataHora"
import { useApi } from "../../hooks/useApi"
import { useDialogo } from "../../hooks/useDialogo"
import { Cabecalho } from "../../layout/Painel"
import { api, ERRO_DE_CONEXAO } from "../../lib/api"
import { baixarArquivo } from "../../lib/arquivos"
import { dataDoCalendario } from "../../lib/datas"
import { dataEHora, STATUS_DO_MATERIAL } from "../../lib/formatos"

/**
 * Atividades do professor: criar, acompanhar e corrigir.
 *
 * Espelha Materiais de propósito — mesmo seletor de disciplina, mesmos três
 * estados (rascunho, agendado, publicado). Quem sabe publicar material não
 * reaprende nada aqui. A diferença: atividade tem prazo e tem entregas, e
 * por isso ganha o painel de correção.
 */
export function AtividadesProfessor() {
  const turmas = useApi("/turmas")
  const lista = turmas.dados?.turmas || []
  // Vindo do calendário (?nova=AAAA-MM-DD&turma=N): o formulário já abre,
  // com o prazo naquele dia, às 23:59, e na disciplina que estava filtrada.
  const [parametros] = useSearchParams()
  const [escolhida, setEscolhida] = useState(() => Number(parametros.get("turma")) || null)
  const turma = escolhida ?? lista[0]?.id ?? null
  const atividades = useApi(turma ? `/atividades?turma_id=${turma}` : null)
  const [formulario, setFormulario] = useState(() => {
    const prazo = dataDoCalendario(parametros.get("nova"), "23:59")
    return prazo ? { prazo } : null
  })
  const [corrigindo, setCorrigindo] = useState(null)
  const { confirmar, avisar } = useDialogo()

  async function excluir(atividade) {
    const sim = await confirmar(`Excluir "${atividade.titulo}"?\n\nAs entregas e as notas dos alunos saem junto. Não há como desfazer.`,
      { titulo: "Excluir atividade", rotulo: "Excluir", perigo: true })
    if (!sim) return
    try {
      const resultado = await (await api(`/atividades/${atividade.id}`, { method: "DELETE" })).json()
      if (!resultado.sucesso) await avisar(resultado.mensagem, "Algo deu errado")
      atividades.recarregar()
    } catch (erro) {
      console.error("Erro ao excluir atividade:", erro)
      await avisar(ERRO_DE_CONEXAO, "Algo deu errado")
    }
  }

  return (
    <>
      <Cabecalho titulo="Atividades" descricao="Quizzes e trabalhos: crie, acompanhe as entregas e corrija.">
        {lista.length > 0 && (
          <select aria-label="Disciplina" value={turma ?? ""} onChange={(e) => setEscolhida(Number(e.target.value))}
            className="rounded-campo border border-borda-campo bg-superficie px-3 py-2.5 text-sm outline-none focus:border-primaria">
            {lista.map((t) => <option key={t.id} value={t.id}>{t.nome} · {t.semestre}</option>)}
          </select>
        )}
        {lista.length > 0 && !formulario && <Botao onClick={() => setFormulario({})}>Nova atividade</Botao>}
      </Cabecalho>

      {turmas.carregando && <Carregando />}
      {turmas.erro && <EstadoVazio>{turmas.erro}</EstadoVazio>}
      {turmas.dados && lista.length === 0 && <EstadoVazio>Você ainda não tem disciplinas. A administração é quem cria e atribui disciplinas.</EstadoVazio>}

      {/* Só depois de as disciplinas chegarem: aberto direto pelo calendário,
          o formulário nasceria antes da lista, sem a disciplina marcada. */}
      {formulario && lista.length > 0 && (
        <FormularioAtividade key={formulario.id ?? "nova"} atividade={formulario.id ? formulario : null} prazoInicial={formulario.prazo}
          turmas={lista} turmaPadrao={turma}
          aoFechar={() => setFormulario(null)} aoSalvar={() => { setFormulario(null); atividades.recarregar() }} />
      )}

      {atividades.carregando && <Carregando />}
      {atividades.dados && atividades.dados.atividades.length === 0 && <EstadoVazio>Nenhuma atividade nesta disciplina ainda.</EstadoVazio>}
      <section className="flex flex-col gap-3">
        {(atividades.dados?.atividades || []).map((atividade) => (
          <LinhaAtividade key={atividade.id} atividade={atividade} aoEditar={() => setFormulario(atividade)}
            aoExcluir={() => excluir(atividade)} aoCorrigir={() => setCorrigindo(atividade)} />
        ))}
      </section>

      {corrigindo && <PainelEntregas atividade={corrigindo} aoFechar={() => { setCorrigindo(null); atividades.recarregar() }} />}
    </>
  )
}

function LinhaAtividade({ atividade, aoEditar, aoExcluir, aoCorrigir }) {
  const status = STATUS_DO_MATERIAL[atividade.status] || { rotulo: atividade.status, tom: "neutro" }
  const detalhes = [
    atividade.tipo === "objetiva" && `${atividade.total_questoes} questão(ões)`,
    `vale ${atividade.pontos}`,
    atividade.prazo && `prazo ${dataEHora(atividade.prazo)}`,
  ].filter(Boolean)

  return (
    <article className="flex flex-col gap-4 rounded-cartao bg-superficie p-5 shadow-cartao md:flex-row md:items-start md:justify-between">
      <div className="min-w-0">
        <div className="mb-1.5 flex flex-wrap gap-2">
          <Selo>{atividade.tipo === "objetiva" ? "Objetiva" : "Dissertativa"}</Selo>
          <Selo tom={status.tom}>{status.rotulo}</Selo>
        </div>
        <h2 className="text-[17px] font-semibold text-navy-900">{atividade.titulo}</h2>
        {(atividade.assunto || atividade.topico) && <p className="mt-1 text-xs font-medium text-primaria">{[atividade.assunto, atividade.topico].filter(Boolean).join(" · ")}</p>}
        <p className="mt-1 text-[14px] text-texto-secundario">{detalhes.join(" · ")}</p>
        {atividade.status === "publicado" && (
          <p className="mt-1.5 text-[14px] text-texto">
            <strong>{atividade.entregues}</strong> de {atividade.total_alunos} entregaram
            {atividade.a_corrigir > 0 && <span className="font-semibold text-perigo"> · {atividade.a_corrigir} a corrigir</span>}
          </p>
        )}
      </div>
      <div className="flex shrink-0 flex-wrap gap-2">
        {atividade.status === "publicado" && <Botao pequeno onClick={aoCorrigir}>Entregas</Botao>}
        <Botao variante="neutra" pequeno onClick={aoEditar}>Editar</Botao>
        <Botao variante="perigo" pequeno onClick={aoExcluir}>Excluir</Botao>
      </div>
    </article>
  )
}

const questaoVazia = () => ({ enunciado: "", alternativas: ["", ""], correta: 0 })
const ANEXOS = [
  { valor: "nenhum", rotulo: "Só texto" },
  { valor: "opcional", rotulo: "Texto, com arquivo opcional" },
  { valor: "obrigatorio", rotulo: "Arquivo obrigatório" },
]

function FormularioAtividade({ atividade, prazoInicial, turmas, turmaPadrao, aoFechar, aoSalvar }) {
  const editando = Boolean(atividade)
  const [campos, setCampos] = useState({
    titulo: atividade?.titulo || "", enunciado: atividade?.enunciado || "", tipo: atividade?.tipo || "objetiva",
    anexo: atividade?.anexo || "nenhum", pontos: String(atividade?.pontos ?? 10), assunto: atividade?.assunto || "",
    topico: atividade?.topico || "", data_liberacao: atividade?.data_liberacao || null, prazo: atividade?.prazo || prazoInicial || null,
  })
  const [marcadas, setMarcadas] = useState(turmaPadrao ? [turmaPadrao] : [])
  const [questoes, setQuestoes] = useState([questaoVazia()])
  const [mensagem, setMensagem] = useState("")
  const [enviando, setEnviando] = useState(false)
  const mudar = (nome) => (valor) => setCampos((atual) => ({ ...atual, [nome]: valor }))
  const objetiva = campos.tipo === "objetiva"

  async function salvar(rascunho) {
    if (!campos.titulo.trim()) return setMensagem("Informe o título da atividade.")
    const corpo = {
      titulo: campos.titulo.trim(), enunciado: campos.enunciado.trim(), assunto: campos.assunto.trim(), topico: campos.topico.trim(),
      pontos: Number(campos.pontos) || 10, rascunho, data_liberacao: campos.data_liberacao, prazo: campos.prazo,
    }
    if (!editando) {
      if (!marcadas.length) return setMensagem("Escolha pelo menos uma disciplina.")
      Object.assign(corpo, { turma_ids: marcadas, tipo: campos.tipo, anexo: objetiva ? "nenhum" : campos.anexo })
      if (objetiva) {
        corpo.questoes = questoes.map((q) => ({
          enunciado: q.enunciado.trim(), alternativas: q.alternativas.map((a) => a.trim()).filter(Boolean), correta: q.correta,
        }))
      }
    }
    setEnviando(true)
    try {
      const resposta = editando
        ? await api(`/atividades/${atividade.id}`, { method: "PUT", body: JSON.stringify(corpo) })
        : await api("/atividades", { method: "POST", body: JSON.stringify(corpo) })
      const resultado = await resposta.json()
      if (!resultado.sucesso) return setMensagem(resultado.mensagem || resultado.detail || "Não foi possível salvar.")
      aoSalvar()
    } catch (erro) {
      console.error("Erro ao salvar atividade:", erro)
      setMensagem(ERRO_DE_CONEXAO)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <Cartao titulo={editando ? "Editar atividade" : "Nova atividade"} className="mb-5">
      <form onSubmit={(e) => { e.preventDefault(); salvar(e.nativeEvent.submitter?.value === "rascunho") }} className="flex flex-col gap-4">
        <Texto rotulo="Título" valor={campos.titulo} aoMudar={mudar("titulo")} obrigatorio placeholder="ex.: Quiz — Arritmias" />
        {!editando && <ChecklistTurmas turmas={turmas} marcadas={marcadas} aoMudar={setMarcadas} acao="criada" />}
        <AreaDeTexto rotulo="Enunciado (opcional)" valor={campos.enunciado} aoMudar={mudar("enunciado")} linhas={3} />

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {editando
            ? <p className="text-sm text-texto-secundario">Tipo: <strong className="text-texto">{objetiva ? "Objetiva" : "Dissertativa"}</strong></p>
            : <Escolha rotulo="Tipo" valor={campos.tipo} aoMudar={mudar("tipo")} opcoes={[{ valor: "objetiva", rotulo: "Objetiva (quiz)" }, { valor: "dissertativa", rotulo: "Dissertativa" }]} />}
          {!objetiva && !editando && <Escolha rotulo="Entrega" valor={campos.anexo} aoMudar={mudar("anexo")} opcoes={ANEXOS} />}
          <Texto rotulo="Vale (pontos)" tipo="number" valor={campos.pontos} aoMudar={mudar("pontos")} />
          <Texto rotulo="Assunto" valor={campos.assunto} aoMudar={mudar("assunto")} />
          <Texto rotulo="Tópico" valor={campos.topico} aoMudar={mudar("topico")} />
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <SeletorDataHora rotulo="Liberar em (opcional)" valor={campos.data_liberacao} aoMudar={mudar("data_liberacao")} dica="Em branco: libera ao publicar." />
          <SeletorDataHora rotulo="Prazo de entrega (opcional)" valor={campos.prazo} aoMudar={mudar("prazo")} dica="Depois dele a entrega continua possível, marcada como atrasada." />
        </div>

        {/* As questões só existem na criação: editar questão com entrega já feita
            mudaria a nota de quem respondeu à pergunta antiga. */}
        {objetiva && !editando && <EditorDeQuestoes questoes={questoes} aoMudar={setQuestoes} />}

        <div className="flex flex-wrap gap-2.5">
          <Botao tipo="submit" desativado={enviando}>Publicar</Botao>
          <button type="submit" value="rascunho" disabled={enviando}
            className="rounded-campo border border-borda bg-superficie px-4 py-3 text-sm font-semibold text-texto hover:bg-fundo">Salvar rascunho</button>
          <Botao variante="neutra" onClick={aoFechar}>Cancelar</Botao>
        </div>
        <MensagemDeFormulario texto={mensagem} />
      </form>
    </Cartao>
  )
}

/** O montador do quiz: enunciado, alternativas e qual é a correta. */
function EditorDeQuestoes({ questoes, aoMudar }) {
  const mudarQuestao = (indice, mudanca) => aoMudar(questoes.map((q, i) => (i === indice ? { ...q, ...mudanca } : q)))

  return (
    <fieldset className="flex flex-col gap-3">
      <legend className="mb-1.5 text-[14px] font-medium text-texto">Questões — marque a alternativa correta de cada uma</legend>
      {questoes.map((questao, indice) => (
        <div key={indice} className="rounded-bloco border border-borda p-4">
          <div className="mb-2 flex items-center justify-between">
            <strong className="text-sm text-navy-900">Questão {indice + 1}</strong>
            {questoes.length > 1 && (
              <button type="button" onClick={() => aoMudar(questoes.filter((_, i) => i !== indice))} className="text-xs font-semibold text-perigo hover:underline">Remover</button>
            )}
          </div>
          <input value={questao.enunciado} onChange={(e) => mudarQuestao(indice, { enunciado: e.target.value })} placeholder="Enunciado da questão"
            aria-label={`Enunciado da questão ${indice + 1}`} className="mb-2.5 w-full rounded-campo border border-borda-campo px-3 py-2 text-sm outline-none focus:border-primaria" />
          <div className="flex flex-col gap-2">
            {questao.alternativas.map((alternativa, posicao) => (
              <div key={posicao} className="flex items-center gap-2">
                <input type="radio" name={`correta-${indice}`} checked={questao.correta === posicao} onChange={() => mudarQuestao(indice, { correta: posicao })}
                  aria-label={`Alternativa ${posicao + 1} é a correta`} className="size-4 accent-primaria" />
                <input value={alternativa} placeholder={`Alternativa ${posicao + 1}`} aria-label={`Alternativa ${posicao + 1}`}
                  onChange={(e) => mudarQuestao(indice, { alternativas: questao.alternativas.map((a, p) => (p === posicao ? e.target.value : a)) })}
                  className="min-w-0 flex-1 rounded-campo border border-borda-campo px-3 py-2 text-sm outline-none focus:border-primaria" />
                {questao.alternativas.length > 2 && (
                  <button type="button" aria-label={`Remover alternativa ${posicao + 1}`}
                    onClick={() => {
                      const alternativas = questao.alternativas.filter((_, p) => p !== posicao)
                      mudarQuestao(indice, { alternativas, correta: questao.correta >= alternativas.length ? 0 : questao.correta })
                    }}
                    className="px-2 text-lg text-perigo">×</button>
                )}
              </div>
            ))}
          </div>
          <button type="button" onClick={() => mudarQuestao(indice, { alternativas: [...questao.alternativas, ""] })}
            className="mt-2 text-xs font-semibold text-primaria hover:underline">+ Alternativa</button>
        </div>
      ))}
      <div><Botao variante="neutra" pequeno onClick={() => aoMudar([...questoes, questaoVazia()])}>+ Questão</Botao></div>
    </fieldset>
  )
}

/** Quem entregou, quem não, e a correção de cada um. */
function PainelEntregas({ atividade, aoFechar }) {
  const { dados, carregando, erro, recarregar } = useApi(`/atividades/${atividade.id}/entregas`)
  const [corrigindo, setCorrigindo] = useState(null)

  return (
    <>
      <Modal aberto={!corrigindo} aoFechar={aoFechar} largura="max-w-[760px]" rotulo={`Entregas · ${atividade.titulo}`}>
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-navy-900">{atividade.titulo}</h2>
            <p className="text-xs text-texto-secundario">{[atividade.turma_nome, `vale ${atividade.pontos}`, atividade.prazo && `prazo ${dataEHora(atividade.prazo)}`].filter(Boolean).join(" · ")}</p>
          </div>
          <Botao variante="neutra" pequeno onClick={aoFechar}>Fechar</Botao>
        </div>
        {carregando && <Carregando />}
        {erro && <p className="text-sm text-texto-secundario">{erro}</p>}
        <div className="flex max-h-[65vh] flex-col gap-3 overflow-y-auto">
          {(dados?.entregas || []).map((entrega) => (
            <LinhaEntrega key={entrega.aluno_id} entrega={entrega} questoes={dados.questoes || []} aoCorrigir={() => setCorrigindo(entrega)} />
          ))}
        </div>
      </Modal>
      {corrigindo && (
        <ModalCorrecao entrega={corrigindo} pontos={atividade.pontos} aoFechar={() => setCorrigindo(null)}
          aoSalvar={() => { setCorrigindo(null); recarregar() }} />
      )}
    </>
  )
}

function LinhaEntrega({ entrega, questoes, aoCorrigir }) {
  const { avisar } = useDialogo()
  const temNota = entrega.nota !== null && entrega.nota !== undefined
  const situacao = !entrega.entregue ? { rotulo: "Não entregou", tom: "neutro" }
    : temNota ? { rotulo: `Nota ${entrega.nota}`, tom: "sucesso" } : { rotulo: "A corrigir", tom: "alerta" }

  // Download autenticado: o link direto do front antigo ia sem o token (401).
  async function baixarAnexo() {
    try {
      await baixarArquivo(`/entregas/${entrega.entrega_id}/arquivo`, entrega.arquivo_nome)
    } catch (erro) {
      console.error("Erro ao baixar anexo:", erro)
      await avisar("Não foi possível baixar o anexo.", "Algo deu errado")
    }
  }

  return (
    <article className="flex flex-col gap-3 rounded-bloco border border-borda p-4 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0">
        <strong className="text-sm text-navy-900">{entrega.aluno_nome}</strong>
        <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-texto-secundario">
          <Selo tom={situacao.tom}>{situacao.rotulo}</Selo>
          {entrega.enviado_em && <span>{dataEHora(entrega.enviado_em)}</span>}
          {entrega.atrasada && <span className="font-semibold text-perigo">entregue com atraso</span>}
        </div>
        {entrega.entregue && typeof entrega.respostas === "string" && entrega.respostas && (
          <p className="mt-2 rounded-campo bg-fundo px-3 py-2 text-[14px] whitespace-pre-wrap text-texto">{entrega.respostas}</p>
        )}
        {entrega.entregue && Array.isArray(entrega.respostas) && <GabaritoDoAluno questoes={questoes} escolhas={entrega.respostas} />}
        {entrega.arquivo_nome && (
          <button type="button" onClick={baixarAnexo} className="mt-2 text-[14px] font-semibold text-primaria hover:underline">Anexo: {entrega.arquivo_nome}</button>
        )}
        {entrega.devolutiva && <p className="mt-2 text-[14px] text-texto-secundario italic">Devolutiva: {entrega.devolutiva}</p>}
      </div>
      {entrega.entregue && <Botao pequeno variante={temNota ? "neutra" : "primaria"} onClick={aoCorrigir} className="shrink-0">{temNota ? "Rever nota" : "Corrigir"}</Botao>}
    </article>
  )
}

/**
 * O que o aluno marcou em cada questão, com acerto e erro. A nota da
 * objetiva sai sozinha, mas o professor precisa ver **onde** a turma errou —
 * é isso que diz qual tópico retomar em aula.
 */
function GabaritoDoAluno({ questoes, escolhas }) {
  if (!questoes.length) return null
  return (
    <ul className="mt-2 flex flex-col gap-1.5">
      {questoes.map((questao, indice) => {
        const marcada = escolhas[indice]
        const respondeu = marcada !== null && marcada !== undefined
        const acertou = respondeu && marcada === questao.correta
        return (
          <li key={indice} className={`flex gap-2 rounded-campo px-3 py-1.5 text-[14px] ${acertou ? "bg-sucesso-fundo" : "bg-perigo-fundo"}`}>
            <span aria-hidden="true" className={acertou ? "text-sucesso" : "text-perigo"}>{acertou ? "✓" : "✗"}</span>
            <span>
              <strong>{indice + 1}.</strong> {questao.enunciado}
              <span className="block text-texto-secundario">marcou: {respondeu ? questao.alternativas[marcada] ?? "—" : "não respondeu"}</span>
              {!acertou && <span className="block font-semibold text-sucesso">correta: {questao.alternativas[questao.correta]}</span>}
            </span>
          </li>
        )
      })}
    </ul>
  )
}

function ModalCorrecao({ entrega, pontos, aoFechar, aoSalvar }) {
  const [nota, setNota] = useState(entrega.nota == null ? "" : String(entrega.nota))
  const [devolutiva, setDevolutiva] = useState(entrega.devolutiva ?? "")
  const [mensagem, setMensagem] = useState("")

  async function salvar(evento) {
    evento.preventDefault()
    try {
      const resultado = await (await api(`/entregas/${entrega.entrega_id}/correcao`, {
        method: "POST", body: JSON.stringify({ nota: Number(nota), devolutiva }),
      })).json()
      if (!resultado.sucesso) return setMensagem(resultado.mensagem)
      aoSalvar()
    } catch (erro) {
      console.error("Erro ao corrigir:", erro)
      setMensagem(ERRO_DE_CONEXAO)
    }
  }

  return (
    <Modal aberto aoFechar={aoFechar} titulo={`Corrigir — ${entrega.aluno_nome}`}>
      <p className="mb-4 text-sm text-texto-secundario">O aluno recebe a nota e a devolutiva, e é avisado pelo sino.</p>
      <form onSubmit={salvar} className="flex flex-col gap-4">
        <Texto rotulo={`Nota (0 a ${pontos})`} tipo="number" valor={nota} aoMudar={setNota} obrigatorio />
        <AreaDeTexto rotulo="Devolutiva para o aluno" valor={devolutiva} aoMudar={setDevolutiva} linhas={4} />
        <MensagemDeFormulario texto={mensagem} />
        <AcoesDoModal>
          <Botao variante="neutra" onClick={aoFechar}>Cancelar</Botao>
          <Botao tipo="submit">Salvar correção</Botao>
        </AcoesDoModal>
      </form>
    </Modal>
  )
}
