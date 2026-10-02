import { Link, Route, Routes } from "react-router"

import { useSessao } from "./hooks/useSessao"
import { Painel } from "./layout/Painel"
import { INICIO_DO_PERFIL } from "./lib/usuario"
import { Conteudo } from "./paginas/admin/Conteudo"
import { DenunciasAdmin } from "./paginas/admin/Denuncias"
import { DisciplinasAdmin } from "./paginas/admin/Disciplinas"
import { InicioAdmin } from "./paginas/admin/Inicio"
import { PrivacidadeAdmin } from "./paginas/admin/Privacidade"
import { Turmas } from "./paginas/admin/Turmas"
import { Usuarios } from "./paginas/admin/Usuarios"
import { Avisos } from "./paginas/comum/Avisos"
import { Denuncias } from "./paginas/comum/Denuncias"
import { Historico } from "./paginas/comum/Historico"
import { Mensagens } from "./paginas/comum/Mensagens"
import { ModuloPlanejado } from "./paginas/comum/ModuloPlanejado"
import { Anotacoes } from "./paginas/aluno/Anotacoes"
import { Atividades } from "./paginas/aluno/Atividades"
import { Chat } from "./paginas/aluno/Chat"
import { Desempenho } from "./paginas/aluno/Desempenho"
import { Favoritos } from "./paginas/aluno/Favoritos"
import { InicioAluno } from "./paginas/aluno/Inicio"
import { Materiais } from "./paginas/aluno/Materiais"
import { MeusDados } from "./paginas/aluno/MeusDados"
import { Ranking } from "./paginas/aluno/Ranking"
import { AtividadesProfessor } from "./paginas/professor/Atividades"
import { Calendario } from "./paginas/professor/Calendario"
import { DesempenhoProfessor } from "./paginas/professor/Desempenho"
import { Disciplinas } from "./paginas/professor/Disciplinas"
import { Lacunas } from "./paginas/professor/Lacunas"
import { InicioProfessor } from "./paginas/professor/Inicio"
import { MateriaisProfessor } from "./paginas/professor/Materiais"
import { Login } from "./paginas/publicas/Login"
import { Privacidade } from "./paginas/publicas/Privacidade"
import { TrocarSenha } from "./paginas/publicas/TrocarSenha"
import { RotaPrivada, SoVisitante } from "./rotas/RotaPrivada"

/**
 * O mapa de endereços do sistema.
 *
 * Públicas: login e privacidade. Privadas: uma árvore por perfil, cada uma
 * atrás da RotaPrivada daquele perfil e dentro do Painel (menu + rodapé).
 * Uma rota nova é uma linha aqui e um item em layout/menus.js.
 */
export function App() {
  return (
    <Routes>
      <Route element={<SoVisitante />}>
        <Route path="/" element={<Login />} />
      </Route>
      <Route path="/privacidade" element={<Privacidade />} />
      <Route path="/trocar-senha" element={<TrocarSenha />} />

      <Route element={<RotaPrivada perfil="aluno" />}>
        <Route element={<Painel />}>
          <Route path="/aluno" element={<InicioAluno />} />
          <Route path="/aluno/chat" element={<Chat />} />
          <Route path="/aluno/mensagens" element={<Mensagens />} />
          <Route path="/aluno/materiais" element={<Materiais />} />
          <Route path="/aluno/atividades" element={<Atividades />} />
          <Route path="/aluno/desempenho" element={<Desempenho />} />
          <Route path="/aluno/favoritos" element={<Favoritos />} />
          <Route path="/aluno/anotacoes" element={<Anotacoes />} />
          <Route path="/aluno/meus-dados" element={<MeusDados />} />
          <Route path="/aluno/ranking" element={<Ranking />} />
          <Route path="/aluno/historico" element={<Historico />} />
          <Route path="/aluno/denuncias" element={<Denuncias />} />
        </Route>
      </Route>

      <Route element={<RotaPrivada perfil="professor" />}>
        <Route element={<Painel />}>
          <Route path="/professor" element={<InicioProfessor />} />
          <Route path="/professor/materiais" element={<MateriaisProfessor />} />
          <Route path="/professor/atividades" element={<AtividadesProfessor />} />
          <Route path="/professor/calendario" element={<Calendario />} />
          <Route path="/professor/disciplinas" element={<Disciplinas />} />
          <Route path="/professor/mensagens" element={<Mensagens />} />
          <Route path="/professor/desempenho" element={<DesempenhoProfessor />} />
          <Route path="/professor/lacunas" element={<Lacunas />} />
          <Route path="/professor/avisos" element={<Avisos />} />
          <Route path="/professor/historico" element={<Historico />} />
          <Route path="/professor/denuncias" element={<Denuncias />} />
        </Route>
      </Route>

      <Route element={<RotaPrivada perfil="adm" />}>
        <Route element={<Painel />}>
          <Route path="/admin" element={<InicioAdmin />} />
          <Route path="/admin/turmas" element={<Turmas />} />
          <Route path="/admin/disciplinas" element={<DisciplinasAdmin />} />
          <Route path="/admin/usuarios" element={<Usuarios />} />
          <Route path="/admin/denuncias" element={<DenunciasAdmin />} />
          <Route path="/admin/avisos" element={<Avisos />} />
          <Route path="/admin/conteudo" element={<Conteudo />} />
          <Route path="/admin/privacidade" element={<PrivacidadeAdmin />} />
          <Route path="/admin/relatorios" element={<ModuloPlanejado chave="relatorios" />} />
        </Route>
      </Route>

      <Route path="*" element={<NaoEncontrada />} />
    </Routes>
  )
}

function NaoEncontrada() {
  const { usuario } = useSessao()
  const destino = usuario ? INICIO_DO_PERFIL[usuario.tipo] : "/"

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 p-4 text-center">
      <h1 className="text-2xl font-bold text-navy-900">Página não encontrada</h1>
      <p className="text-sm text-texto-secundario">O endereço não existe ou mudou de lugar.</p>
      <Link to={destino} className="text-sm font-semibold text-primaria hover:underline">
        {usuario ? "Voltar para o início" : "Ir para o login"}
      </Link>
    </div>
  )
}
