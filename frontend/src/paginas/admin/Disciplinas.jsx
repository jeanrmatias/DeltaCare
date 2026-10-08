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
 * Disciplinas na visão da administração. Cada disciplina tem um professor e
 * o seu próprio material — é o que mantém o assistente de IA buscando no
 * material certo. Apontada para uma turma, os alunos dela entram
 * matriculados na hora, menos os marcados como exceção.
 */
export function DisciplinasAdmin() {
  const professores = useApi("/admin/professores")
  const disciplinas = useApi("/admin/turmas")
  const coortes = useApi("/admin/coortes")
  const [formulario, setFormulario] = useState(false)
  const [abertas, setAbertas] = useState(() => new Set())
  const [trocando, setTrocando] = useState(null)
  const { confirmar, avisar } = useDialogo()
  const lista = disciplinas.dados?.turmas || []
  const semProfessor = professores.dados && !(professores.dados.professores || []).length

  async function excluir(turma) {
    const sim = await confirmar(
      `Excluir a disciplina "${turma.nome} · ${turma.semestre}" de ${turma.professor_email}?\n\n` +
      "Saem junto os materiais, as atividades, as entregas com as notas, as mensagens e o histórico do chat. Não há como desfazer.\n\n" +
      "Se o semestre dela só terminou, não precisa excluir: ao virar o semestre, ela vai sozinha para o histórico, com tudo preservado.",
      { titulo: "Excluir disciplina", rotulo: "Excluir", perigo: true })
    if (!sim) return
    try {
      const resultado = await (await api(`/admin/turmas/${turma.id}`, { method: "DELETE" })).json()
      if (!resultado.sucesso) await avisar(resultado.mensagem, "Algo deu errado")
      disciplinas.recarregar()
    } catch (erro) {
      console.error("Erro ao excluir disciplina:", erro)
      await avisar(ERRO_DE_CONEXAO, "Algo deu errado")
    }
  }

  function alternar(id) {
    setAbertas((atual) => {
      const nova = new Set(atual)
      if (nova.has(id)) nova.delete(id)
      else nova.add(id)
      return nova
    })
  }

  return (
    <>
      <Cabecalho titulo="Disciplinas" descricao="Cada disciplina tem um professor e o seu próprio material. Aponte para uma turma e os alunos dela já entram matriculados.">
        {!formulario && <Botao onClick={() => setFormulario(true)} desativado={semProfessor}>Nova disciplina</Botao>}
      </Cabecalho>

      {semProfessor && (
        <EstadoVazio>Ainda não há nenhum professor cadastrado. <Link to="/admin/usuarios" className="font-semibold text-primaria">Cadastre um professor</Link> antes de criar uma disciplina.</EstadoVazio>
      )}

      {formulario && (
        <NovaDisciplina professores={professores.dados?.professores || []} coortes={coortes.dados?.coortes || []}
          aoFechar={() => setFormulario(false)} aoCriar={() => { setFormulario(false); disciplinas.recarregar(); coortes.recarregar() }} />
      )}

      {disciplinas.carregando && <Carregando />}
      {disciplinas.erro && <EstadoVazio>{disciplinas.erro}</EstadoVazio>}
      {disciplinas.dados && !lista.length && <EstadoVazio>Nenhuma disciplina criada ainda. Clique em "Nova disciplina" para começar.</EstadoVazio>}

      <section className="flex flex-col gap-3">
        {lista.map((turma) => (
          <div key={turma.id} className="rounded-cartao bg-superficie shadow-cartao">
            {/* Lado a lado só com folga (lg): no tablet, três botões ao lado do nome passavam da tela. */}
            <article className="flex flex-col gap-3 p-5 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <h2 className="text-[17px] font-semibold text-navy-900">{turma.nome} · {turma.semestre}</h2>
                <p className="mt-1 text-[14px] text-texto-secundario">Professor: {turma.professor_email}</p>
                <p className="text-[14px] text-texto-secundario">{turma.total_materiais} material(is) cadastrado(s)</p>
              </div>
              <div className="flex shrink-0 flex-wrap gap-2">
                <Botao variante="neutra" pequeno onClick={() => setTrocando(trocando === turma.id ? null : turma.id)}>Trocar professor</Botao>
                <Botao variante="neutra" pequeno onClick={() => alternar(turma.id)}>{abertas.has(turma.id) ? "Fechar alunos" : "Alunos"}</Botao>
                <Botao variante="perigo" pequeno onClick={() => excluir(turma)}>Excluir</Botao>
              </div>
            </article>
            {trocando === turma.id && (
              <TrocarProfessor turma={turma} professores={(professores.dados?.professores || []).filter((e) => e !== turma.professor_email)}
                aoFechar={() => setTrocando(null)} aoTrocar={() => { setTrocando(null); disciplinas.recarregar() }} />
            )}
            {abertas.has(turma.id) && <AlunosDaDisciplina turma={turma} />}
          </div>
        ))}
      </section>
    </>
  )
}

