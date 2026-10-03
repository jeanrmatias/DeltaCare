import { useEffect, useState } from "react"

import { useApi } from "../hooks/useApi"
import { useApagarAnotacao } from "../hooks/useApagarAnotacao"
import { api, ERRO_DE_CONEXAO } from "../lib/api"
import { dataComAno } from "../lib/formatos"
import { Botao } from "./Botao"
import { AreaDeTexto, MensagemDeFormulario } from "./Campos"
import { AcoesDoModal, Modal } from "./Modal"

/**
 * Anotações do aluno: a lista de um material, o formulário e o item.
 *
 * Anotação é privada, e a tela diz isso ao lado do campo: o aluno só escreve
 * com franqueza ("não entendi nada desta aula") se souber que ninguém mais
 * lê. E é verdade no servidor: não existe rota de professor nem de
 * administração para anotações.
 */

/** Uma anotação, com editar e apagar. `comMaterial` mostra de que material é. */
export function ItemAnotacao({ anotacao, aoEditar, aoApagar, comMaterial = false }) {
  return (
    <article className="rounded-bloco bg-fundo px-4 py-3">
      {comMaterial && (
        <p className="mb-1.5 text-xs font-semibold text-texto-secundario">
          {anotacao.material_disponivel ? anotacao.material_titulo : `${anotacao.material_titulo} (material removido)`}
        </p>
      )}
      {anotacao.trecho && (
        <blockquote className="mb-2 border-l-3 border-primaria pl-3 text-[13px] text-texto-secundario italic">{anotacao.trecho}</blockquote>
      )}
      <p className="text-sm leading-relaxed whitespace-pre-wrap text-texto">{anotacao.texto}</p>
      <div className="mt-2 flex items-center gap-3 text-xs text-texto-secundario">
        <span>{dataComAno(anotacao.atualizado_em)}</span>
        <button type="button" onClick={() => aoEditar(anotacao)} className="font-semibold text-primaria hover:underline">Editar</button>
        <button type="button" onClick={() => aoApagar(anotacao)} className="font-semibold text-perigo hover:underline">Apagar</button>
      </div>
    </article>
  )
}

/** Criar (sem `anotacao`) ou editar. `aoSalvar` recebe a anotação salva. */
export function FormularioAnotacao({ material, anotacao, aoFechar, aoSalvar }) {
  const [trecho, setTrecho] = useState(anotacao?.trecho || "")
  const [texto, setTexto] = useState(anotacao?.texto || "")
  const [mensagem, setMensagem] = useState("")
  const [enviando, setEnviando] = useState(false)

  async function salvar(evento) {
    evento.preventDefault()
    if (!texto.trim()) return setMensagem("Escreva a anotação.")

    setEnviando(true)
    try {
      const corpo = { texto: texto.trim(), trecho: trecho.trim() }
      const resposta = anotacao
        ? await api(`/aluno/anotacoes/${anotacao.id}`, { method: "PUT", body: JSON.stringify(corpo) })
        : await api("/aluno/anotacoes", { method: "POST", body: JSON.stringify({ ...corpo, material_id: material.id }) })
      const dados = await resposta.json()
      if (!dados.sucesso) return setMensagem(dados.mensagem || "Não foi possível salvar.")
      aoSalvar(dados.anotacao)
    } catch (erro) {
      console.error("Erro ao salvar anotação:", erro)
      setMensagem(ERRO_DE_CONEXAO)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <Modal aberto aoFechar={aoFechar} titulo={anotacao ? "Editar anotação" : `Nova anotação · ${material.titulo}`}>
      <p className="mb-4 text-[13px] text-texto-secundario">Só você vê suas anotações. Nem o professor, nem a coordenação.</p>
      <form onSubmit={salvar} className="flex flex-col gap-4">
        <AreaDeTexto rotulo="Trecho do material (opcional)" valor={trecho} aoMudar={setTrecho} linhas={2} maximo={1000}
          placeholder="Cole aqui a passagem a que a anotação se refere" />
        <AreaDeTexto rotulo="Anotação" valor={texto} aoMudar={setTexto} linhas={5} maximo={5000} />
        <MensagemDeFormulario texto={mensagem} />
        <AcoesDoModal>
          <Botao variante="neutra" onClick={aoFechar}>Cancelar</Botao>
          <Botao tipo="submit" desativado={enviando}>{enviando ? "Salvando..." : "Salvar"}</Botao>
        </AcoesDoModal>
      </form>
    </Modal>
  )
}

/** As anotações de um material: a lista e o botão de escrever. `aoMudar(total)` atualiza o contador da tela. */
export function PainelAnotacoes({ material, aoFechar, aoMudar }) {
  const { dados, carregando, erro, recarregar } = useApi(`/aluno/anotacoes?material_id=${material.id}`)
  const [editando, setEditando] = useState(null) // null: nada; {}: nova; anotação: editar
  const apagar = useApagarAnotacao()
  const anotacoes = dados?.anotacoes || []

  function mudou() {
    setEditando(null)
    recarregar()
  }

  // O contador da tela de Materiais acompanha o que o painel acabou de
  // carregar. É efeito, e não código solto na renderização: avisar outro
  // componente é mudar o estado dele, e isso não pode acontecer no meio do
  // desenho deste.
  const total = dados ? anotacoes.length : null
  useEffect(() => {
    if (total !== null) aoMudar?.(total)
    // aoMudar fica fora de propósito: é uma função nova a cada render de
    // quem usa, e reavisar o mesmo total a cada render não muda nada.
  }, [total]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <>
      <Modal aberto={!editando} aoFechar={aoFechar} largura="max-w-[620px]" rotulo={`Anotações · ${material.titulo}`}>
        <div className="mb-4 flex items-start justify-between gap-3">
          <h2 className="text-lg font-bold text-navy-900">Anotações · {material.titulo}</h2>
          <Botao variante="neutra" onClick={aoFechar} className="py-2">Fechar</Botao>
        </div>
        <Botao onClick={() => setEditando({})}>Nova anotação</Botao>
        <div className="mt-4 flex max-h-[55vh] flex-col gap-2.5 overflow-y-auto">
          {carregando && <p className="text-sm text-texto-secundario">Carregando...</p>}
          {erro && <p className="text-sm text-texto-secundario">{erro}</p>}
          {dados && !anotacoes.length && <p className="text-sm text-texto-secundario">Nenhuma anotação neste material ainda.</p>}
          {anotacoes.map((anotacao) => (
            <ItemAnotacao key={anotacao.id} anotacao={anotacao} aoEditar={setEditando}
              aoApagar={async (alvo) => (await apagar(alvo)) && recarregar()} />
          ))}
        </div>
      </Modal>

      {editando && (
        <FormularioAnotacao material={material} anotacao={editando.id ? editando : null}
          aoFechar={() => setEditando(null)} aoSalvar={mudou} />
      )}
    </>
  )
}
