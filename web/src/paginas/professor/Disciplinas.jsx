import { Link } from "react-router"

import { Carregando, EstadoVazio } from "../../componentes/Cartao"
import { useApi } from "../../hooks/useApi"
import { Cabecalho } from "../../layout/Painel"

/**
 * As disciplinas atribuídas ao professor. Só leitura: quem cria, edita e
 * atribui disciplina é a administração.
 */
export function Disciplinas() {
  const { dados, carregando, erro } = useApi("/turmas")
  const turmas = dados?.turmas || []

  return (
    <>
      <Cabecalho titulo="Disciplinas" descricao="As disciplinas atribuídas a você pela administração. Só um administrador pode criar ou editar disciplinas." />
      {carregando && <Carregando />}
      {erro && <EstadoVazio>{erro}</EstadoVazio>}
      {dados && turmas.length === 0 && (
        <EstadoVazio>Você ainda não tem nenhuma disciplina atribuída. Fale com a administração para ser vinculado a uma.</EstadoVazio>
      )}
      <section className="grid grid-cols-[repeat(auto-fill,minmax(220px,1fr))] gap-4">
        {turmas.map((turma) => (
          <article key={turma.id} className="rounded-cartao bg-superficie p-5 shadow-cartao">
            <h2 className="text-[17px] font-bold text-navy-900">{turma.nome}</h2>
            <div className="mt-1 flex flex-wrap gap-1.5">
              <span className="rounded-campo bg-fundo px-2 py-0.5 text-xs font-semibold text-texto-secundario">{turma.semestre}</span>
              {turma.vigente === false && <span className="rounded-campo bg-fundo px-2 py-0.5 text-xs font-semibold text-texto-secundario">semestre anterior</span>}
            </div>
            <p className="mt-3 mb-3.5 text-[13px] text-texto-secundario">
              {turma.total_alunos ?? 0} aluno(s) · {turma.materiais_publicados} material(is) publicado(s)
            </p>
            <Link to={`/professor/materiais?turma=${turma.id}`}
              className="inline-flex w-full justify-center rounded-campo border border-borda px-3.5 py-2 text-[13px] font-semibold text-texto hover:bg-fundo">
              Ver materiais
            </Link>
          </article>
        ))}
      </section>
    </>
  )
}
