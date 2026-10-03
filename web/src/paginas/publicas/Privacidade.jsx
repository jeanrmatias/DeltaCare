import { AvisoDeAprovacao, Documento, Lista, Paragrafo, Titulo } from "../../componentes/Documento"

/**
 * Política de privacidade. Rota pública: tem que poder ser lida antes de
 * entrar — e por quem já entrou, que volta para o próprio início.
 */
export function Privacidade() {
  return (
    <Documento titulo="Privacidade e uso de dados" subtitulo="Delta Care — plataforma de apoio ao estudo em saúde">
      <Paragrafo>
        A instituição de ensino é a <strong>controladora</strong> dos dados desta plataforma: é ela que
        decide para que eles servem e responde por eles.
      </Paragrafo>
      <Paragrafo>
        A <strong>administração acadêmica</strong> da instituição é a <strong>encarregada pelo tratamento de
        dados</strong> (o DPO da LGPD): é ela que responde aos seus pedidos e às suas dúvidas sobre dados
        pessoais — pela tela Meus dados ou pela secretaria acadêmica.
      </Paragrafo>

      <Titulo>Que dados a plataforma guarda</Titulo>
      <Lista>
        <li><strong>Cadastro:</strong> nome, e-mail, matrícula e perfil (aluno, professor ou administração). A senha nunca é guardada em texto — fica só o hash (PBKDF2 com salt individual), que não permite recuperar a senha original.</li>
        <li><strong>Vínculo acadêmico:</strong> a turma e as disciplinas que você cursa, em cada semestre.</li>
        <li><strong>Atividades:</strong> suas entregas, os arquivos anexados, as notas e as devolutivas do professor.</li>
        <li><strong>Estudo:</strong> quais materiais você abriu e quando (é o que calcula seu nível e o ranking), seus favoritos e suas anotações.</li>
        <li><strong>Conversas:</strong> as perguntas ao assistente de estudos, com as respostas e os materiais citados, e as mensagens trocadas com os professores.</li>
        <li><strong>Avisos e notificações</strong> que você recebeu, e as denúncias de conteúdo que fez.</li>
        <li><strong>Sessão:</strong> um token temporário que identifica o seu acesso, com validade de 12 horas.</li>
      <li><strong>Registro de acesso e de ações (segurança):</strong> quando você entra ou erra a senha, de qual endereço de rede (IP), e as ações administrativas — criar e excluir contas, matrículas, decisões sobre dados pessoais. Fica por 1 ano e só a administração consulta; senha e código de verificação nunca são registrados.</li>
      </Lista>

      <Titulo>Onde os dados ficam</Titulo>
      <Paragrafo>
        Nos servidores da própria instituição, com acesso por HTTPS. O modelo de inteligência artificial
        também roda lá: nem o material de aula nem as perguntas dos alunos são enviados a serviços de
        terceiros — não há chamada a APIs externas de IA em nenhum ponto do sistema.
      </Paragrafo>

      <Titulo>Quem enxerga o quê</Titulo>
      <Lista>
        <li>O aluno acessa apenas o material publicado nas disciplinas em que está matriculado.</li>
        <li>O professor vê as disciplinas que leciona: o material, as entregas e as notas dos alunos delas, e as mensagens que recebe.</li>
        <li>A administração gerencia contas, turmas e matrículas e acompanha o conteúdo publicado. <strong>Não lê</strong> suas entregas, suas anotações nem suas conversas com o assistente.</li>
        <li>Suas anotações são só suas: nenhum outro perfil tem acesso a elas.</li>
        <li>Suas conversas com o assistente são individuais. Quando ele não encontra a resposta no material, o professor vê só o <strong>assunto</strong> da dúvida, em poucas palavras, e quantos alunos perguntaram — nunca o texto da pergunta nem quem perguntou. E um assunto só aparece para ele quando pelo menos dois alunos diferentes perguntaram. Serve para o professor saber o que falta no material.</li>
        <li>No ranking da turma aparece só o topo, e você pode escolher não aparecer.</li>
        <li>Nos <strong>relatórios</strong>, a administração e os professores veem números da turma — médias, entregas, quantos alunos estudaram, quanto o material respondeu ao assistente —, nunca com o nome de um aluno.</li>
      </Lista>
      <Paragrafo>
        Essas regras são verificadas no servidor a cada requisição, e não apenas escondidas na interface.
      </Paragrafo>

      <Titulo>Seus direitos (LGPD)</Titulo>
      <Paragrafo>
        A Lei Geral de Proteção de Dados garante a você acessar, corrigir, levar consigo e pedir a exclusão
        dos seus dados. Na plataforma, pela tela <strong>Meus dados</strong> (no seu perfil):
      </Paragrafo>
      <Lista>
        <li><strong>Cópia dos dados:</strong> você baixa na hora, sem precisar pedir a ninguém.</li>
        <li><strong>Correção</strong> de nome, e-mail ou matrícula: a administração confere com o registro acadêmico e responde pela própria plataforma.</li>
        <li><strong>Exclusão da conta:</strong> a administração avalia o pedido. Aprovado, a conta é desativada na hora.</li>
      </Lista>
      <Paragrafo>
        A administração também pode excluir a conta de quem deixou a instituição, com o mesmo prazo e as mesmas
        regras abaixo; o motivo fica registrado, e a pessoa é avisada por e-mail. Professores apagam o próprio
        conteúdo (material, atividade, aviso) a qualquer momento.
      </Paragrafo>

      <Titulo>Por quanto tempo guardamos</Titulo>
      <Paragrafo>
        Enquanto durar o vínculo acadêmico. Com a exclusão da conta aprovada, os dados pessoais são{" "}
        <strong>anonimizados 45 dias depois</strong>: nome, e-mail, matrícula, anotações, favoritos,
        notificações e as conversas com o assistente e com os professores deixam de existir. Até o fim desse
        prazo, a secretaria pode reativar a conta — é o caso de quem trancou e vai ser realocado.
      </Paragrafo>
      <Paragrafo>
        Notas, entregas e matrículas continuam, sem nada que identifique você: a instituição é obrigada a
        guardar o registro acadêmico.
      </Paragrafo>

      <AvisoDeAprovacao>
        <strong>Antes de usar com dados reais:</strong> a instituição precisa aprovar formalmente esta política
        e publicar o contato da administração acadêmica para assuntos de dados pessoais.
      </AvisoDeAprovacao>
    </Documento>
  )
}
