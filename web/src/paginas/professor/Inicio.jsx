import { Link } from "react-router"

import { Cartao, EstadoVazio, Numero, Numeros } from "../../componentes/Cartao"
import { ListaComContador } from "../../componentes/ListaComContador"
import { MuralDeAvisos } from "../../componentes/MuralDeAvisos"
import { Selo } from "../../componentes/Selo"
import { useApi } from "../../hooks/useApi"
import { useSessao } from "../../hooks/useSessao"
import { Cabecalho } from "../../layout/Painel"
import { dataCurta, ROTULOS_TIPO_MATERIAL, STATUS_DO_MATERIAL } from "../../lib/formatos"
import { nomeExibicao } from "../../lib/usuario"

/**
 * Tela inicial do professor, só do semestre vigente.
 *
 * As disciplinas passadas ficam em Semestres anteriores: somá-las aqui faria
 * "Alunos matriculados" crescer a cada semestre sem o professor ter mais
 * aluno nenhum. Cada bloco busca o seu dado sozinho: um erro em mensagens
 * não apaga as disciplinas da tela.
 */
export function InicioProfessor() {
  const { usuario } = useSessao()
  const turmas = useApi("/turmas")
  const materiais = useApi("/materiais")
  const atividades = useApi("/atividades")
  const conversas = useApi("/mensagens/conversas")
  const lacunas = useApi("/lacunas")

  const vigentes = (turmas.dados?.turmas || []).filter((turma) => turma.vigente !== false)
  const idsVigentes = new Set(vigentes.map((turma) => turma.id))
  const materiaisVigentes = (materiais.dados?.materiais || []).filter((m) => idsVigentes.has(m.turma_id))

  const paraCorrigir = (atividades.dados?.atividades || [])
    .filter((atividade) => atividade.a_corrigir > 0)
    .sort((a, b) => b.a_corrigir - a.a_corrigir)
  const naoLidas = (conversas.dados?.conversas || []).filter((conversa) => conversa.nao_lidas > 0)

  const primeiroNome = nomeExibicao(usuario).split(" ")[0]

  // As lacunas das disciplinas deste semestre, as mais perguntadas primeiro.
  const lacunasVigentes = (lacunas.dados?.disciplinas || [])
    .filter((d) => idsVigentes.has(d.id))
    .flatMap((d) => d.lacunas.map((l) => ({ ...l, disciplina: d.nome })))
    .sort((a, b) => b.alunos - a.alunos || b.perguntas - a.perguntas)

  return (
    <>
      <Cabecalho titulo={`Olá, Prof. ${primeiroNome}`} descricao={hojePorExtenso()} />

      {turmas.erro && <EstadoVazio>{turmas.erro}</EstadoVazio>}

      <Numeros>
        <Numero rotulo="Disciplinas" valor={vigentes.length} />
        <Numero rotulo="Alunos matriculados" valor={vigentes.reduce((soma, t) => soma + (t.total_alunos || 0), 0)} />
        <Numero rotulo="Materiais publicados" valor={materiaisVigentes.filter((m) => m.status === "publicado").length} />
        <Numero rotulo="Materiais agendados" valor={materiaisVigentes.filter((m) => m.status === "agendado").length} />
        <Numero rotulo="Entregas para corrigir" valor={paraCorrigir.reduce((soma, a) => soma + a.a_corrigir, 0)} />
      </Numeros>

      <div className="grid gap-5 min-[1101px]:grid-cols-[1fr_380px]">
        <div className="flex min-w-0 flex-col gap-5">
          <Cartao titulo="Minhas disciplinas">
            {vigentes.length === 0 && !turmas.carregando ? (
              <p className="text-sm text-texto-secundario">
                Você não tem disciplinas neste semestre. A administração é quem cria e atribui disciplinas.
              </p>
            ) : (
              <div className="grid grid-cols-[repeat(auto-fill,minmax(190px,1fr))] gap-4">
                {vigentes.map((turma) => (
                  <CartaoDisciplina key={turma.id} turma={turma} />
                ))}
              </div>
            )}
          </Cartao>

          <Cartao titulo="Materiais recentes">
            <MateriaisRecentes materiais={materiaisVigentes.slice(0, 5)} />
            <Link to="/professor/materiais" className={`${classeAcaoPrimaria} mt-3.5`}>
              Gerenciar materiais
            </Link>
          </Cartao>
        </div>

        <div className="flex min-w-0 flex-col gap-5">
          <Cartao titulo="Para corrigir">
            <ListaComContador
              erro={atividades.erro && "Não foi possível carregar."}
              vazio="Nada esperando correção."
              itens={paraCorrigir.slice(0, 5).map((atividade) => ({
                chave: atividade.id,
                numero: atividade.a_corrigir,
                titulo: atividade.titulo,
                detalhe: atividade.turma_nome,
                para: "/professor/atividades",
              }))}
            />
          </Cartao>

          <Cartao titulo="Mensagens">
            <ListaComContador
              erro={conversas.erro && "Não foi possível carregar."}
              vazio="Nenhuma mensagem nova."
              itens={naoLidas.slice(0, 4).map((conversa) => ({
                chave: `${conversa.turma_id}-${conversa.contraparte_email}`,
                numero: conversa.nao_lidas,
                titulo: conversa.titulo,
                detalhe: conversa.ultima_mensagem || conversa.subtitulo,
                para: "/professor/mensagens",
              }))}
            />
          </Cartao>

          <Cartao titulo="O que falta no material">
            <ListaComContador
              erro={lacunas.erro && "Não foi possível carregar."}
              vazio="Nenhuma dúvida sem resposta no material, por enquanto."
              itens={lacunasVigentes.slice(0, 4).map((l) => ({
                chave: `${l.disciplina}-${l.chave}`,
                numero: l.alunos,
                titulo: l.assunto,
                detalhe: `${l.disciplina}${l.o_que_falta.length ? ` · falta: ${l.o_que_falta[0]}` : ""}`,
                para: "/professor/lacunas",
              }))}
            />
          </Cartao>

          <MuralDeAvisos limite={3} />
        </div>
      </div>
    </>
  )
}

