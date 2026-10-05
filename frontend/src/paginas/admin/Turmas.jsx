import { useState } from "react"
import { Link } from "react-router"

import { Botao } from "../../componentes/Botao"
import { Carregando, Cartao, EstadoVazio } from "../../componentes/Cartao"
import { Escolha, MensagemDeFormulario, Texto } from "../../componentes/Campos"
import { useApi } from "../../hooks/useApi"
import { useDialogo } from "../../hooks/useDialogo"
import { Cabecalho } from "../../layout/Painel"
import { api, ERRO_DE_CONEXAO } from "../../lib/api"

/**
 * Turmas de alunos (MED 3A, o grupo que cursa junto), as exceções por
 * disciplina e o semestre vigente. A tela de Disciplinas cuida de Anatomia,
 * Fisiologia e de qual professor dá cada uma. (No banco a disciplina se chama
 * `turmas` e a turma, `coortes` — ver backend/regras/coortes.py.)
 *
 * A exceção é uma fileira de chips por aluno, um por disciplina: aceso =
 * cursa, apagado = está fora; um toque alterna. Uma matriz aluno × disciplina
 * não caberia no celular, e a secretaria mexe nisso do telefone também.
 */
const contar = (n, singular, plural) => `${n} ${n === 1 ? singular : plural}`

export function Turmas() {
  const coortes = useApi("/admin/coortes")
  const [formulario, setFormulario] = useState(false)
  const [aberta, setAberta] = useState(null)
  const { confirmar, avisar } = useDialogo()
  const lista = coortes.dados?.coortes || []

  async function desfazer(coorte) {
    const sim = await confirmar(`Desfazer a turma "${coorte.nome} · ${coorte.semestre}"?\n\n` +
      "As disciplinas e as matrículas continuam — o aluno cursou, e isso não deixa de ter acontecido. " +
      "Elas só voltam a ser disciplinas soltas, e matricular passa a ser uma por uma.",
    { titulo: "Desfazer turma", rotulo: "Desfazer", perigo: true })
    if (!sim) return
    try {
      const resultado = await (await api(`/admin/coortes/${coorte.id}`, { method: "DELETE" })).json()
      if (!resultado.sucesso) await avisar(resultado.mensagem, "Algo deu errado")
      coortes.recarregar()
    } catch (erro) {
      console.error("Erro ao desfazer turma:", erro)
      await avisar(ERRO_DE_CONEXAO, "Algo deu errado")
    }
  }

  return (
    <>
      <Cabecalho titulo="Turmas" descricao="O grupo de alunos que cursa junto. Quem entra na turma entra em todas as disciplinas dela, menos nas exceções.">
        {!formulario && <Botao onClick={() => setFormulario(true)}>Nova turma</Botao>}
      </Cabecalho>

      <div className="flex flex-col gap-5">
        <SemestreVigente />
        {formulario && <NovaTurma aoFechar={() => setFormulario(false)} aoCriar={() => { setFormulario(false); coortes.recarregar() }} />}

        {coortes.carregando && <Carregando />}
        {coortes.erro && <EstadoVazio>{coortes.erro}</EstadoVazio>}
        {coortes.dados && !lista.length && <EstadoVazio>Nenhuma turma criada ainda. Clique em "Nova turma" para começar.</EstadoVazio>}

        <section className="flex flex-col gap-3">
          {lista.map((coorte) => (
            <div key={coorte.id} className="rounded-cartao bg-superficie shadow-cartao">
              <article className="flex flex-col gap-3 p-5 md:flex-row md:items-start md:justify-between">
                <div>
                  <h3 className="text-[17px] font-semibold text-navy-900">{coorte.nome} · {coorte.semestre}</h3>
                  <p className="mt-1 text-[14px] text-texto-secundario">
                    {contar(coorte.total_alunos, "aluno", "alunos")} · {contar(coorte.total_disciplinas, "disciplina", "disciplinas")}
                  </p>
                </div>
                <div className="flex shrink-0 gap-2">
                  <Botao variante="neutra" pequeno onClick={() => setAberta(aberta === coorte.id ? null : coorte.id)}>{aberta === coorte.id ? "Fechar" : "Alunos"}</Botao>
                  <Botao variante="perigo" pequeno onClick={() => desfazer(coorte)}>Desfazer</Botao>
                </div>
              </article>
              {aberta === coorte.id && <PainelDaTurma coorte={coorte} aoMudar={coortes.recarregar} />}
            </div>
          ))}
        </section>
      </div>
    </>
  )
}

