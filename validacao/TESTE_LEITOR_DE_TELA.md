# Teste com leitor de tela (NVDA)

Para quem conduz. É diferente do teste de usabilidade: aqui não se observa uma
pessoa de fora, e sim se **a plataforma funciona para quem não enxerga a
tela**. Leva uns 30 minutos.

## O que é o NVDA

Um **leitor de tela** gratuito para Windows (<https://www.nvaccess.org>), o
mais usado no Brasil por pessoas cegas ou com baixa visão. Ele lê em voz alta
o que está na tela, e a pessoa usa só o teclado. Se uma tela depende de ver
para ser usada — um botão que é só um ícone, uma resposta que aparece sem
aviso —, com o NVDA ela simplesmente não funciona.

O ideal é que o teste seja feito por alguém que usa leitor de tela no dia a
dia. Feito pela equipe, ainda pega a maior parte dos problemas; só registre
que foi assim.

## Preparar

1. Instale o NVDA (o instalador oferece rodar sem instalar). Ele fala em
   português sozinho se o Windows estiver em português.
2. Use o **Chrome** ou o **Edge**, numa janela anônima, em
   <http://127.0.0.1:8000/app/>, com o seed de demonstração no banco.
3. **Desligue o monitor** (ou feche os olhos de verdade). Olhar "só para
   conferir" estraga o teste: é exatamente o que a pessoa cega não pode fazer.

## As teclas que bastam

| Tecla | O que faz |
|---|---|
| `Tab` / `Shift+Tab` | Próximo / anterior elemento que se aperta ou preenche |
| `H` / `Shift+H` | Próximo / anterior título da página |
| `D` | Próxima região (menu, conteúdo) |
| `F` | Próximo campo de formulário |
| `Enter` / `Espaço` | Aperta o botão ou link; marca a caixa |
| Setas | Lê linha a linha; dentro de um campo, digita |
| `Ctrl` | Cala o NVDA |
| `Insert+F7` | Lista de links e títulos da página |
| `Insert+Q` | Encerra o NVDA |

## As tarefas

Marque **OK**, **com dificuldade** ou **não deu**, e anote o que o NVDA
falou quando algo deu errado — a frase exata é o que diz o que consertar.

| # | Tarefa (conta `aluno@deltacare.com` / `demo123`) | O que precisa acontecer |
|---|---|---|
| 1 | Entrar na plataforma | Os campos são anunciados como "E-mail" e "Senha"; um erro de senha é lido sem procurar |
| 2 | Na primeira tela depois do login, pular o menu | O primeiro `Tab` oferece "Pular para o conteúdo", e `Enter` leva ao título da página |
| 3 | Descobrir qual prova mudou de data | Chega ao aviso "Prova antecipada" pelos títulos (`H`) e ouve o texto dele |
| 4 | Abrir o Chat de estudos e perguntar a dose do Cardiolex | O campo é anunciado como "Sua pergunta"; enquanto espera, ouve "Consultando o material" **uma vez** (não a cada segundo); **a resposta é lida sozinha** quando chega, com a fonte |
| 5 | Interromper uma resposta no meio | Acha o botão "Parar" pelo `Tab` |
| 6 | Abrir a aula de insuficiência cardíaca e favoritá-la | O botão da estrela diz o que faz ("Guardar nos favoritos") e é anunciado como botão de alternância, pressionado ou não |
| 7 | Responder o quiz de insuficiência cardíaca | Cada questão é lida com as alternativas; dá para escolher com as setas e entregar |
| 8 | Abrir o perfil e fechar | A janela é anunciada com o nome dela; `Esc` fecha e o foco volta para onde estava |
| 9 | Abrir o sino de notificações | O botão diz quantas notificações há e se está aberto ou fechado |

Depois, com `adm@deltacare.com`: abrir **Relatórios** e trocar entre as abas
**Ao vivo**, **Por mês** e **Dificuldade por disciplina** — cada aba é
anunciada como aba, e a selecionada como selecionada.

## Registrar

No [RESULTADOS.md](RESULTADOS.md), numa seção "Leitor de tela": quem fez
(equipe ou usuário de leitor de tela), a data, o navegador, o resultado de cada
tarefa e as frases do NVDA nos problemas. Problema que impede a tarefa é
gravidade 4, como no teste de usabilidade.
