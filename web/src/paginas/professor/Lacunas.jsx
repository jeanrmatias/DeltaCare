import { useState } from "react"
import { Link } from "react-router"

import { Botao } from "../../componentes/Botao"
import { Carregando, Cartao, EstadoVazio } from "../../componentes/Cartao"
import { Selo } from "../../componentes/Selo"
import { useApi } from "../../hooks/useApi"
import { useDialogo } from "../../hooks/useDialogo"
import { Cabecalho } from "../../layout/Painel"
import { api, ERRO_DE_CONEXAO } from "../../lib/api"
import { dataComAno } from "../../lib/formatos"

/**
 * Lacunas do material: o que os alunos perguntam ao assistente e o material
 * do professor não responde. O assistente não pode completar a lacuna — ele
 * só responde a partir do material —, mas o professor pode.
 *
 * Sem o nome de quem perguntou e sem o texto da pergunta: só o assunto, em
 * poucas palavras, e quantos alunos. E só aparece assunto de pelo menos dois
 * alunos — com um, daria para saber quem foi (regras/lacunas.py).
 */
export function Lacunas() {
  const { dados, carregando, erro, recarregar } = useApi("/lacunas")
  const [escolhida, setEscolhida] = useState(null)
  const disciplinas = dados?.disciplinas || []
  const disciplina = disciplinas.find((d) => d.id === escolhida) ?? disciplinas[0]

  return (
    <>
      <Cabecalho titulo="Lacunas do material"
        descricao="O que os alunos perguntam ao assistente e o seu material não responde — sem o nome nem o texto da pergunta.">
        {disciplinas.length > 1 && (
          <select aria-label="Disciplina" value={disciplina?.id ?? ""} onChange={(e) => setEscolhida(Number(e.target.value))}
            className="rounded-campo border border-borda bg-superficie px-3 py-2.5 text-sm outline-none focus:border-primaria">
            {disciplinas.map((d) => <option key={d.id} value={d.id}>{d.nome} · {d.semestre}</option>)}
          </select>
        )}
      </Cabecalho>

      {carregando && <Carregando />}
      {erro && <EstadoVazio>{erro}</EstadoVazio>}
      {dados?.sucesso && !disciplinas.length && <EstadoVazio>Você ainda não tem disciplinas atribuídas.</EstadoVazio>}

      {disciplina && (
        <div className="flex max-w-3xl flex-col gap-4">
          {disciplina.sem_material.perguntas > 0 && (
            <div className="rounded-cartao border-l-3 border-alerta bg-alerta-fundo px-5 py-4 text-sm text-texto">
              <strong>{disciplina.sem_material.perguntas} pergunta(s) de {disciplina.sem_material.alunos} aluno(s) chegaram sem nenhum PDF nesta disciplina.</strong>
              <p className="mt-1">O assistente só lê PDF — links e vídeos ele não lê. Sem PDF publicado, ele não tem como responder nada.</p>
              <Link to={`/professor/materiais?turma=${disciplina.id}`} className="mt-2 inline-block font-semibold text-primaria hover:underline">Publicar material</Link>
            </div>
          )}

          {disciplina.lacunas.length === 0 && (
            <EstadoVazio>
              Nenhuma lacuna nesta disciplina por enquanto.
              {disciplina.ocultas > 0 && ` ${disciplina.ocultas} assunto(s) de um aluno só não aparecem, para proteger quem perguntou.`}
            </EstadoVazio>
          )}

          {disciplina.lacunas.map((lacuna) => (
            <ItemLacuna key={lacuna.chave} lacuna={lacuna} disciplina={disciplina} tipos={dados.tipos} aoTratar={recarregar} />
          ))}

          {disciplina.lacunas.length > 0 && disciplina.ocultas > 0 && (
            <p className="text-[13px] text-texto-secundario">
              Mais {disciplina.ocultas} assunto(s) perguntados por um aluno só não aparecem, para proteger quem perguntou.
            </p>
          )}

          <Cartao titulo="Como funciona">
            <ul className="list-disc space-y-1.5 pl-5 text-[13px] leading-relaxed text-texto-secundario">
              <li>A cada pergunta, o assistente diz se o material respondeu por inteiro, em parte ou nada, e resume o assunto em poucas palavras.</li>
              <li>Aqui entram as que o material respondeu em parte ou não respondeu, agrupadas por assunto.</li>
              <li>Você nunca vê o texto da pergunta nem quem perguntou. Um assunto só aparece quando pelo menos {dados.min_alunos} alunos diferentes perguntaram.</li>
              <li>Depois de publicar material sobre o assunto, marque "Já tratei": ele sai da lista e só volta se alguém perguntar de novo.</li>
            </ul>
          </Cartao>
        </div>
      )}
    </>
  )
}

function ItemLacuna({ lacuna, disciplina, tipos, aoTratar }) {
  const { avisar } = useDialogo()

  async function tratar() {
    try {
      const resultado = await (await api("/lacunas/tratadas", { method: "POST", body: JSON.stringify({ turma_id: disciplina.id, assunto: lacuna.assunto }) })).json()
      await avisar(resultado.mensagem, resultado.sucesso ? "Pronto" : "Algo deu errado")
      aoTratar()
    } catch (erro) {
      console.error("Erro ao marcar como tratada:", erro)
      await avisar(ERRO_DE_CONEXAO, "Algo deu errado")
    }
  }

  return (
    <article className="flex flex-col gap-3 rounded-cartao bg-superficie p-5 shadow-cartao md:flex-row md:items-start md:justify-between">
      <div className="min-w-0">
        <div className="mb-1.5 flex flex-wrap items-center gap-2">
          <Selo tom={lacuna.tipo === "parcial" ? "alerta" : "perigo"}>{tipos[lacuna.tipo]}</Selo>
        </div>
        <h3 className="text-base font-bold text-navy-900">{lacuna.assunto}</h3>
        <p className="mt-1 text-[13px] text-texto-secundario">
          {lacuna.alunos} alunos · {lacuna.perguntas} pergunta(s) · a última em {dataComAno(lacuna.ultima_em)}
        </p>
        {lacuna.o_que_falta.length > 0 && (
          <p className="mt-1.5 text-sm text-texto"><strong>O que falta:</strong> {lacuna.o_que_falta.join("; ")}</p>
        )}
      </div>
      <div className="flex shrink-0 flex-wrap gap-2">
        <Link to={`/professor/materiais?turma=${disciplina.id}`}
          className="rounded-campo border border-primaria bg-primaria px-3.5 py-2 text-[13px] font-semibold text-white hover:bg-primaria-escura">
          Publicar material
        </Link>
        <Botao variante="neutra" pequeno onClick={tratar}>Já tratei</Botao>
      </div>
    </article>
  )
}
