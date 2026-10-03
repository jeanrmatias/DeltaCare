/**
 * O relatório mensal em CSV, para abrir no Excel ou na planilha da
 * coordenação. Ponto e vírgula e vírgula decimal: é o que o Excel em
 * português espera — com vírgula como separador, ele junta tudo numa coluna.
 */

const COLUNAS = [
  "Mês", "Disciplina", "Aproveitamento (%)", "Notas corrigidas",
  "Entregas no prazo", "Entregas atrasadas", "Não entregues",
  "Alunos ativos", "Alunos", "Dias de estudo por aluno ativo", "Materiais abertos", "XP médio por aluno",
  "Perguntas ao assistente", "Respostas completas", "Respostas parciais", "Sem resposta no material", "Disciplina sem PDF",
]

function celula(valor) {
  if (valor === null || valor === undefined) return ""
  const texto = typeof valor === "number" ? String(valor).replace(".", ",") : String(valor)
  return /[;"\n]/.test(texto) ? `"${texto.replace(/"/g, '""')}"` : texto
}

function linha(mes, nome, bloco) {
  const { notas, entregas, engajamento, chat } = bloco
  return [
    mes, nome, notas.aproveitamento, notas.corrigidas,
    entregas.no_prazo, entregas.atrasadas, entregas.nao_entregues,
    engajamento.alunos_ativos, engajamento.alunos, engajamento.dias_de_estudo_por_aluno, engajamento.materiais_abertos, engajamento.xp_medio,
    chat.perguntas, chat.completa, chat.parcial, chat.nenhuma, chat.sem_material,
  ].map(celula).join(";")
}

export function csvDoRelatorio(relatorio) {
  const linhas = [COLUNAS.join(";")]
  for (const mes of relatorio.meses) {
    linhas.push(linha(mes.rotulo, `Total da turma ${relatorio.turma.nome}`, mes.total))
    for (const disciplina of mes.disciplinas) linhas.push(linha(mes.rotulo, disciplina.nome, disciplina))
  }
  // O BOM faz o Excel ler os acentos em UTF-8.
  return "﻿" + linhas.join("\r\n") + "\r\n"
}

/** "MED 3A · 2026/2" → "relatorio-med-3a-2026-2.csv" */
export function nomeDoCsv(turma) {
  const base = `${turma.nome} ${turma.semestre}`.normalize("NFD").replace(/[̀-ͯ]/g, "")
  return `relatorio-${base.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")}.csv`
}
