import { useMemo, useState } from "react"
import { useSearchParams } from "react-router"

import { Botao } from "../../componentes/Botao"
import { Carregando, EstadoVazio } from "../../componentes/Cartao"
import { ListaDeMateriais } from "../../componentes/ListaDeMateriais"
import { SeletorDisciplina } from "../../componentes/SeletorDisciplina"
import { useApi } from "../../hooks/useApi"
import { Cabecalho } from "../../layout/Painel"
import { ROTULOS_TIPO_MATERIAL } from "../../lib/formatos"

/**
 * Materiais liberados para o aluno.
 *
 * `/aluno/materiais` nunca devolve rascunho nem material agendado para o
 * futuro — a tela confia nisso e não filtra visibilidade por conta própria:
 * filtro de permissão em JavaScript não protege nada.
 *
 * A disciplina escolhida fica na URL (`?turma=2`), não só no estado: assim o
 * link "Ver materiais" da tela inicial chega aqui já filtrado, e o F5 não
 * perde a escolha.
 */
export function Materiais() {
  const [parametros, setParametros] = useSearchParams()
  const turma = Number(parametros.get("turma")) || null

  const turmas = useApi("/aluno/turmas")
  const materiais = useApi(turma ? `/aluno/materiais?turma_id=${turma}` : "/aluno/materiais")

  const [busca, setBusca] = useState("")
  const [filtros, setFiltros] = useState(FILTROS_VAZIOS)
  const todos = useMemo(() => materiais.dados?.materiais || [], [materiais.dados])
  const filtrados = useMemo(() => filtrar(todos, busca, filtros), [todos, busca, filtros])

  function escolherTurma(id) {
    setParametros(id ? { turma: String(id) } : {})
  }

  return (
    <>
      <Cabecalho titulo="Materiais" descricao="Tudo que os seus professores já liberaram nas disciplinas que você cursa.">
        {(turmas.dados?.turmas || []).length > 0 && (
          <SeletorDisciplina turmas={turmas.dados.turmas} valor={turma} aoMudar={escolherTurma} comTodas />
        )}
        <input
          type="search"
          value={busca}
          onChange={(evento) => setBusca(evento.target.value)}
          placeholder="Buscar por título, assunto ou tópico..."
          aria-label="Buscar materiais"
          className="w-64 max-w-full rounded-campo border border-borda bg-superficie px-3 py-2.5 text-sm outline-none focus:border-primaria"
        />
      </Cabecalho>

      {todos.length > 0 && <Filtros materiais={todos} filtros={filtros} aoMudar={setFiltros} />}

      {materiais.carregando && <Carregando />}
      {materiais.erro && <EstadoVazio>{materiais.erro}</EstadoVazio>}
      {materiais.dados && filtrados.length === 0 && (
        <EstadoVazio>
          {todos.length === 0
            ? "Nenhum material liberado até agora. Assim que o professor publicar, aparece aqui."
            : "Nenhum material corresponde à sua busca."}
        </EstadoVazio>
      )}
      {filtrados.length > 0 && <ListaDeMateriais materiais={filtrados} />}
    </>
  )
}

const FILTROS_VAZIOS = { assunto: "", topico: "", tipo: "", periodo: "" }

function filtrar(materiais, busca, { assunto, topico, tipo, periodo }) {
  const termo = busca.trim().toLowerCase()
  const desde = periodo ? Date.now() - Number(periodo) * 24 * 60 * 60 * 1000 : null

  return materiais.filter((material) => {
    if (assunto && material.assunto !== assunto) return false
    if (topico && material.topico !== topico) return false
    if (tipo && material.tipo !== tipo) return false
    if (desde) {
      const criado = new Date(material.criado_em).getTime()
      if (Number.isNaN(criado) || criado < desde) return false
    }
    if (!termo) return true
    return [material.titulo, material.assunto, material.topico, material.aula, material.descricao]
      .filter(Boolean)
      .join(" ")
      .toLowerCase()
      .includes(termo)
  })
}

/**
 * As opções dos filtros saem do que existe nos materiais carregados. Uma
 * lista fixa ofereceria filtros que não retornam nada — e esconderia os
 * assuntos que o professor cadastrou.
 */
function Filtros({ materiais, filtros, aoMudar }) {
  const valores = (campo) => [...new Set(materiais.map((m) => m[campo]).filter(Boolean))].sort((a, b) => a.localeCompare(b, "pt-BR"))
  const mudar = (campo) => (evento) => aoMudar({ ...filtros, [campo]: evento.target.value })

  const seletor = (rotulo, campo, opcoes) => (
    <label className="flex min-w-[150px] flex-1 flex-col gap-1.5 text-[13px] font-medium text-texto">
      {rotulo}
      <select value={filtros[campo]} onChange={mudar(campo)}
        className="rounded-campo border border-borda bg-superficie px-3 py-2 text-sm font-normal outline-none focus:border-primaria">
        {opcoes.map(([valor, texto]) => <option key={valor} value={valor}>{texto}</option>)}
      </select>
    </label>
  )

  return (
    <section className="mb-5 flex flex-wrap items-end gap-3 rounded-cartao bg-superficie p-4 shadow-cartao">
      {seletor("Assunto", "assunto", [["", "Todos"], ...valores("assunto").map((v) => [v, v])])}
      {seletor("Tópico", "topico", [["", "Todos"], ...valores("topico").map((v) => [v, v])])}
      {seletor("Tipo", "tipo", [["", "Todos"], ...valores("tipo").map((v) => [v, ROTULOS_TIPO_MATERIAL[v] || v])])}
      {seletor("Período", "periodo", [["", "Qualquer data"], ["7", "Últimos 7 dias"], ["30", "Últimos 30 dias"], ["90", "Últimos 3 meses"]])}
      <Botao variante="neutra" onClick={() => aoMudar(FILTROS_VAZIOS)} className="py-2">Limpar</Botao>
    </section>
  )
}