function NovaDisciplina({ professores, coortes, aoFechar, aoCriar }) {
  const [campos, setCampos] = useState({ professor_email: professores[0] || "", coorte_id: "", nome: "", semestre: "" })
  const [mensagem, setMensagem] = useState("")
  const mudar = (nome) => (valor) => setCampos((atual) => ({ ...atual, [nome]: valor }))

  async function criar(evento) {
    evento.preventDefault()
    try {
      const resultado = await (await api("/admin/turmas", {
        method: "POST",
        body: JSON.stringify({ ...campos, nome: campos.nome.trim(), semestre: campos.semestre.trim(), coorte_id: campos.coorte_id ? Number(campos.coorte_id) : null }),
      })).json()
      if (!resultado.sucesso) return setMensagem(resultado.mensagem)
      aoCriar()
    } catch (erro) {
      console.error("Erro ao criar disciplina:", erro)
      setMensagem(ERRO_DE_CONEXAO)
    }
  }

  return (
    <Cartao titulo="Nova disciplina" className="mb-5">
      <p className="mb-4 text-[14px] text-texto-secundario">
        Uma entrada por disciplina, com o seu professor e o seu material. Escolhendo a turma, os alunos dela entram matriculados na hora,
        menos os que estiverem marcados como exceção.
      </p>
      <form onSubmit={criar} className="grid gap-4 sm:grid-cols-2">
        <Escolha rotulo="Professor" valor={campos.professor_email} aoMudar={mudar("professor_email")} opcoes={professores.map((e) => ({ valor: e, rotulo: e }))} />
        {/* "Nenhuma" é o padrão: escolher turma por acidente matricularia dezenas de alunos de uma vez. */}
        <Escolha rotulo="Turma" valor={campos.coorte_id} aoMudar={mudar("coorte_id")}
          opcoes={[{ valor: "", rotulo: "Nenhuma (disciplina solta)" }, ...coortes.map((c) => ({ valor: String(c.id), rotulo: `${c.nome} · ${c.semestre} · ${c.total_alunos} aluno(s)` }))]} />
        <Texto rotulo="Disciplina" valor={campos.nome} aoMudar={mudar("nome")} placeholder="ex.: Cardiologia I" obrigatorio />
        <Texto rotulo="Semestre" valor={campos.semestre} aoMudar={mudar("semestre")} placeholder="ex.: 2026/2" obrigatorio />
        <div className="flex gap-2.5 sm:col-span-2">
          <Botao tipo="submit">Criar disciplina</Botao>
          <Botao variante="neutra" onClick={aoFechar}>Cancelar</Botao>
        </div>
      </form>
      <MensagemDeFormulario texto={mensagem} />
    </Cartao>
  )
}

/**
 * Outro professor assume a disciplina (licença, saída, redistribuição). O
 * material e as atividades vão junto: quem assume precisa poder corrigir o
 * que já está publicado e lançar as notas que faltam.
 */
