import { useState } from "react"

import { Carregando, EstadoVazio } from "../../componentes/Cartao"
import { ListaDeMateriais } from "../../componentes/ListaDeMateriais"
import { useApi } from "../../hooks/useApi"
import { Cabecalho } from "../../layout/Painel"

/**
 * O material que o aluno guardou, de qualquer semestre: o que foi marcado no
 * 3º período continua aqui no 6º, quando a matéria volta na revisão.
 */
export function Favoritos() {
  const { dados, carregando, erro } = useApi("/aluno/favoritos")
  // Tirar a estrela tira da lista na hora: esta tela é só de favoritos.
  const [retirados, setRetirados] = useState(() => new Set())
  const favoritos = (dados?.favoritos || []).filter((m) => !retirados.has(m.id))

  return (
    <>
      <Cabecalho titulo="Favoritos" descricao="O material que você guardou, de qualquer semestre." />
      {carregando && <Carregando />}
      {erro && <EstadoVazio>{erro}</EstadoVazio>}
      {dados && favoritos.length === 0 && (
        <EstadoVazio>Nenhum favorito ainda. Toque na estrela ☆ de um material para guardá-lo aqui.</EstadoVazio>
      )}
      {favoritos.length > 0 && (
        <ListaDeMateriais materiais={favoritos}
          aoDesfavoritar={(material) => setRetirados((atual) => new Set(atual).add(material.id))} />
      )}
    </>
  )
}
