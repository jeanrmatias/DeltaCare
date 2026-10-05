import { useState } from "react"

import { Aviso } from "../../componentes/Aviso"
import { Botao } from "../../componentes/Botao"
import { Carregando, Cartao } from "../../componentes/Cartao"
import { AreaDeTexto, MensagemDeFormulario, Texto } from "../../componentes/Campos"
import { useApi } from "../../hooks/useApi"
import { useDialogo } from "../../hooks/useDialogo"
import { useSessao } from "../../hooks/useSessao"
import { Cabecalho } from "../../layout/Painel"
import { api, ERRO_DE_CONEXAO } from "../../lib/api"
import { dataEHora } from "../../lib/formatos"

/**
 * Avisos: escrever para as disciplinas, e ver o que chegou. Um componente
 * para professor e administração; quem pode o quê é do servidor
 * (regras/avisos.py). Aqui muda só o que a tela oferece: a administração tem
 * "instituição inteira" e escolhe entre todas as disciplinas do semestre; o
 * professor, entre as dele.
 */
export function Avisos() {
  const { usuario } = useSessao()
  const adm = usuario.tipo === "adm"
  const enviados = useApi("/avisos/enviados")
  const recebidos = useApi("/avisos/recebidos")

  return (
    <>
      <Cabecalho titulo="Avisos" descricao={adm ? "Escreva para a instituição inteira ou para disciplinas específicas." : "Escreva para as suas disciplinas."} />
      <div className="flex max-w-3xl flex-col gap-5">
        <NovoAviso adm={adm} aoEnviar={enviados.recarregar} />
        <ListaDeAvisos titulo="Enviados" consulta={enviados} vazio="Você ainda não enviou nenhum aviso." proprios />
        <ListaDeAvisos titulo="Recebidos" consulta={recebidos} vazio={adm ? "Nenhum aviso de outros administradores." : "Nenhum aviso da administração."} />
      </div>
    </>
  )
}

function NovoAviso({ adm, aoEnviar }) {
  const disciplinas = useApi(adm ? "/admin/turmas" : "/turmas")
  const semestre = useApi(adm ? "/semestre" : null)
  const [geral, setGeral] = useState(false)
  const [marcadas, setMarcadas] = useState([])
  const [titulo, setTitulo] = useState("")
  const [conteudo, setConteudo] = useState("")
  const [urgente, setUrgente] = useState(false)
  const [mensagem, setMensagem] = useState({ texto: "", sucesso: false })
  const { confirmar } = useDialogo()

  // Só o semestre de agora: avisar disciplina que já terminou não chega a ninguém útil.
  const vigente = semestre.dados?.semestre
  const opcoes = (disciplinas.dados?.turmas || []).filter((d) => (adm ? !vigente || d.semestre === vigente : d.vigente !== false))
  const todas = opcoes.length > 0 && marcadas.length === opcoes.length

  async function enviar(evento) {
    evento.preventDefault()
    if (!geral && !marcadas.length) return setMensagem({ texto: "Escolha pelo menos uma disciplina." })

    const destino = geral ? "a instituição inteira" : opcoes.filter((d) => marcadas.includes(d.id)).map((d) => d.nome).join(", ")
    if (!(await confirmar(`Enviar${urgente ? " como URGENTE" : ""} para ${destino}?\n\n"${titulo.trim()}"`, { titulo: "Enviar aviso", rotulo: "Enviar" }))) return

    try {
      const resultado = await (await api("/avisos", {
        method: "POST",
        body: JSON.stringify({ titulo: titulo.trim(), conteudo: conteudo.trim(), urgente, geral, turma_ids: geral ? [] : marcadas }),
      })).json()
      setMensagem({ texto: resultado.mensagem, sucesso: resultado.sucesso })
      if (resultado.sucesso) {
        setTitulo(""); setConteudo(""); setUrgente(false); setGeral(false); setMarcadas([])
        aoEnviar()
      }
    } catch (erro) {
      console.error("Erro ao enviar aviso:", erro)
      setMensagem({ texto: ERRO_DE_CONEXAO })
    }
  }

  return (
    <Cartao titulo="Novo aviso">
      <form onSubmit={enviar} className="flex flex-col gap-4">
        {/* "Instituição inteira" só existe para a administração: o professor
            não recebe um controle que o servidor recusaria. */}
        {adm && (
          <label className="flex items-center gap-2 text-sm font-semibold text-texto">
            <input type="checkbox" checked={geral} onChange={(e) => setGeral(e.target.checked)} className="size-4 accent-primaria" />
            Para a instituição inteira
          </label>
        )}
        {!geral && (
          <fieldset>
            <div className="mb-1.5 flex items-center justify-between">
              <legend className="text-[14px] font-semibold text-texto">Para quais disciplinas</legend>
              <button type="button" onClick={() => setMarcadas(todas ? [] : opcoes.map((d) => d.id))} className="text-xs font-semibold text-primaria hover:underline">
                {todas ? "Nenhuma" : "Todas"}
              </button>
            </div>
            {disciplinas.carregando && <Carregando />}
            {disciplinas.dados && !opcoes.length && <p className="text-sm text-texto-secundario">Nenhuma disciplina neste semestre.</p>}
            <div className="flex flex-wrap gap-x-5 gap-y-1.5">
              {opcoes.map((d) => (
                <label key={d.id} className="flex items-center gap-1.5 text-sm text-texto">
                  <input type="checkbox" checked={marcadas.includes(d.id)} className="size-4 accent-primaria"
                    onChange={() => setMarcadas(marcadas.includes(d.id) ? marcadas.filter((m) => m !== d.id) : [...marcadas, d.id])} />
                  {adm && d.professor_email ? `${d.nome} · ${d.professor_email}` : d.nome}
                </label>
              ))}
            </div>
          </fieldset>
        )}
        <Texto rotulo="Título" valor={titulo} aoMudar={setTitulo} maximo={120} obrigatorio />
        <AreaDeTexto rotulo="Texto" valor={conteudo} aoMudar={setConteudo} maximo={4000} obrigatorio />
        <label className="flex items-center gap-2 text-sm font-semibold text-texto">
          <input type="checkbox" checked={urgente} onChange={(e) => setUrgente(e.target.checked)} className="size-4 accent-primaria" />
          Urgente <span className="font-normal text-texto-secundario">— fica no topo do mural por 7 dias</span>
        </label>
        <div><Botao tipo="submit">Enviar aviso</Botao></div>
        <MensagemDeFormulario texto={mensagem.texto} sucesso={mensagem.sucesso} />
      </form>
    </Cartao>
  )
}

