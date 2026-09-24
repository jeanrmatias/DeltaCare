# PROMPT — IMPLEMENTAÇÃO DE MELHORIAS NA PLATAFORMA EDUCACIONAL DELTACARE

## Papel
Você é um desenvolvedor(a) full-stack sênior responsável por implementar melhorias
na plataforma educacional DeltaCare. Antes de implementar cada item, analise o
código existente, identifique os arquivos e componentes envolvidos e aplique as
melhores práticas de desenvolvimento (código limpo, testes, acessibilidade e UX).
Ao final, documente o que foi alterado.

## Contexto da plataforma
- Plataforma educacional com perfis de acesso: Administrador (ADM), Professor e Aluno.
- Possui módulos de: materiais didáticos, turmas, notificações, dashboard,
  chat com IA e cadastro de usuários.
- O código-fonte está no repositório: https://github.com/jeanrmatias/DeltaCare

## Escopo
Implementar as melhorias abaixo, organizadas por área. Siga a ordem de priorização
indicada no final.

---

## 1. ÁREA DO PROFESSOR

### 1.1 Publicação de materiais — seleção múltipla de turmas
- **Problema:** ao publicar um material, o professor só consegue selecionar UMA
  turma por vez, o que gera retrabalho quando o mesmo material deve ir para
  várias turmas.
- **Solução esperada:**
  - Permitir selecionar múltiplas turmas no momento da publicação do material.
  - Exibir a lista de turmas do professor com checkboxes.
  - Incluir opção "Selecionar todas" para agilizar a seleção em massa.
  - Ajustar a API/backend para aceitar múltiplos identificadores de turma
    (ex.: array de turma_ids) mantendo a integridade referencial no banco de dados.

### 1.2 Notificações — painel não abre
- **Problema:** o ícone de notificações exibe "5 notificações pendentes", mas ao
  clicar nada acontece — o painel não abre.
- **Solução esperada:**
  - Corrigir o evento de clique do componente de notificações.
  - Garantir que o painel (drawer/popover) abra e liste as notificações pendentes.
  - Consumir o endpoint responsável pela listagem e marcação de leitura.

---

## 2. PERFIL ADMINISTRATIVO (ADM)

### 2.1 Cadastro de usuários — campo nome
- **Problema:** ao criar uma conta, só é possível informar e-mail, perfil e senha
  provisória. Não há campo de nome.
- **Solução esperada:**
  - Adicionar campo obrigatório "Nome" no cadastro de usuários.
  - Aplicar a todos os perfis: administrativo, professor e aluno.
  - Refletir a alteração no banco de dados e nas listagens de usuários.

### 2.2 Campos adicionais por perfil
- **Professor:** campo para informar as matérias/disciplinas que leciona.
- **Aluno:** campos para turma em que está matriculado, número de matrícula e
  outras informações cadastrais relevantes.

### 2.3 Importação de dados em massa
- **Problema:** cadastrar alunos um a um é trabalhoso.
- **Solução esperada:**
  - Permitir importar dados de alunos já matriculados a partir de planilha
    (CSV/Excel .xlsx) — e avaliar viabilidade de PDF.
  - Validar os dados antes de persistir (tipos, campos obrigatórios).
  - Gerar relatório de inconsistências com as linhas rejeitadas.

### 2.4 Implementação futura (fora do escopo atual)
- Autosserviço: usuário poderá editar o próprio perfil. Registrar como item
  futuro, não implementar agora.

---

## 3. ÁREA DO ALUNO

### 3.1 Dashboard inicial — XP e acompanhamento
- **Problema:** o aluno só vê seus pontos de experiência (XP) e acompanhamento
  na aba de desempenho.
- **Solução esperada:**
  - Exibir no dashboard inicial um resumo com: XP acumulado e indicadores
    básicos de acompanhamento.
  - Manter os detalhes aprofundados na aba de desempenho.

### 3.2 Materiais — filtros por assunto/matéria
- **Problema:** os materiais aparecem apenas em lista, sem filtros.
- **Solução esperada:**
  - Adicionar filtros por assunto, matéria/cadeira (e período, se aplicável).

### 3.3 Materiais — visualização na plataforma
- **Problema:** o aluno é obrigado a baixar o material para vê-lo.
- **Solução esperada:**
  - Adicionar guia/visualizador embutido para visualizar o material dentro da
    plataforma (ex.: PDF e formatos comuns), sem download obrigatório.

---

## 4. CHAT

### 4.1 Botão "Parar" durante a geração de resposta
- **Problema:** enquanto o chat carrega uma resposta, não há como interromper.
  As únicas saídas hoje são recarregar a página ou trocar de guia.
- **Solução esperada:**
  - Exibir botão "Parar" enquanto a resposta está sendo gerada.
  - Ao clicar, cancelar a requisição em andamento (ex.: AbortController em
    requisições HTTP/streaming) e encerrar a geração.

---

## 5. PRIORIZAÇÃO SUGERIDA

### Alta prioridade (bugs e requisitos estruturais)
1. Notificações do professor (funcionalidade quebrada).
2. Botão "Parar" no chat.
3. Campo nome no cadastro de usuários (ADM).

### Média prioridade
4. Seleção múltipla de turmas na publicação de materiais.
5. XP e acompanhamento no dashboard do aluno.
6. Visualizador de materiais dentro da plataforma.

### Baixa prioridade / futura
7. Filtros na lista de materiais.
8. Importação em massa de dados (CSV/XLSX).
9. Edição de perfil pelo próprio usuário (autosserviço).

---

## Restrições e considerações
- Preserve a identidade visual e os padrões de UX já existentes na plataforma.
- Não quebre funcionalidades existentes; implemente de forma incremental.
- Adicione testes para as correções e novas funcionalidades sempre que possível.
- Ao terminar cada item, resuma: o que foi alterado, arquivos envolvidos e como
  testar.
- Se alguma informação de contexto faltar (ex.: stack tecnológica, estrutura do
  banco), solicite antes de implementar.