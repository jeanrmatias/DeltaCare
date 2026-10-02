import { Cabecalho } from "../../layout/Painel"

/**
 * Página de um módulo que ainda não existe.
 *
 * Em vez de um "em breve" sem conteúdo ou de uma tela com dados de exemplo,
 * o item do menu leva aqui: diz que o módulo não foi construído e o que ele
 * vai fazer. Declarar o que falta é melhor do que simular — quem está na
 * tela não teria como saber que o dado de exemplo não é real.
 *
 * O catálogo vem do backlog do produto. Quando o módulo for construído, sai
 * daqui e ganha a sua rota de verdade.
 */
const MODULOS_PLANEJADOS = {
  relatorios: {
    titulo: "Relatórios",
    resumo: "Indicadores da instituição para coordenação.",
    etapa: "Sprint 7",
    itens: ["Desempenho por turma e por período", "Uso da plataforma por perfil", "Exportação dos indicadores"],
  },
}

export function ModuloPlanejado({ chave }) {
  const modulo = MODULOS_PLANEJADOS[chave]

  return (
    <>
      <Cabecalho titulo={modulo.titulo} descricao={modulo.resumo} />
      <section className="max-w-2xl rounded-cartao border border-dashed border-borda bg-superficie p-6">
        <span className="rounded-full bg-fundo px-2.5 py-1 text-xs font-bold text-texto-secundario">{modulo.etapa}</span>
        <h2 className="mt-3 text-base font-semibold text-navy-900">Ainda não construído nesta versão</h2>
        <p className="mt-2 text-sm text-texto-secundario">O que este módulo vai permitir quando for entregue:</p>
        <ul className="mt-2 list-disc pl-5 text-sm text-texto">
          {modulo.itens.map((item) => <li key={item}>{item}</li>)}
        </ul>
      </section>
    </>
  )
}
