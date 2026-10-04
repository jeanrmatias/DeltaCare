import { useState } from "react"
import { useSearchParams } from "react-router"

import { Botao } from "../../componentes/Botao"
import { Carregando, Cartao, EstadoVazio } from "../../componentes/Cartao"
import { AreaDeTexto, Escolha, MensagemDeFormulario, Texto } from "../../componentes/Campos"
import { ChecklistTurmas } from "../../componentes/ChecklistTurmas"
import { ModalReportar } from "../../componentes/Reportar"
import { Selo } from "../../componentes/Selo"
import { SeletorDataHora } from "../../componentes/SeletorDataHora"
import { Visualizador } from "../../componentes/Visualizador"
import { useApi } from "../../hooks/useApi"
import { useDialogo } from "../../hooks/useDialogo"
import { Cabecalho } from "../../layout/Painel"
import { api, ERRO_DE_CONEXAO } from "../../lib/api"
import { baixarArquivo, podeVisualizar } from "../../lib/arquivos"
import { ROTULOS_TIPO_MATERIAL, STATUS_DO_MATERIAL } from "../../lib/formatos"

/**
 * Materiais do professor: publicar, salvar rascunho, agendar a liberação,
 * editar e excluir. PDF publicado é indexado pelo servidor para o assistente
 * de estudos responder a partir dele.
 */
export function MateriaisProfessor() {
  const [parametros, setParametros] = useSearchParams()
  const turmas = useApi("/turmas")
  const lista = turmas.dados?.turmas || []
  const turmaDaUrl = Number(parametros.get("turma")) || null
  const turma = lista.some((t) => t.id === turmaDaUrl) ? turmaDaUrl : lista[0]?.id ?? null

  const materiais = useApi(turma ? `/materiais?turma_id=${turma}` : null)
  const [formulario, setFormulario] = useState(null) // null: fechado; {}: novo; material: editar
  const [janela, setJanela] = useState(null)
  const { confirmar, avisar } = useDialogo()

  async function excluir(material) {
    const sim = await confirmar(`Excluir "${material.titulo}"?\nO arquivo e os trechos indexados para o assistente saem junto. Não há como desfazer.`,
      { titulo: "Excluir material", rotulo: "Excluir", perigo: true })
    if (!sim) return
    try {
      const resultado = await (await api(`/materiais/${material.id}`, { method: "DELETE" })).json()
      if (!resultado.sucesso) await avisar(resultado.mensagem, "Algo deu errado")
      materiais.recarregar()
    } catch (erro) {
      console.error("Erro ao excluir material:", erro)
      await avisar(ERRO_DE_CONEXAO, "Algo deu errado")
    }
  }

  async function indexar(material) {
    try {
      const resultado = await (await api(`/materiais/${material.id}/indexar`, { method: "POST" })).json()
      await avisar(resultado.mensagem, resultado.sucesso ? "Material no chat" : "Não deu para indexar")
      materiais.recarregar()
    } catch (erro) {
      console.error("Erro ao indexar material:", erro)
      await avisar(ERRO_DE_CONEXAO, "Algo deu errado")
    }
  }

  return (
    <>
      <Cabecalho titulo="Materiais" descricao="Publique e organize PDFs, vídeos, documentos e links para suas disciplinas.">
        {lista.length > 0 && (
          <select aria-label="Disciplina" value={turma ?? ""} onChange={(e) => setParametros({ turma: e.target.value })}
            className="rounded-campo border border-borda-campo bg-superficie px-3 py-2.5 text-sm outline-none focus:border-primaria">
            {lista.map((t) => <option key={t.id} value={t.id}>{t.nome} · {t.semestre}</option>)}
          </select>
        )}
        {lista.length > 0 && !formulario && <Botao onClick={() => setFormulario({})}>Novo material</Botao>}
      </Cabecalho>

      {turmas.carregando && <Carregando />}
      {turmas.erro && <EstadoVazio>{turmas.erro}</EstadoVazio>}
      {turmas.dados && lista.length === 0 && (
        <EstadoVazio>Você ainda não tem disciplinas. A administração é quem cria e atribui disciplinas.</EstadoVazio>
      )}

      {formulario && (
        <FormularioMaterial key={formulario.id ?? "novo"} material={formulario.id ? formulario : null} turmas={lista} turmaPadrao={turma}
          aoFechar={() => setFormulario(null)}
          aoSalvar={async (aviso) => {
            setFormulario(null); materiais.recarregar(); turmas.recarregar()
            // Publicado, mas fora do chat (assistente fora do ar, PDF escaneado):
            // calar isto deixaria o aluno perguntando sem resposta.
            if (aviso) await avisar(aviso, "Material fora do chat")
          }} />
      )}

      {materiais.carregando && <Carregando />}
      {materiais.dados && materiais.dados.materiais.length === 0 && (
        <EstadoVazio>Nenhum material nesta disciplina ainda. Clique em "Novo material" para publicar o primeiro.</EstadoVazio>
      )}
      <section className="flex flex-col gap-3">
        {(materiais.dados?.materiais || []).map((material) => (
          <LinhaMaterial key={material.id} material={material} aoEditar={() => setFormulario(material)} aoExcluir={() => excluir(material)}
            aoIndexar={() => indexar(material)}
            aoVer={() => setJanela({ tipo: "ver", material })} aoReportar={() => setJanela({ tipo: "reportar", material })} />
        ))}
      </section>

      {janela?.tipo === "ver" && <Visualizador material={janela.material} caminho={`/materiais/${janela.material.id}/arquivo`} aoFechar={() => setJanela(null)} />}
      {janela?.tipo === "reportar" && <ModalReportar material={janela.material} aoFechar={() => setJanela(null)} />}
    </>
  )
}

