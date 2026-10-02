import { useState } from "react"

import { Botao } from "../../componentes/Botao"
import { Carregando, Cartao, EstadoVazio } from "../../componentes/Cartao"
import { AreaDeTexto, Escolha, MensagemDeFormulario } from "../../componentes/Campos"
import { Selo } from "../../componentes/Selo"
import { useApi } from "../../hooks/useApi"
import { useDialogo } from "../../hooks/useDialogo"
import { useSessao } from "../../hooks/useSessao"
import { Cabecalho } from "../../layout/Painel"
import { api, ERRO_DE_CONEXAO } from "../../lib/api"
import { dataComAno } from "../../lib/formatos"

/**
 * Denúncias na visão de quem reporta — aluno e professor. Acompanha o que
 * foi reportado; reportar acontece também no próprio material ("Reportar"),
 * porque uma denúncia que exige lembrar o nome do arquivo e vir até aqui é
 * uma denúncia que ninguém faz.
 */
export function Denuncias() {
  const { dados, carregando, erro, recarregar } = useApi("/denuncias")
  const [formulario, setFormulario] = useState(false)
  const denuncias = dados?.denuncias || []

  return (
    <>
      <Cabecalho titulo="Denúncias" descricao="Reporte conteúdo com problema e acompanhe o que a administração respondeu.">
        {!formulario && <Botao onClick={() => setFormulario(true)}>Reportar conteúdo</Botao>}
      </Cabecalho>

      {formulario && (
        <NovaDenuncia motivos={dados?.motivos || []} aoFechar={() => setFormulario(false)}
          aoEnviar={() => { setFormulario(false); recarregar() }} />
      )}

      {carregando && <Carregando />}
      {erro && <EstadoVazio>{erro}</EstadoVazio>}
      {dados?.sucesso && denuncias.length === 0 && (
        <EstadoVazio>Você ainda não reportou nenhum conteúdo. Use o botão acima, ou o link "Reportar" no próprio material.</EstadoVazio>
      )}

      <section className="flex flex-col gap-3">
        {denuncias.map((denuncia) => <LinhaDenuncia key={denuncia.id} denuncia={denuncia} aoMudar={recarregar} />)}
      </section>
    </>
  )
}

const TOM_DO_STATUS = { aberta: "neutro", em_analise: "alerta", concluida: "sucesso", arquivada: "neutro", retirada: "neutro" }

function LinhaDenuncia({ denuncia, aoMudar }) {
  const { confirmar, avisar } = useDialogo()
  // Só dá para voltar atrás antes de a administração encerrar o caso.
  const podeRetirar = denuncia.status === "aberta" || denuncia.status === "em_analise"

  /**
   * O aviso muda conforme o estado, porque a consequência muda: sem ninguém
   * ter lido, a denúncia some; em análise, fica registrada como retirada — e
   * dizer isso antes evita achar que apagou algo que continua lá.
   */
  async function retirar() {
    const emAnalise = denuncia.status === "em_analise"
    const texto = emAnalise
      ? `A administração já começou a analisar "${denuncia.material_titulo}".\n\nA denúncia deixa de estar na fila, mas continua registrada como retirada, e a administração é avisada.`
      : `Retirar a denúncia de "${denuncia.material_titulo}"?\n\nComo ninguém analisou ainda, ela é apagada e não fica registrada.`
    if (!(await confirmar(texto, { titulo: "Retirar denúncia", rotulo: "Retirar", perigo: !emAnalise }))) return

    try {
      const resultado = await (await api(`/denuncias/${denuncia.id}`, { method: "DELETE" })).json()
      await avisar(resultado.mensagem, resultado.sucesso ? "Denúncia retirada" : "Algo deu errado")
      aoMudar()
    } catch (falha) {
      console.error("Erro ao retirar denúncia:", falha)
      await avisar(ERRO_DE_CONEXAO, "Algo deu errado")
    }
  }

  return (
    <article className="flex flex-col gap-3 rounded-cartao bg-superficie p-5 shadow-cartao md:flex-row md:items-start md:justify-between">
      <div className="min-w-0">
        <div className="mb-1.5 flex flex-wrap gap-2">
          <Selo>{denuncia.motivo_rotulo}</Selo>
          <Selo tom={TOM_DO_STATUS[denuncia.status]}>{denuncia.status_rotulo}</Selo>
        </div>
        <h3 className="font-bold text-navy-900">{denuncia.material_titulo}</h3>
        <p className="mt-1 text-xs font-medium text-primaria">
          {denuncia.turma_nome ? `${denuncia.turma_nome} · ` : ""}reportado em {dataComAno(denuncia.criado_em)}
        </p>
        {denuncia.descricao && <p className="mt-1.5 text-[13px] text-texto-secundario">{denuncia.descricao}</p>}
        {denuncia.acao ? (
          <div className="mt-2.5 rounded-campo bg-fundo px-3 py-2 text-[13px]">
            <strong className="text-navy-900">Resposta da administração</strong>
            <p className="mt-0.5 text-texto">{denuncia.acao}</p>
          </div>
        ) : denuncia.status === "aberta" && <p className="mt-1.5 text-[13px] text-texto-secundario">Aguardando a administração analisar.</p>}
      </div>
      {podeRetirar && <Botao variante="neutra" onClick={retirar} className="shrink-0 py-2 text-[13px]">Retirar</Botao>}
    </article>
  )
}

