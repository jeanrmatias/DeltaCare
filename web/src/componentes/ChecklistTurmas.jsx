/**
 * Marcar em quais disciplinas publicar. Publicar o mesmo material (ou
 * atividade, ou aviso) em várias de uma vez evita repetir o envio uma a uma.
 *
 * Controlado: `marcadas` é a lista de ids e `aoMudar` recebe a nova lista.
 */
export function ChecklistTurmas({ turmas, marcadas, aoMudar, rotulo = "Publicar nas disciplinas", acao = "publicado" }) {
  const todas = turmas.length > 0 && marcadas.length === turmas.length

  function alternar(id) {
    aoMudar(marcadas.includes(id) ? marcadas.filter((m) => m !== id) : [...marcadas, id])
  }

  const dica = marcadas.length === 0 ? "Nenhuma disciplina marcada."
    : marcadas.length === 1 ? "Vai para 1 disciplina." : `Será ${acao} em ${marcadas.length} disciplinas.`

  return (
    <fieldset>
      <legend className="mb-1.5 text-[14px] font-medium text-texto">{rotulo}</legend>
      {turmas.length === 0 ? <p className="text-sm text-texto-secundario">Você ainda não tem disciplinas atribuídas.</p> : (
        <div className="flex flex-col gap-1.5 rounded-campo border border-borda p-3">
          {turmas.length > 1 && (
            <label className="flex items-center gap-2 border-b border-borda pb-1.5 text-sm font-semibold text-texto">
              <input type="checkbox" checked={todas} onChange={() => aoMudar(todas ? [] : turmas.map((t) => t.id))}
                ref={(caixa) => { if (caixa) caixa.indeterminate = marcadas.length > 0 && !todas }} className="size-4 accent-primaria" />
              Selecionar todas
            </label>
          )}
          {turmas.map((turma) => (
            <label key={turma.id} className="flex items-center gap-2 text-sm text-texto">
              <input type="checkbox" checked={marcadas.includes(turma.id)} onChange={() => alternar(turma.id)} className="size-4 accent-primaria" />
              {turma.nome} · {turma.semestre}
            </label>
          ))}
        </div>
      )}
      <span className="mt-1 block text-xs text-texto-secundario">{dica}</span>
    </fieldset>
  )
}
