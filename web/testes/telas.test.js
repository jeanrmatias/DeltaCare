/**
 * Testes das telas: renderiza os componentes no Node (sem navegador) e
 * confere o HTML que sai.
 *
 * O Vite carrega os .jsx do jeito que o navegador carregaria; o React os
 * transforma em HTML com renderToString. Não roda os efeitos (as buscas na
 * API), então cada tela aparece no estado inicial — o que basta para provar
 * quem entra em qual rota e como um componente desenha os dados que recebe.
 */
import assert from "node:assert/strict"
import { after, before, test } from "node:test"

import { createElement as h } from "react"
import { renderToString } from "react-dom/server"
import { MemoryRouter } from "react-router"
import { createServer } from "vite"

let vite
let App, SessaoProvider, DialogosProvider, CartaoProgresso, Markdown

before(async () => {
  vite = await createServer({ server: { middlewareMode: true }, appType: "custom", logLevel: "error" })
  ;({ App } = await vite.ssrLoadModule("/src/App.jsx"))
  ;({ SessaoProvider } = await vite.ssrLoadModule("/src/sessao/SessaoProvider.jsx"))
  ;({ DialogosProvider } = await vite.ssrLoadModule("/src/dialogos/DialogosProvider.jsx"))
  ;({ CartaoProgresso } = await vite.ssrLoadModule("/src/paginas/aluno/CartaoProgresso.jsx"))
  ;({ Markdown } = await vite.ssrLoadModule("/src/componentes/Markdown.jsx"))
})

after(() => vite?.close())

/** O HTML sem os marcadores que o React põe entre trechos de texto. */
function html(elemento) {
  return renderToString(elemento).replace(/<!-- -->/g, "")
}

function logado(usuario) {
  const dados = usuario ? { deltacare_usuario: JSON.stringify(usuario), deltacare_token: "token" } : {}
  globalThis.sessionStorage = { getItem: (k) => dados[k] ?? null, setItem() {}, removeItem() {} }
}

/** O título da tela que aparece em `rota`, ou null se a rota redirecionou. */
function tituloEm(rota) {
  const saida = html(h(MemoryRouter, { initialEntries: [rota] }, h(SessaoProvider, null, h(DialogosProvider, null, h(App)))))
  return saida.match(/<h1[^>]*>(.*?)<\/h1>/)?.[1] ?? null
}

const ALUNA = { email: "marina@x.com", tipo: "aluno", nome: "Marina Duarte" }
const PROFESSOR = { email: "ricardo@x.com", tipo: "professor", nome: "Ricardo Salles" }
const ADM = { email: "coord@x.com", tipo: "adm", nome: "Coordenação" }

test("visitante vê o login e a privacidade, e nenhuma área privada", () => {
  logado(null)
  assert.equal(tituloEm("/"), "Delta Care")
  assert.equal(tituloEm("/privacidade"), "Privacidade e uso de dados")
  assert.equal(tituloEm("/termos"), "Termos de uso")
  for (const rota of ["/aluno", "/professor", "/admin"]) {
    assert.equal(tituloEm(rota), null, `${rota} abriu sem login`)
  }
})

test("cada perfil entra só na própria área", () => {
  const casos = [
    [ALUNA, "/aluno", "Olá, Marina Duarte"],
    [PROFESSOR, "/professor", "Olá, Prof. Ricardo"],
    [ADM, "/admin", "Olá, Coordenação"],
  ]
  for (const [usuario, propria, titulo] of casos) {
    logado(usuario)
    assert.equal(tituloEm(propria), titulo)
    for (const alheia of ["/aluno", "/professor", "/admin"].filter((r) => r !== propria)) {
      assert.equal(tituloEm(alheia), null, `${usuario.tipo} abriu ${alheia}`)
    }
  }
})

test("quem já entrou não vê o login de novo, mas ainda lê a privacidade", () => {
  logado(ALUNA)
  assert.equal(tituloEm("/"), null)
  assert.equal(tituloEm("/privacidade"), "Privacidade e uso de dados")
})

test("com a senha provisória, só a tela de trocar a senha abre", () => {
  logado({ ...ALUNA, trocar_senha: true })
  assert.equal(tituloEm("/trocar-senha"), "Defina a sua senha")
  for (const rota of ["/aluno", "/aluno/chat", "/aluno/meus-dados"]) {
    assert.equal(tituloEm(rota), null, `${rota} abriu antes da troca`)
  }
})

test("a tela de trocar a senha não abre para quem não precisa dela", () => {
  logado(null)
  assert.equal(tituloEm("/trocar-senha"), null)
  logado(ALUNA)
  assert.equal(tituloEm("/trocar-senha"), null)
})

test("toda tela logada começa com o atalho para pular o menu", () => {
  for (const [usuario, rota] of [[ALUNA, "/aluno"], [PROFESSOR, "/professor/materiais"], [ADM, "/admin/turmas"]]) {
    logado(usuario)
    const saida = html(h(MemoryRouter, { initialEntries: [rota] }, h(SessaoProvider, null, h(DialogosProvider, null, h(App)))))
    const atalho = saida.indexOf('href="#conteudo"')
    assert.ok(atalho >= 0 && atalho < saida.indexOf("Menu principal"), `${rota}: sem o atalho antes do menu`)
    assert.match(saida, /<main[^>]*id="conteudo"/, `${rota}: o conteúdo não tem o alvo do atalho`)
  }
})

test("endereço que não existe diz que não existe", () => {
  logado(null)
  assert.equal(tituloEm("/qualquer-coisa"), "Página não encontrada")
  // Mesmo dentro de /aluno: endereço inexistente não abre tela nem revela nada.
  assert.equal(tituloEm("/aluno/qualquer-coisa"), "Página não encontrada")
})

