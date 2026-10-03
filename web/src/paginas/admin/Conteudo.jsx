import { useState } from "react"

import { Botao } from "../../componentes/Botao"
import { Carregando, EstadoVazio } from "../../componentes/Cartao"
import { Modal } from "../../componentes/Modal"
import { Selo } from "../../componentes/Selo"
import { useApi } from "../../hooks/useApi"
import { useDialogo } from "../../hooks/useDialogo"
import { Cabecalho } from "../../layout/Painel"
import { baixarArquivo } from "../../lib/arquivos"
import { dataCurta, ROTULOS_TIPO_MATERIAL } from "../../lib/formatos"
import { normalizar } from "../../lib/texto"

/**
 * Supervisão de conteúdo: o que as turmas recebem — material e atividades
 * publicados ou agendados, de qualquer disciplina.
 *
 * Rascunho, entrega, anotação e conversa não aparecem, e não por filtro
 * desta tela: o servidor não tem rota que os entregue à administração
 * (regras/conteudo.py). Só leitura: tirar material do ar é decisão de
 * política ainda não tomada; o caminho para tratar é a tela de Denúncias.
 */
export function Conteudo() {
  const [semestre, setSemestre] = useState("")
  const [busca, setBusca] = useState("")
  const [vendo, setVendo] = useState(null)
  const { dados, carregando, erro } = useApi(`/admin/conteudo${semestre ? `?semestre=${encodeURIComponent(semestre)}` : ""}`)

  // Uma disciplina aparece se ela casar com a busca, ou se algum material ou
  // atividade dela casar — e aí só com o que casou.
  const termo = normalizar(busca.trim())
  const disciplinas = (dados?.disciplinas || []).map((d) => {
    if (!termo || normalizar(`${d.nome} ${d.professor_nome} ${d.professor_email}`).includes(termo)) return d
    return { ...d, materiais: d.materiais.filter((m) => normalizar(m.titulo).includes(termo)), atividades: d.atividades.filter((a) => normalizar(a.titulo).includes(termo)) }
  }).filter((d) => !termo || d.materiais.length || d.atividades.length)

  return (
    <>
      <Cabecalho titulo="Conteúdo"
        descricao="O que as turmas recebem: material e atividades publicados ou agendados. Rascunhos, entregas e anotações não aparecem aqui." />

      <section className="mb-5 flex flex-col gap-3 rounded-cartao bg-superficie p-4 shadow-cartao sm:flex-row">
        <label className="flex flex-col gap-1.5 text-[13px] text-texto-secundario">
          Semestre
          <select value={dados?.semestre ?? semestre} onChange={(e) => setSemestre(e.target.value)}
            className="rounded-campo border border-borda-campo px-3 py-2 text-sm text-texto outline-none focus:border-primaria">
            {(dados?.semestres || []).map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </label>
        <label className="flex flex-1 flex-col gap-1.5 text-[13px] text-texto-secundario">
          Buscar disciplina, professor ou título
          <input type="search" value={busca} onChange={(e) => setBusca(e.target.value)} autoComplete="off"
            className="rounded-campo border border-borda-campo px-3 py-2 text-sm text-texto outline-none focus:border-primaria" />
        </label>
      </section>

      {carregando && <Carregando />}
      {erro && <EstadoVazio>{erro}</EstadoVazio>}
      {dados?.sucesso && !disciplinas.length && <EstadoVazio>{termo ? "Nada com esse termo neste semestre." : `Nenhuma disciplina em ${dados.semestre}.`}</EstadoVazio>}

      <div className="flex flex-col gap-3">
        {disciplinas.map((disciplina) => {
          const denuncias = disciplina.materiais.reduce((soma, m) => soma + m.denuncias_abertas, 0)
          return (
            <details key={disciplina.id} open={Boolean(termo)} className="group rounded-cartao bg-superficie shadow-cartao">
              <summary className="flex cursor-pointer list-none flex-wrap items-baseline gap-x-3 gap-y-1 p-5">
                <span className="text-texto-secundario transition group-open:rotate-90" aria-hidden="true">›</span>
                <strong className="text-navy-900">{disciplina.nome}</strong>
                <span className="text-[13px] text-texto-secundario">
                  Prof. {disciplina.professor_nome} · {disciplina.total_alunos} aluno(s) · {disciplina.materiais.length} material(is) · {disciplina.atividades.length} atividade(s)
                  {denuncias > 0 && <span className="font-semibold text-perigo"> · {denuncias} denúncia(s) aberta(s)</span>}
                </span>
              </summary>
              <div className="flex flex-col gap-2.5 px-5 pb-5">
                {!disciplina.materiais.length && !disciplina.atividades.length && <p className="text-sm text-texto-secundario">Nada publicado ou agendado nesta disciplina.</p>}
                {disciplina.materiais.map((m) => <ItemMaterial key={`m${m.id}`} material={m} />)}
                {disciplina.atividades.map((a) => (
                  <Item key={`a${a.id}`}
                    selos={<><Selo>{a.tipo === "objetiva" ? "Objetiva" : "Dissertativa"}</Selo><Selo tom={a.status === "agendado" ? "alerta" : "sucesso"}>{a.status === "agendado" ? "Agendado" : "Publicado"}</Selo></>}
                    titulo={a.titulo}
                    detalhe={`${a.pontos} pontos${a.prazo ? ` · prazo ${dataCurta(a.prazo)}` : ""} · ${a.entregues} de ${disciplina.total_alunos} entregaram`}
                    acao={<Botao variante="neutra" pequeno onClick={() => setVendo(a.id)}>{a.tipo === "objetiva" ? "Ver questões" : "Ver enunciado"}</Botao>} />
                ))}
              </div>
            </details>
          )
        })}
      </div>

      {vendo && <AtividadeSupervisionada id={vendo} aoFechar={() => setVendo(null)} />}
    </>
  )
}

function Item({ selos, titulo, detalhe, acao }) {
  return (
    <article className="flex flex-col gap-3 rounded-bloco border border-borda p-4 md:flex-row md:items-start md:justify-between">
      <div className="min-w-0">
        <div className="mb-1.5 flex flex-wrap gap-2">{selos}</div>
        <h3 className="font-bold text-navy-900">{titulo}</h3>
        {detalhe && <p className="mt-1 text-xs font-medium text-primaria">{detalhe}</p>}
      </div>
      <div className="shrink-0">{acao}</div>
    </article>
  )
}

function ItemMaterial({ material }) {
  const { avisar } = useDialogo()

  // Rota própria da administração, autenticada como todo o sistema.
  async function baixar() {
    try {
      await baixarArquivo(`/admin/conteudo/materiais/${material.id}/arquivo`, material.arquivo_nome)
    } catch (erro) {
      console.error("Erro ao baixar material:", erro)
      await avisar("Não foi possível baixar este material.", "Algo deu errado")
    }
  }

  return (
    <Item
      selos={<>
        <Selo>{ROTULOS_TIPO_MATERIAL[material.tipo] || material.tipo}</Selo>
        <Selo tom={material.status === "agendado" ? "alerta" : "sucesso"}>{material.status === "agendado" ? `Agendado · ${dataCurta(material.data_liberacao)}` : "Publicado"}</Selo>
        {material.denuncias_abertas > 0 && <Selo tom="perigo">{material.denuncias_abertas} denúncia(s) aberta(s)</Selo>}
      </>}
      titulo={material.titulo}
      detalhe={material.classificacao}
      acao={material.tipo === "link" && material.link_url
        ? <a href={material.link_url} target="_blank" rel="noopener noreferrer" className="rounded-campo border border-borda px-3.5 py-2 text-[13px] font-semibold hover:bg-fundo">Abrir link</a>
        : material.arquivo_nome && <Botao variante="neutra" pequeno onClick={baixar}>Baixar</Botao>}
    />
  )
}

/** A atividade como os alunos recebem — com o gabarito, que a supervisão precisa ver. */
function AtividadeSupervisionada({ id, aoFechar }) {
  const { dados, carregando, erro } = useApi(`/admin/conteudo/atividades/${id}`)

  return (
    <Modal aberto aoFechar={aoFechar} largura="max-w-[680px]" rotulo={dados?.atividade?.titulo || "Atividade"}>
      {carregando && <Carregando />}
      {erro && <p className="text-sm text-texto-secundario">{erro}</p>}
      {dados?.sucesso && (
        <>
          <h2 className="mb-3 text-lg font-bold text-navy-900">{dados.atividade.titulo} · {dados.atividade.turma_nome}</h2>
          {dados.atividade.enunciado && <p className="mb-4 text-sm whitespace-pre-wrap text-texto">{dados.atividade.enunciado}</p>}
          <ol className="flex max-h-[60vh] list-decimal flex-col gap-3 overflow-y-auto pl-5">
            {dados.questoes.map((questao, i) => (
              <li key={i} className="text-sm text-texto">
                <p className="font-semibold">{questao.enunciado}</p>
                <ul className="mt-1 flex flex-col gap-0.5">
                  {questao.alternativas.map((alternativa, j) => (
                    <li key={j} className={j === questao.correta ? "font-semibold text-sucesso" : "text-texto-secundario"}>
                      {alternativa}{j === questao.correta && " ✓ gabarito"}
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ol>
        </>
      )}
      <div className="mt-5 flex justify-end"><Botao variante="neutra" onClick={aoFechar}>Fechar</Botao></div>
    </Modal>
  )
}
