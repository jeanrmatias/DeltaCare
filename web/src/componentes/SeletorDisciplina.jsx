/**
 * Escolha de disciplina, para o aluno.
 *
 * O professor vai no rótulo: uma mesma turma de alunos cursa várias
 * disciplinas, e "nome · semestre" sozinho podia deixar duas opções iguais na
 * lista. As de semestres anteriores ficam num grupo à parte — continuam
 * escolhíveis (revisar para a residência é justamente isso), mas não se
 * misturam com as de agora.
 *
 * `comTodas` acrescenta a opção "Todas as disciplinas" (valor vazio).
 */
export function SeletorDisciplina({ turmas, valor, aoMudar, comTodas = false }) {
  const atuais = turmas.filter((t) => t.vigente !== false)
  const anteriores = turmas.filter((t) => t.vigente === false)

  return (
    <select
      aria-label="Disciplina"
      value={valor ?? ""}
      onChange={(evento) => aoMudar(evento.target.value ? Number(evento.target.value) : null)}
      className="max-w-full rounded-campo border border-borda bg-superficie px-3 py-2.5 text-sm text-texto outline-none focus:border-primaria"
    >
      {comTodas && <option value="">Todas as disciplinas</option>}
      {atuais.map((turma) => <Opcao key={turma.id} turma={turma} />)}
      {anteriores.length > 0 && (
        <optgroup label="Semestres anteriores">
          {anteriores.map((turma) => <Opcao key={turma.id} turma={turma} />)}
        </optgroup>
      )}
    </select>
  )
}

function Opcao({ turma }) {
  const professor = turma.professor_nome ? ` · Prof. ${turma.professor_nome}` : ""
  return <option value={turma.id}>{`${turma.nome} · ${turma.semestre}${professor}`}</option>
}