const PROGRESSO = {
  nivel: 4, xp: 500, xp_total: 500, semestre: "2026/2", xp_no_nivel: 50, xp_para_proximo_nivel: 200,
  faixa: { chave: "bronze", nome: "Bronze", proxima: "Prata", nivel_da_proxima: 5 },
  sequencia: 0, composicao: [{ rotulo: "Perguntas ao assistente", quantidade: 12, xp: 120 }],
  acompanhamento: [{ dia: "2026-10-01", ativo: true }, { dia: "2026-10-02", ativo: false }], dias_ativos: 9,
}

function progresso(alteracoes) {
  return html(h(MemoryRouter, null, h(CartaoProgresso, { progresso: { ...PROGRESSO, ...alteracoes } })))
}

test("progresso: XP, o que falta e o próximo degrau da faixa", () => {
  const saida = progresso({})
  assert.match(saida, /500 XP/)
  assert.match(saida, /faltam 150 XP para o nível 5/)
  assert.match(saida, /Falta 1 nível para Prata\./)
  assert.match(saida, /1 de 2 dias com estudo · 9 no total/)
})

test("progresso: sequência zerada não aparece, e platina não promete degrau", () => {
  assert.doesNotMatch(progresso({}), /dias seguidos/)
  assert.match(progresso({ sequencia: 3 }), /dias seguidos/)

  const platina = progresso({ faixa: { chave: "platina", nome: "Platina", proxima: null, nivel_da_proxima: null } })
  assert.match(platina, /Faixa máxima/)
  assert.doesNotMatch(platina, /Falta/)
})

test("progresso: XP de semestres anteriores aparece como total, sem inflar o do semestre", () => {
  assert.match(progresso({ xp_total: 1400 }), /Semestre 2026\/2 · 1400 XP desde o início/)
  assert.doesNotMatch(progresso({}), /desde o início/)
})

test("HTML vindo da IA aparece como texto, e não vira elemento", () => {
  // O texto do modelo passou por PDFs de professores: um <script> ou um
  // <img onerror> escondido ali não pode virar código na tela do aluno.
  const saida = html(h(Markdown, { texto: "Dose: **12,5 mg** <img src=x onerror=alert(1)> <script>alert(2)</script>" }))

  assert.match(saida, /<strong>12,5 mg<\/strong>/)
  assert.doesNotMatch(saida, /<img/)
  assert.doesNotMatch(saida, /<script/)
  assert.match(saida, /&lt;script&gt;/)
})

test("toda tela do menu do aluno abre para a aluna", () => {
  logado(ALUNA)
  const titulos = {
    "/aluno/chat": "Chat de estudos", "/aluno/mensagens": "Mensagens", "/aluno/materiais": "Materiais",
    "/aluno/atividades": "Atividades", "/aluno/desempenho": "Desempenho", "/aluno/denuncias": "Denúncias",
    "/aluno/favoritos": "Favoritos", "/aluno/anotacoes": "Anotações", "/aluno/ranking": "Ranking",
    "/aluno/historico": "Semestres anteriores", "/aluno/meus-dados": "Meus dados",
  }
  for (const [rota, titulo] of Object.entries(titulos)) assert.equal(tituloEm(rota), titulo, rota)
})

test("toda tela do professor e da administração abre com o título certo", () => {
  const casos = {
    professor: [PROFESSOR, {
      "/professor/materiais": "Materiais", "/professor/atividades": "Atividades", "/professor/calendario": "Calendário",
      "/professor/disciplinas": "Disciplinas", "/professor/mensagens": "Mensagens", "/professor/desempenho": "Desempenho",
      "/professor/denuncias": "Denúncias", "/professor/avisos": "Avisos", "/professor/historico": "Semestres anteriores",
      "/professor/lacunas": "Lacunas do material", "/professor/relatorios": "Relatórios",
    }],
    adm: [ADM, {
      "/admin/turmas": "Turmas", "/admin/disciplinas": "Disciplinas", "/admin/usuarios": "Usuários", "/admin/denuncias": "Denúncias",
      "/admin/avisos": "Avisos", "/admin/conteudo": "Conteúdo", "/admin/privacidade": "Privacidade", "/admin/relatorios": "Relatórios", "/admin/auditoria": "Auditoria",
    }],
  }
  for (const [, [usuario, titulos]] of Object.entries(casos)) {
    logado(usuario)
    for (const [rota, titulo] of Object.entries(titulos)) assert.equal(tituloEm(rota), titulo, rota)
  }
})

test("relatórios: a dificuldade por disciplina é só da administração", () => {
  const telaDe = (usuario, rota) => {
    logado(usuario)
    return html(h(MemoryRouter, { initialEntries: [rota] }, h(SessaoProvider, null, h(DialogosProvider, null, h(App)))))
  }
  assert.match(telaDe(ADM, "/admin/relatorios"), /Dificuldade por disciplina/)
  const doProfessor = telaDe(PROFESSOR, "/professor/relatorios")
  assert.match(doProfessor, /Ao vivo/)
  assert.doesNotMatch(doProfessor, /Dificuldade por disciplina/)
})

test("todo item de menu leva a uma rota que existe", async () => {
  // Item de menu para rota inexistente cairia em "Página não encontrada".
  const { MENUS } = await vite.ssrLoadModule("/src/layout/menus.js")
  const sessoes = { aluno: ALUNA, professor: PROFESSOR, adm: ADM }
  for (const [perfil, itens] of Object.entries(MENUS)) {
    logado(sessoes[perfil])
    for (const item of itens) assert.notEqual(tituloEm(item.caminho), "Página não encontrada", `${perfil}: ${item.caminho}`)
  }
})