function LinhaMaterial({ material, aoEditar, aoExcluir, aoVer, aoReportar, aoIndexar }) {
  const { avisar } = useDialogo()
  const status = STATUS_DO_MATERIAL[material.status] || { rotulo: material.status, tom: "neutro" }
  const classificacao = [material.assunto, material.topico, material.aula, material.semestre].filter(Boolean).join(" · ")
  const agendadoPara = material.status === "agendado" && material.data_liberacao
    ? new Date(material.data_liberacao).toLocaleString("pt-BR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }) : ""

  async function baixar() {
    try {
      await baixarArquivo(`/materiais/${material.id}/arquivo`, material.arquivo_nome)
    } catch (erro) {
      console.error("Erro ao baixar arquivo:", erro)
      await avisar("Não foi possível baixar o arquivo.", "Algo deu errado")
    }
  }

  return (
    <article className="flex flex-col gap-4 rounded-cartao bg-superficie p-5 shadow-cartao md:flex-row md:items-start md:justify-between">
      <div className="min-w-0">
        <div className="mb-1.5 flex flex-wrap items-center gap-2">
          <Selo>{ROTULOS_TIPO_MATERIAL[material.tipo] || material.tipo}</Selo>
          <Selo tom={status.tom}>{status.rotulo}</Selo>
          {agendadoPara && <span className="text-xs text-texto-secundario">libera em {agendadoPara}</span>}
          {material.no_chat === false && <Selo tom="alerta">Fora do chat</Selo>}
        </div>
        <h3 className="text-[17px] font-semibold text-navy-900">{material.titulo}</h3>
        {classificacao && <p className="mt-1 text-xs font-medium text-primaria">{classificacao}</p>}
        {material.descricao && <p className="mt-1.5 text-[14px] text-texto-secundario">{material.descricao}</p>}
        <p className="mt-1.5 flex flex-wrap gap-x-2 text-[14px]">
          {material.tipo === "link" && material.link_url && (
            <a href={material.link_url} target="_blank" rel="noopener noreferrer" className="font-semibold text-primaria hover:underline">Abrir link</a>
          )}
          {material.tipo !== "link" && material.arquivo_nome && (
            <>
              <button type="button" onClick={baixar} className="font-semibold text-primaria hover:underline">{material.arquivo_nome}</button>
              {podeVisualizar(material) && <>· <button type="button" onClick={aoVer} className="font-semibold text-primaria hover:underline">visualizar</button></>}
            </>
          )}
        </p>
      </div>
      <div className="flex shrink-0 flex-wrap gap-2">
        {material.no_chat === false && <Botao pequeno onClick={aoIndexar}>Indexar para o chat</Botao>}
        <button type="button" onClick={aoReportar} className="px-2 text-[14px] font-semibold text-texto-secundario hover:text-perigo">Reportar</button>
        <Botao variante="neutra" pequeno onClick={aoEditar}>Editar</Botao>
        <Botao variante="perigo" pequeno onClick={aoExcluir}>Excluir</Botao>
      </div>
    </article>
  )
}

const TIPOS = [
  { valor: "pdf", rotulo: "PDF" },
  { valor: "documento", rotulo: "Documento" },
  { valor: "video", rotulo: "Vídeo" },
  { valor: "link", rotulo: "Link" },
]
const LIMITE = 15 * 1024 * 1024

function lerComoBase64(arquivo) {
  return new Promise((resolver, rejeitar) => {
    const leitor = new FileReader()
    leitor.onload = () => resolver(leitor.result)
    leitor.onerror = () => rejeitar(leitor.error)
    leitor.readAsDataURL(arquivo)
  })
}

function FormularioMaterial({ material, turmas, turmaPadrao, aoFechar, aoSalvar }) {
  const editando = Boolean(material)
  const [campos, setCampos] = useState({
    titulo: material?.titulo || "", descricao: material?.descricao || "", tipo: material?.tipo || "pdf",
    link_url: material?.link_url || "", assunto: material?.assunto || "", topico: material?.topico || "",
    aula: material?.aula || "", semestre: material?.semestre || "", data_liberacao: material?.data_liberacao || null,
  })
  // Quem abriu o formulário estando numa disciplina espera publicar nela.
  const [marcadas, setMarcadas] = useState(turmaPadrao ? [turmaPadrao] : [])
  const [arquivo, setArquivo] = useState(null)
  const [mensagem, setMensagem] = useState({ texto: "", sucesso: false })
  const [enviando, setEnviando] = useState(false)
  const mudar = (nome) => (valor) => setCampos((atual) => ({ ...atual, [nome]: valor }))
  const ehLink = campos.tipo === "link"

  async function salvar(publicar) {
    setMensagem({ texto: "Salvando...", sucesso: false })
    setEnviando(true)
    try {
      const comuns = {
        titulo: campos.titulo.trim(), descricao: campos.descricao.trim(), assunto: campos.assunto.trim(),
        topico: campos.topico.trim(), aula: campos.aula.trim(), semestre: campos.semestre.trim(),
        rascunho: !publicar, data_liberacao: campos.data_liberacao,
      }
      let resposta
      if (editando) {
        // Na edição, tipo e arquivo não mudam: trocar o arquivo seria outro material.
        resposta = await api(`/materiais/${material.id}`, {
          method: "PUT", body: JSON.stringify({ ...comuns, ...(ehLink && { link_url: campos.link_url.trim() }) }),
        })
      } else {
        if (!ehLink && !arquivo) return setMensagem({ texto: "Selecione um arquivo." })
        if (!ehLink && arquivo.size > LIMITE) return setMensagem({ texto: "O arquivo passa do limite de 15MB." })
        if (!marcadas.length) return setMensagem({ texto: "Escolha pelo menos uma disciplina." })
        resposta = await api("/materiais", {
          method: "POST",
          body: JSON.stringify({
            ...comuns, turma_ids: marcadas, tipo: campos.tipo, link_url: ehLink ? campos.link_url.trim() : null,
            arquivo_base64: ehLink ? null : await lerComoBase64(arquivo), arquivo_nome: ehLink ? null : arquivo.name,
          }),
        })
      }
      const resultado = await resposta.json()
      if (!resultado.sucesso) return setMensagem({ texto: resultado.mensagem })
      aoSalvar(resultado.aviso_indexacao)
    } catch (erro) {
      console.error("Erro ao salvar material:", erro)
      setMensagem({ texto: ERRO_DE_CONEXAO })
    } finally {
      setEnviando(false)
    }
  }

  return (
    <Cartao titulo={editando ? "Editar material" : "Novo material"} className="mb-5">
      <form onSubmit={(evento) => { evento.preventDefault(); salvar(evento.nativeEvent.submitter?.value !== "rascunho") }} className="flex flex-col gap-4">
        <Texto rotulo="Título" valor={campos.titulo} aoMudar={mudar("titulo")} obrigatorio placeholder="ex.: Protocolo de atendimento — Arritmias" />
        {/* Some ao editar: a edição vale só para o registro daquela disciplina. */}
        {!editando && <ChecklistTurmas turmas={turmas} marcadas={marcadas} aoMudar={setMarcadas} />}
        <AreaDeTexto rotulo="Descrição (opcional)" valor={campos.descricao} aoMudar={mudar("descricao")} linhas={3} placeholder="Alguma observação sobre o material" />

        <div className="grid gap-4 sm:grid-cols-2">
          {editando ? (
            <p className="text-sm text-texto-secundario">Tipo: <strong className="text-texto">{ROTULOS_TIPO_MATERIAL[campos.tipo]}</strong></p>
          ) : <Escolha rotulo="Tipo" valor={campos.tipo} aoMudar={mudar("tipo")} opcoes={TIPOS} />}
          {ehLink ? (
            <Texto rotulo="Link" tipo="url" valor={campos.link_url} aoMudar={mudar("link_url")} placeholder="https://..." obrigatorio />
          ) : !editando && (
            <label className="flex flex-col gap-1.5 text-[14px] font-medium text-texto">
              Arquivo
              <input type="file" onChange={(e) => setArquivo(e.target.files?.[0] || null)} className="text-sm font-normal" />
              <span className="text-xs font-normal text-texto-secundario">Até 15MB. PDF, DOC(X), TXT, ODT, MP4, MOV, WEBM ou MKV, conforme o tipo.</span>
            </label>
          )}
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Texto rotulo="Assunto" valor={campos.assunto} aoMudar={mudar("assunto")} placeholder="ex.: Cardiologia" />
          <Texto rotulo="Tópico" valor={campos.topico} aoMudar={mudar("topico")} placeholder="ex.: Arritmias" />
          <Texto rotulo="Aula" valor={campos.aula} aoMudar={mudar("aula")} placeholder="ex.: Aula 3" />
          <Texto rotulo="Semestre" valor={campos.semestre} aoMudar={mudar("semestre")} placeholder="ex.: 2026/2" />
        </div>

        <div className="max-w-sm">
          <SeletorDataHora rotulo="Agendar liberação (opcional)" valor={campos.data_liberacao} aoMudar={mudar("data_liberacao")}
            dica="Deixe em branco para liberar assim que publicar." />
        </div>

        <div className="flex flex-wrap gap-2.5">
          <Botao tipo="submit" desativado={enviando}>Publicar</Botao>
          <button type="submit" value="rascunho" disabled={enviando}
            className="rounded-campo border border-borda bg-superficie px-4 py-3 text-sm font-semibold text-texto hover:bg-fundo">Salvar rascunho</button>
          <Botao variante="neutra" onClick={aoFechar}>Cancelar</Botao>
        </div>
        <MensagemDeFormulario texto={mensagem.texto} sucesso={mensagem.sucesso} />
      </form>
    </Cartao>
  )
}
