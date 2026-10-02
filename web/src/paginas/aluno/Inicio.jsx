import { Link } from "react-router"

import { Carregando, Cartao, EstadoVazio, Numero, Numeros } from "../../componentes/Cartao"
import { MuralDeAvisos } from "../../componentes/MuralDeAvisos"
import { useApi } from "../../hooks/useApi"
import { useSessao } from "../../hooks/useSessao"
import { Cabecalho } from "../../layout/Painel"
import { contagemDeMateriais, dataCurta, ROTULOS_TIPO_MATERIAL } from "../../lib/formatos"
import { nomeExibicao } from "../../lib/usuario"
import { CartaoProgresso } from "./CartaoProgresso"

/**
 * Tela inicial do aluno. Tudo vem de `/aluno/resumo`: números, progresso,
 * disciplinas e materiais recentes. Sem dado, estado vazio — nada inventado.
 */
export function InicioAluno() {
  const { usuario } = useSessao()
  const { dados, carregando, erro } = useApi("/aluno/resumo")

  return (
    <>
      <Cabecalho
        titulo={`Olá, ${nomeExibicao(usuario)}`}
        descricao="Seu painel de estudos — disciplinas, materiais liberados e o assistente de dúvidas."
      />

      {carregando && <Carregando />}
      {erro && <EstadoVazio>{erro}</EstadoVazio>}

      {dados?.sucesso && (
        <>
          <Numeros>
            <Numero rotulo="Disciplinas cursando" valor={dados.total_turmas} />
            <Numero rotulo="Materiais disponíveis" valor={dados.total_materiais} />
            <Numero rotulo="Perguntas ao assistente" valor={dados.perguntas_feitas} />
          </Numeros>

          {dados.turmas.length === 0 ? (
            <EstadoVazio>Você ainda não está matriculado em nenhuma disciplina. Fale com a administração.</EstadoVazio>
          ) : (
            <>
              {dados.progresso && <CartaoProgresso progresso={dados.progresso} />}
              <MuralDeAvisos />

              <div className="grid gap-5 min-[1101px]:grid-cols-[1fr_380px]">
                <MinhasDisciplinas turmas={dados.turmas} />
                <div className="flex min-w-0 flex-col gap-5">
                  <MateriaisRecentes materiais={dados.materiais_recentes || []} />
                  <ConviteAoChat />
                </div>
              </div>
            </>
          )}
        </>
      )}
    </>
  )
}

const classeDeAcao =
  "inline-flex w-full justify-center rounded-campo bg-primaria px-3.5 py-2.5 text-[13px] font-semibold text-white transition hover:bg-primaria-escura"

function MinhasDisciplinas({ turmas }) {
  return (
    <Cartao titulo="Minhas disciplinas" className="min-w-0 self-start">
      <div className="grid grid-cols-[repeat(auto-fill,minmax(190px,1fr))] gap-4">
        {turmas.map((turma) => (
          <article key={turma.id} className="rounded-cartao border border-borda p-4">
            <h3 className="text-[17px] font-bold text-navy-900">{turma.nome}</h3>
            <span className="mt-1 inline-block rounded-campo bg-fundo px-2 py-0.5 text-xs font-semibold text-texto-secundario">
              {turma.semestre}
            </span>
            <p className="mt-3 mb-3.5 text-[13px] text-texto-secundario">{contagemDeMateriais(turma.total_materiais)}</p>
            <Link to={`/aluno/materiais?turma=${turma.id}`} className={classeDeAcao}>
              Ver materiais
            </Link>
          </article>
        ))}
      </div>
    </Cartao>
  )
}

function MateriaisRecentes({ materiais }) {
  return (
    <Cartao titulo="Materiais recentes">
      {materiais.length === 0 ? (
        <p className="py-3.5 text-[13px] text-texto-secundario">Nenhum material liberado ainda.</p>
      ) : (
        <ul>
          {materiais.map((material, indice) => (
            <li key={material.id ?? indice} className="flex items-start gap-2.5 border-b border-borda py-2.5 last:border-b-0">
              <span className="rounded-campo bg-fundo px-2 py-0.5 text-[11px] font-bold tracking-wide text-texto-secundario uppercase">
                {ROTULOS_TIPO_MATERIAL[material.tipo] || material.tipo}
              </span>
              <div className="flex min-w-0 flex-col gap-0.5">
                <strong className="text-[13.5px] leading-snug font-semibold text-texto">{material.titulo}</strong>
                <span className="text-xs text-texto-secundario">
                  {[material.turma_nome, dataCurta(material.criado_em)].filter(Boolean).join(" · ")}
                </span>
              </div>
            </li>
          ))}
        </ul>
      )}
      <Link to="/aluno/materiais" className={`${classeDeAcao} mt-3.5`}>
        Ver todos os materiais
      </Link>
    </Cartao>
  )
}

function ConviteAoChat() {
  return (
    <Cartao titulo="Ficou com dúvida?">
      <p className="text-[13px] leading-relaxed text-texto-secundario">
        O assistente responde com base apenas no material que o seu professor liberou — sem inventar o que não
        está lá.
      </p>
      <Link to="/aluno/chat" className={`${classeDeAcao} mt-3.5`}>
        Abrir o chat de estudos
      </Link>
    </Cartao>
  )
}