const classeAcaoPrimaria =
  "inline-flex w-full justify-center rounded-campo bg-primaria px-3.5 py-2.5 text-[13px] font-semibold text-white transition hover:bg-primaria-escura"

function hojePorExtenso() {
  const texto = new Date().toLocaleDateString("pt-BR", { weekday: "long", day: "2-digit", month: "long", year: "numeric" })
  return texto.charAt(0).toUpperCase() + texto.slice(1)
}

function CartaoDisciplina({ turma }) {
  const alunos = turma.total_alunos || 0
  const publicados = turma.materiais_publicados || 0

  return (
    <article className="rounded-cartao border border-borda p-4">
      <h3 className="text-[17px] font-bold text-navy-900">{turma.nome}</h3>
      <span className="mt-1 inline-block rounded-campo bg-fundo px-2 py-0.5 text-xs font-semibold text-texto-secundario">
        {turma.semestre}
      </span>
      <p className="mt-3 mb-3.5 text-[13px] text-texto-secundario">
        {alunos} aluno{alunos === 1 ? "" : "s"} · {publicados} materia{publicados === 1 ? "l" : "is"}
      </p>
      <Link to={`/professor/materiais?turma=${turma.id}`} className={classeAcaoPrimaria}>
        Ver materiais
      </Link>
    </article>
  )
}

function MateriaisRecentes({ materiais }) {
  if (!materiais.length) {
    return <p className="py-3.5 text-[13px] text-texto-secundario">Você ainda não publicou nenhum material.</p>
  }

  return (
    <ul>
      {materiais.map((material) => {
        const status = STATUS_DO_MATERIAL[material.status] || { rotulo: material.status, tom: "neutro" }
        return (
          <li key={material.id} className="flex items-start gap-2.5 border-b border-borda py-2.5 last:border-b-0">
            <Selo tom={status.tom}>{status.rotulo}</Selo>
            <div className="flex min-w-0 flex-col gap-0.5">
              <strong className="text-[13.5px] leading-snug font-semibold text-texto">{material.titulo}</strong>
              <span className="text-xs text-texto-secundario">
                {[ROTULOS_TIPO_MATERIAL[material.tipo] || material.tipo, material.turma_nome, dataCurta(material.criado_em)]
                  .filter(Boolean)
                  .join(" · ")}
              </span>
            </div>
          </li>
        )
      })}
    </ul>
  )
}