function SemestreVigente() {
  const { dados, recarregar } = useApi("/semestre")
  const [novo, setNovo] = useState("")
  const [mensagem, setMensagem] = useState({ texto: "", sucesso: false })
  const { confirmar } = useDialogo()

  async function virar(evento) {
    evento.preventDefault()
    const semestre = novo.trim()
    if (!semestre) return
    const sim = await confirmar(`Virar o semestre para ${semestre}?\n\n` +
      "As disciplinas do semestre atual saem da tela inicial dos alunos e vão para Semestres anteriores, com material, notas e conversas preservados. " +
      "O nível e a faixa dos alunos recomeçam no semestre novo; o XP acumulado continua aparecendo.\n\nDá para voltar atrás virando de novo.",
    { titulo: "Virar semestre", rotulo: "Virar" })
    if (!sim) return
    try {
      const resultado = await (await api("/admin/semestre", { method: "PUT", body: JSON.stringify({ semestre }) })).json()
      setMensagem({ texto: resultado.mensagem, sucesso: resultado.sucesso })
      if (resultado.sucesso) { setNovo(""); recarregar() }
    } catch (erro) {
      console.error("Erro ao virar o semestre:", erro)
      setMensagem({ texto: ERRO_DE_CONEXAO })
    }
  }

  return (
    <Cartao titulo="Semestre vigente">
      <p className="font-numero text-[28px] font-semibold text-navy-900">{dados?.semestre ?? "—"}</p>
      <p className="mt-1 text-[14px] text-texto-secundario">
        {dados?.definido_pela_administracao ? "Definido pela administração." : "Pelo calendário (jan–jun é o 1º, jul–dez o 2º). Vira sozinho se ninguém definir."}
      </p>
      <form onSubmit={virar} className="mt-4 flex flex-col gap-2 sm:flex-row sm:items-end">
        <Texto rotulo="Virar para" valor={novo} aoMudar={setNovo} placeholder="ex.: 2027/1" className="sm:w-48" />
        <Botao tipo="submit" variante="neutra">Virar semestre</Botao>
      </form>
      <MensagemDeFormulario texto={mensagem.texto} sucesso={mensagem.sucesso} />
    </Cartao>
  )
}

function NovaTurma({ aoFechar, aoCriar }) {
  const [nome, setNome] = useState("")
  const [semestre, setSemestre] = useState("")
  const [mensagem, setMensagem] = useState("")

  async function criar(evento) {
    evento.preventDefault()
    try {
      const resultado = await (await api("/admin/coortes", { method: "POST", body: JSON.stringify({ nome: nome.trim(), semestre: semestre.trim() }) })).json()
      if (!resultado.sucesso) return setMensagem(resultado.mensagem)
      aoCriar()
    } catch (erro) {
      console.error("Erro ao criar turma:", erro)
      setMensagem(ERRO_DE_CONEXAO)
    }
  }

  return (
    <Cartao titulo="Nova turma">
      <form onSubmit={criar} className="grid gap-4 sm:grid-cols-2">
        <Texto rotulo="Nome" valor={nome} aoMudar={setNome} placeholder="ex.: MED 3A" obrigatorio />
        <Texto rotulo="Semestre" valor={semestre} aoMudar={setSemestre} placeholder="ex.: 2026/2" obrigatorio />
        <div className="flex gap-2.5 sm:col-span-2">
          <Botao tipo="submit">Criar turma</Botao>
          <Botao variante="neutra" onClick={aoFechar}>Cancelar</Botao>
        </div>
      </form>
      <MensagemDeFormulario texto={mensagem} />
    </Cartao>
  )
}