function ListaDeAvisos({ titulo, consulta, vazio, proprios = false }) {
  const { confirmar, avisar } = useDialogo()
  const avisos = consulta.dados?.avisos || []

  async function apagar(aviso) {
    if (!(await confirmar(`Apagar "${aviso.titulo}" do mural?\n\nQuem já foi avisado pelo sino continua com a notificação.`,
      { titulo: "Apagar aviso", rotulo: "Apagar", perigo: true }))) return
    try {
      const resultado = await (await api(`/avisos/${aviso.id}`, { method: "DELETE" })).json()
      if (!resultado.sucesso) await avisar(resultado.mensagem, "Algo deu errado")
      consulta.recarregar()
    } catch (erro) {
      console.error("Erro ao apagar aviso:", erro)
      await avisar(ERRO_DE_CONEXAO, "Algo deu errado")
    }
  }

  return (
    <Cartao titulo={titulo}>
      {consulta.carregando && <Carregando />}
      {consulta.erro && <p className="text-sm text-texto-secundario">Não foi possível carregar os avisos.</p>}
      {consulta.dados && !avisos.length && <p className="text-sm text-texto-secundario">{vazio}</p>}
      <div className="flex flex-col gap-2.5">
        {avisos.map((aviso) => {
          const destino = aviso.geral ? "Instituição inteira" : aviso.disciplinas.join(", ")
          const rodape = proprios
            ? `${dataEHora(aviso.criado_em)} · para ${destino}`
            : `${aviso.autor_e_administracao ? "Administração" : aviso.autor} · ${dataEHora(aviso.criado_em)} · ${destino}`
          return (
            <Aviso key={aviso.id} aviso={aviso} rodape={rodape}>
              {proprios && <button type="button" onClick={() => apagar(aviso)} className="mt-1.5 text-xs font-semibold text-perigo hover:underline">Apagar</button>}
            </Aviso>
          )
        })}
      </div>
    </Cartao>
  )
}
