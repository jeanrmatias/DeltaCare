import { useState } from "react"

import { FormularioAnotacao, ItemAnotacao } from "../../componentes/Anotacoes"
import { Carregando, Cartao, EstadoVazio } from "../../componentes/Cartao"
import { useApagarAnotacao } from "../../hooks/useApagarAnotacao"
import { useApi } from "../../hooks/useApi"
import { Cabecalho } from "../../layout/Painel"
import { normalizar } from "../../lib/texto"

/**
 * O caderno do aluno: todas as anotações, de todos os materiais.
 *
 * Agrupadas por material e com busca, porque o uso real é "onde foi que eu
 * escrevi sobre o forame magno?" — e ninguém lembra em que material foi. A
 * busca é na própria tela: são as anotações de uma pessoa, cabem inteiras na
 * memória do navegador.
 */
export function Anotacoes() {
  const { dados, carregando, erro, recarregar } = useApi("/aluno/anotacoes")
  const [busca, setBusca] = useState("")
  const [editando, setEditando] = useState(null)
  const apagar = useApagarAnotacao()

  const todas = dados?.anotacoes || []
  const termo = normalizar(busca.trim())
  const visiveis = termo ? todas.filter((a) => normalizar(`${a.texto} ${a.trecho} ${a.material_titulo}`).includes(termo)) : todas

  // Um grupo por material. Material apagado pelo professor não tem id, mas a
  // anotação sobrevive — agrupa pelo título que ficou guardado.
  const grupos = new Map()
  visiveis.forEach((anotacao) => {
    const chave = anotacao.material_id ?? `removido:${anotacao.material_titulo}`
    grupos.set(chave, [...(grupos.get(chave) || []), anotacao])
  })

  return (
    <>
      <Cabecalho titulo="Anotações" descricao="Seu caderno, de todos os materiais. Só você vê." />

      <label className="mb-5 flex max-w-md flex-col gap-1.5 text-[13px] text-texto-secundario">
        Buscar nas anotações
        <input type="search" value={busca} onChange={(evento) => setBusca(evento.target.value)} placeholder="ex.: forame magno"
          autoComplete="off" className="rounded-campo border border-borda-campo bg-superficie px-3 py-2.5 text-sm text-texto outline-none focus:border-primaria" />
      </label>

      {carregando && <Carregando />}
      {erro && <EstadoVazio>{erro}</EstadoVazio>}
      {dados && visiveis.length === 0 && (
        <EstadoVazio>
          {todas.length ? "Nenhuma anotação com esse termo." : "Nenhuma anotação ainda. Em Materiais, use o botão Anotar de qualquer material."}
        </EstadoVazio>
      )}

      <div className="flex flex-col gap-4">
        {[...grupos.entries()].map(([chave, anotacoes]) => (
          <Cartao key={chave}
            titulo={anotacoes[0].material_disponivel ? anotacoes[0].material_titulo : `${anotacoes[0].material_titulo} (material removido pelo professor)`}>
            <div className="flex flex-col gap-2.5">
              {anotacoes.map((anotacao) => (
                <ItemAnotacao key={anotacao.id} anotacao={anotacao} aoEditar={setEditando}
                  aoApagar={async (alvo) => (await apagar(alvo)) && recarregar()} />
              ))}
            </div>
          </Cartao>
        ))}
      </div>

      {editando && (
        <FormularioAnotacao
          material={{ id: editando.material_id, titulo: editando.material_titulo }}
          anotacao={editando}
          aoFechar={() => setEditando(null)}
          aoSalvar={() => { setEditando(null); recarregar() }}
        />
      )}
    </>
  )
}