function PainelDaTurma({ coorte, aoMudar }) {
  const alunos = useApi(`/admin/coortes/${coorte.id}/alunos`)
  const disciplinas = useApi(`/admin/coortes/${coorte.id}/disciplinas`)
  const todos = useApi("/admin/alunos")
  const [escolhido, setEscolhido] = useState("")
  const [mensagem, setMensagem] = useState({ texto: "", sucesso: false })
  const { confirmar, avisar } = useDialogo()

  const naTurma = alunos.dados?.alunos || []
  const listaDisciplinas = disciplinas.dados?.disciplinas || []
  const jaEstao = new Set(naTurma.map((a) => a.email))
  const disponiveis = (todos.dados?.alunos || []).filter((email) => !jaEstao.has(email))

  async function chamar(caminho, opcoes) {
    try {
      const resultado = await (await api(caminho, opcoes)).json()
      setMensagem({ texto: resultado.mensagem, sucesso: resultado.sucesso })
      if (resultado.sucesso) { alunos.recarregar(); aoMudar() }
      return resultado.sucesso
    } catch (erro) {
      console.error("Erro na turma:", erro)
      setMensagem({ texto: ERRO_DE_CONEXAO })
      return false
    }
  }

  async function adicionar() {
    const aluno = escolhido || disponiveis[0]
    if (aluno && await chamar(`/admin/coortes/${coorte.id}/alunos`, { method: "POST", body: JSON.stringify({ aluno_email: aluno }) })) setEscolhido("")
  }

  async function remover(aluno) {
    if (!(await confirmar(`Remover ${aluno.nome} da turma "${coorte.nome}"?\n\nSai também de todas as disciplinas dela, e perde o acesso ao material.`,
      { titulo: "Remover da turma", rotulo: "Remover", perigo: true }))) return
    if (!(await chamar(`/admin/coortes/${coorte.id}/alunos`, { method: "DELETE", body: JSON.stringify({ aluno_email: aluno.email }) }))) {
      await avisar(mensagem.texto || "Não foi possível remover.", "Algo deu errado")
    }
  }

  // Sem confirmação de propósito: é reversível no mesmo toque, e um diálogo a
  // cada chip tornaria insuportável ajustar a grade de uma turma inteira.
  const alternar = (aluno, disciplina, estaFora) =>
    chamar("/admin/excecoes", { method: estaFora ? "DELETE" : "POST", body: JSON.stringify({ aluno_email: aluno.email, turma_id: disciplina.id }) })

  return (
    <div className="border-t border-borda px-5 py-4">
      <h4 className="mb-1 text-sm font-semibold text-navy-900">{coorte.nome} · alunos e disciplinas</h4>
      <p className="mb-3 text-[14px] text-texto-secundario">
        {disciplinas.dados && !listaDisciplinas.length
          ? <>Esta turma ainda não tem disciplinas. Crie uma em <Link to="/admin/disciplinas" className="font-semibold text-primaria">Disciplinas</Link> apontando para esta turma — os alunos que já estiverem aqui entram nela automaticamente.</>
          : `Disciplinas: ${listaDisciplinas.map((d) => `${d.nome} (Prof. ${d.professor_nome})`).join(", ")}`}
      </p>

      <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
        <Escolha rotulo="Adicionar aluno à turma" valor={escolhido || disponiveis[0] || ""} aoMudar={setEscolhido} className="flex-1"
          opcoes={disponiveis.length ? disponiveis.map((e) => ({ valor: e, rotulo: e })) : [{ valor: "", rotulo: "Nenhum aluno disponível" }]} />
        <Botao onClick={adicionar} desativado={!disponiveis.length}>Adicionar</Botao>
      </div>
      <MensagemDeFormulario texto={mensagem.texto} sucesso={mensagem.sucesso} />

      {alunos.carregando && <Carregando />}
      <ul className="mt-3 flex flex-col gap-2">
        {alunos.dados && !naTurma.length && <li className="text-sm text-texto-secundario">Nenhum aluno nesta turma ainda.</li>}
        {naTurma.map((aluno) => {
          const fora = new Set(aluno.fora_de.map((d) => d.turma_id))
          return (
            <li key={aluno.email} className="flex flex-col gap-2 rounded-bloco bg-fundo p-3 sm:flex-row sm:items-start sm:justify-between">
              <div className="min-w-0">
                <strong className="block text-sm text-texto">{aluno.nome}</strong>
                {aluno.email !== aluno.nome && <span className="block text-xs text-texto-secundario">{aluno.email}</span>}
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {listaDisciplinas.map((disciplina) => {
                    const estaFora = fora.has(disciplina.id)
                    return (
                      <button key={disciplina.id} type="button" aria-pressed={!estaFora} onClick={() => alternar(aluno, disciplina, estaFora)}
                        title={estaFora ? `${aluno.nome} está fora de ${disciplina.nome}. Clique para devolver.` : `${aluno.nome} cursa ${disciplina.nome}. Clique para tirar.`}
                        className={`rounded-full border px-2.5 py-1 text-xs font-semibold transition ${estaFora
                          ? "border-dashed border-borda bg-superficie text-texto-secundario line-through" : "border-primaria bg-primaria text-white"}`}>
                        {disciplina.nome}
                      </button>
                    )
                  })}
                </div>
              </div>
              <button type="button" onClick={() => remover(aluno)} className="shrink-0 text-xs font-semibold text-perigo hover:underline">Remover da turma</button>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
