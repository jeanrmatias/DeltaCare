import { useId } from "react"

/**
 * Campo de formulário com rótulo. **Controlado:** o valor mora no estado de
 * quem usa (`valor` + `aoMudar`), e não no próprio input — é assim que o
 * React sabe o que está digitado sem ir buscar no DOM.
 */
export function CampoTexto({
  rotulo,
  valor,
  aoMudar,
  tipo = "text",
  placeholder,
  autoComplete,
  obrigatorio = false,
  minimo,
  maximo,
  modoTeclado,
}) {
  // useId liga o <label> ao <input> sem inventar id à mão — dois campos
  // iguais na mesma tela não colidem.
  const id = useId()

  return (
    <div>
      <label htmlFor={id} className="mt-5 mb-2 block text-[13px] font-medium text-texto">
        {rotulo}
      </label>
      <input
        id={id}
        type={tipo}
        value={valor}
        onChange={(evento) => aoMudar(evento.target.value)}
        placeholder={placeholder}
        autoComplete={autoComplete}
        required={obrigatorio}
        minLength={minimo}
        maxLength={maximo}
        inputMode={modoTeclado}
        className="w-full rounded-campo border border-borda-campo bg-white px-3.5 py-3 text-sm text-texto outline-none transition placeholder:text-texto-secundario focus:border-primaria focus:ring-3 focus:ring-primaria/12"
      />
    </div>
  )
}
