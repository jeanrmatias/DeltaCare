/**
 * O montador de questões do quiz. A resposta certa é guardada pela posição da
 * alternativa — então toda mudança na lista precisa mover a marcação junto.
 */

/**
 * Tira a alternativa `posicao` e mantém marcada a mesma alternativa de antes.
 *
 * Antes, a marcação ficava no mesmo número: com a C marcada (2), remover a A
 * deixava [B, C] com o 2 apontando para fora da lista — e o código o jogava
 * para a B. A resposta certa mudava sozinha. Se a removida era a marcada, a
 * questão fica sem marcação (null), à vista; salvar assim é recusado.
 */
export function removerAlternativa(questao, posicao) {
  const alternativas = questao.alternativas.filter((_, p) => p !== posicao)
  let correta = questao.correta
  if (correta === posicao) correta = null
  else if (correta !== null && correta > posicao) correta -= 1
  return { ...questao, alternativas, correta }
}

/**
 * A questão como vai para o servidor. As alternativas em branco vão junto, na
 * posição em que estão: é o servidor que as tira e acerta o índice da correta
 * (regras/atividades._alternativas_e_correta). Filtrar aqui, sem acertar o
 * índice, deslocava o gabarito.
 */
export function questaoParaEnvio(questao) {
  return {
    enunciado: questao.enunciado.trim(),
    alternativas: questao.alternativas.map((a) => a.trim()),
    correta: questao.correta,
  }
}
