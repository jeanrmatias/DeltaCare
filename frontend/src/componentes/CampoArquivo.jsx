/**
 * Campo de arquivo: o nome escolhido à esquerda e o botão "Selecionar" à
 * direita. Substitui o "Escolher ficheiro / Nenhum ficheiro selecionado" do
 * navegador, que muda de texto e de cara conforme o sistema de quem abre.
 *
 * O <input type="file"> continua lá, só escondido (sr-only, não display:none):
 * é ele que recebe o foco do teclado e o que o leitor de tela anuncia. O
 * rótulo inteiro envolve a caixa, então clicar em qualquer ponto abre a
 * escolha do arquivo.
 *
 * `aoMudar` recebe o evento, e não o arquivo: quem recusa um arquivo grande
 * demais precisa limpar `evento.target.value`.
 */
export function CampoArquivo({ rotulo, nome, aceitos, dica, aoMudar, obrigatorio = false }) {
  return (
    <label className="flex flex-col gap-1.5 text-[14px] font-medium text-texto">
      {rotulo}
      <span className="flex items-center justify-between gap-3 rounded-campo border border-borda-campo bg-superficie py-1.5 pr-1.5 pl-3 has-[:focus-visible]:border-primaria has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-primaria/30">
        <span aria-hidden="true" className={`min-w-0 truncate text-sm font-normal ${nome ? "text-texto" : "text-texto-secundario"}`}>
          {nome || "Nenhum arquivo selecionado"}
        </span>
        <span aria-hidden="true"
          className="shrink-0 cursor-pointer rounded-campo border border-borda bg-fundo px-3.5 py-1.5 text-[14px] font-semibold text-texto hover:border-primaria hover:text-primaria">
          Selecionar
        </span>
        <input type="file" accept={aceitos} onChange={aoMudar} required={obrigatorio} className="sr-only" />
      </span>
      {dica && <span className="text-xs font-normal text-texto-secundario">{dica}</span>}
    </label>
  )
}