function NovaDenuncia({ motivos, aoFechar, aoEnviar }) {
  const { usuario } = useSessao()
  const professor = usuario.tipo === "professor"
  const lista = useApi(professor ? "/materiais" : "/aluno/materiais")
  // O professor só reporta material publicado — rascunho é dele e ainda dá para corrigir.
  const materiais = (lista.dados?.materiais || []).filter((m) => !professor || m.status === "publicado")
  const [material, setMaterial] = useState("")
  const [motivo, setMotivo] = useState("")
  const [descricao, setDescricao] = useState("")
  const [mensagem, setMensagem] = useState("")
  const { avisar } = useDialogo()

  async function enviar(evento) {
    evento.preventDefault()
    const materialId = Number(material || materiais[0]?.id)
    if (!materialId) return setMensagem("Escolha o material que você quer reportar.")
    try {
      const resultado = await (await api("/denuncias", {
        method: "POST",
        body: JSON.stringify({ material_id: materialId, motivo: motivo || motivos[0]?.valor, descricao: descricao.trim() }),
      })).json()
      if (!resultado.sucesso) return setMensagem(resultado.mensagem || "Não foi possível registrar a denúncia.")
      aoEnviar()
      await avisar(resultado.mensagem, "Denúncia registrada")
    } catch (falha) {
      console.error("Erro ao enviar denúncia:", falha)
      setMensagem(ERRO_DE_CONEXAO)
    }
  }

  const opcoesMaterial = materiais.length
    ? materiais.map((m) => ({ valor: String(m.id), rotulo: `${m.titulo} — ${m.turma_nome}` }))
    : [{ valor: "", rotulo: lista.carregando ? "Carregando..." : "Nenhum material disponível" }]

  return (
    <Cartao titulo="Reportar conteúdo" className="mb-5">
      <form onSubmit={enviar} className="flex flex-col gap-4">
        <div>
          <Escolha rotulo="Material" valor={material || opcoesMaterial[0].valor} aoMudar={setMaterial} opcoes={opcoesMaterial} />
          <span className="mt-1 block text-xs text-texto-secundario">Só aparecem os materiais que você tem acesso.</span>
        </div>
        {motivos.length > 0 && <Escolha rotulo="Motivo" valor={motivo || motivos[0].valor} aoMudar={setMotivo} opcoes={motivos} />}
        <AreaDeTexto rotulo="O que está errado" valor={descricao} aoMudar={setDescricao} maximo={1000}
          placeholder="Descreva o problema. Quanto mais específico, mais rápido a administração resolve." />
        <div className="flex gap-2.5">
          <Botao tipo="submit">Enviar denúncia</Botao>
          <Botao variante="neutra" onClick={aoFechar}>Cancelar</Botao>
        </div>
        <MensagemDeFormulario texto={mensagem} />
      </form>
    </Cartao>
  )
}