function TrocarProfessor({ turma, professores, aoFechar, aoTrocar }) {
  const [novo, setNovo] = useState(professores[0] || "")
  const [mensagem, setMensagem] = useState("")

  async function trocar(evento) {
    evento.preventDefault()
    try {
      const resultado = await (await api(`/admin/turmas/${turma.id}/professor`, { method: "PUT", body: JSON.stringify({ professor_email: novo }) })).json()
      if (!resultado.sucesso) return setMensagem(resultado.mensagem)
      aoTrocar()
    } catch (erro) {
      console.error("Erro ao trocar professor:", erro)
      setMensagem(ERRO_DE_CONEXAO)
    }
  }

  return (
    <form onSubmit={trocar} className="border-t border-borda px-5 py-4">
      <p className="mb-3 text-[14px] text-texto-secundario">
        Quem assume fica com o material e as atividades de {turma.nome}, inclusive as entregas por corrigir. {turma.professor_email} perde o acesso a ela.
      </p>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
        <Escolha rotulo="Novo professor" valor={novo} aoMudar={setNovo} className="flex-1"
          opcoes={professores.length ? professores.map((e) => ({ valor: e, rotulo: e })) : [{ valor: "", rotulo: "Nenhum outro professor ativo" }]} />
        <Botao tipo="submit" desativado={!novo}>Trocar</Botao>
        <Botao variante="neutra" onClick={aoFechar}>Cancelar</Botao>
      </div>
      <MensagemDeFormulario texto={mensagem} />
    </form>
  )
}

/** Matrícula direta na disciplina — para quem não está na turma (optativa, dependência). */
function AlunosDaDisciplina({ turma }) {
  const matriculados = useApi(`/admin/turmas/${turma.id}/alunos`)
  const todos = useApi("/admin/alunos")
  const [escolhido, setEscolhido] = useState("")
  const [mensagem, setMensagem] = useState({ texto: "", sucesso: false })
  const { confirmar, avisar } = useDialogo()
  const dentro = matriculados.dados?.alunos || []
  const disponiveis = (todos.dados?.alunos || []).filter((email) => !dentro.includes(email))

  async function matricular() {
    const aluno = escolhido || disponiveis[0]
    if (!aluno) return
    try {
      const resultado = await (await api("/admin/matriculas", { method: "POST", body: JSON.stringify({ aluno_email: aluno, turma_id: turma.id }) })).json()
      setMensagem({ texto: resultado.mensagem, sucesso: resultado.sucesso })
      if (resultado.sucesso) { setEscolhido(""); matriculados.recarregar() }
    } catch (erro) {
      console.error("Erro ao matricular:", erro)
      setMensagem({ texto: ERRO_DE_CONEXAO })
    }
  }

  async function remover(email) {
    if (!(await confirmar(`Remover ${email} da disciplina "${turma.nome}"?`, { titulo: "Remover matrícula", rotulo: "Remover", perigo: true }))) return
    try {
      const resultado = await (await api("/admin/matriculas", { method: "DELETE", body: JSON.stringify({ aluno_email: email, turma_id: turma.id }) })).json()
      if (!resultado.sucesso) await avisar(resultado.mensagem, "Algo deu errado")
      matriculados.recarregar()
    } catch (erro) {
      console.error("Erro ao remover matrícula:", erro)
      await avisar(ERRO_DE_CONEXAO, "Algo deu errado")
    }
  }

  return (
    <div className="border-t border-borda px-5 py-4">
      <h4 className="mb-3 text-sm font-semibold text-navy-900">Alunos matriculados · {turma.nome}</h4>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
        <Escolha rotulo="Matricular aluno" valor={escolhido || disponiveis[0] || ""} aoMudar={setEscolhido} className="flex-1"
          opcoes={disponiveis.length ? disponiveis.map((e) => ({ valor: e, rotulo: e })) : [{ valor: "", rotulo: "Nenhum aluno disponível" }]} />
        <Botao onClick={matricular} desativado={!disponiveis.length}>Matricular</Botao>
      </div>
      <MensagemDeFormulario texto={mensagem.texto} sucesso={mensagem.sucesso} />
      {matriculados.carregando && <Carregando />}
      <ul className="mt-3 flex flex-col gap-1.5">
        {matriculados.dados && !dentro.length && <li className="text-sm text-texto-secundario">Nenhum aluno matriculado ainda.</li>}
        {dentro.map((email) => (
          <li key={email} className="flex items-center justify-between gap-3 rounded-campo bg-fundo px-3 py-2 text-sm">
            <span className="truncate">{email}</span>
            <button type="button" onClick={() => remover(email)} className="shrink-0 text-xs font-semibold text-perigo hover:underline">Remover</button>
          </li>
        ))}
      </ul>
    </div>
  )
}
