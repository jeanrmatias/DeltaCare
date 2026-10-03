import { useEffect } from "react"

/**
 * Põe o nome da página na aba do navegador: "Materiais · Delta Care".
 *
 * Numa aplicação de página única a troca de tela não recarrega nada, e o
 * título ficaria "Delta Care" para sempre. É o título que o leitor de tela
 * anuncia ao trocar de aba, e o que diferencia três abas abertas.
 */
export function useTituloDaPagina(titulo) {
  useEffect(() => {
    document.title = titulo ? `${titulo} · Delta Care` : "Delta Care"
  }, [titulo])
}
