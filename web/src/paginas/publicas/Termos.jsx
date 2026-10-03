import { Link } from "react-router"

import { AvisoDeAprovacao, Documento, Lista, Paragrafo, Titulo } from "../../componentes/Documento"

/**
 * Termos de uso: as regras de quem usa o Delta Care. A política de
 * privacidade diz o que a plataforma faz com os dados; os termos dizem o que
 * se espera de quem está do outro lado.
 */
export function Termos() {
  return (
    <Documento titulo="Termos de uso" subtitulo="Delta Care — plataforma de apoio ao estudo em saúde">
      <Paragrafo>
        O Delta Care é oferecido pela instituição de ensino aos seus alunos, professores e à administração acadêmica,
        para apoiar o estudo e o ensino. Ao entrar, você concorda com estes termos e com a{" "}
        <Link to="/privacidade" className="font-semibold text-primaria hover:underline">política de privacidade</Link>.
      </Paragrafo>

      <Titulo>Quem pode usar</Titulo>
      <Lista>
        <li>Só quem tem vínculo com a instituição: toda conta é criada pela administração, e não há cadastro aberto.</li>
        <li>A conta é pessoal. Não empreste a sua senha nem use a de outra pessoa — inclusive a senha provisória que a turma recebeu.</li>
        <li>Professores e administração entram com a senha e um código enviado por e-mail. Se receber um código sem ter tentado entrar, troque a senha e avise a administração.</li>
      </Lista>

      <Titulo>O assistente de estudos</Titulo>
      <Lista>
        <li>O assistente responde <strong>somente</strong> a partir do material que o professor publicou na disciplina, e diz de onde tirou a resposta. Pode errar: confira a fonte e leve ao professor o que parecer estranho.</li>
        <li><strong>Não é orientação clínica.</strong> As respostas servem ao estudo e não substituem o julgamento de um profissional, protocolos da instituição de saúde nem a supervisão de um preceptor. Não use o assistente para decidir a conduta com um paciente real.</li>
        <li>Não coloque dados de pacientes (nome, prontuário, documento, foto) nas perguntas, nas anotações nem nas entregas.</li>
      </Lista>

      <Titulo>Integridade acadêmica</Titulo>
      <Lista>
        <li>As atividades são individuais, salvo quando o professor disser o contrário. Copiar a entrega de um colega, ou entregar o que o assistente escreveu como se fosse seu, segue as mesmas regras acadêmicas de qualquer avaliação.</li>
        <li>Tentar ver o que não é seu — gabarito, nota de colega, conversa alheia —, burlar o limite de tentativas ou testar falhas do sistema sem autorização da instituição é proibido e fica registrado.</li>
      </Lista>

      <Titulo>Conteúdo</Titulo>
      <Lista>
        <li>O material publicado é do professor e da instituição, para uso no curso. Não redistribua fora da plataforma sem autorização.</li>
        <li>Quem publica responde pelo que publica: o professor pelo material, o aluno pelas entregas e mensagens. Conteúdo ofensivo, fora do tema ou que viole direitos autorais pode ser denunciado pela própria plataforma, e a administração decide o que fazer.</li>
        <li>Os arquivos enviados passam por conferência de formato. Não envie programa, arquivo disfarçado ou nada que possa prejudicar quem baixar.</li>
      </Lista>

      <Titulo>Registro e consequências</Titulo>
      <Paragrafo>
        Acessos e ações administrativas ficam registrados por segurança, como descrito na política de privacidade.
        O uso em desacordo com estes termos pode levar à suspensão da conta e às medidas do regimento da instituição.
      </Paragrafo>

      <Titulo>Contato</Titulo>
      <Paragrafo>
        Dúvidas sobre estes termos ou sobre os seus dados: administração acadêmica, pela secretaria. Quando os termos
        mudarem, a nova versão aparece aqui, com a data.
      </Paragrafo>

      <AvisoDeAprovacao>
        <strong>Minuta:</strong> estes termos precisam ser revisados e aprovados pela instituição (jurídico e
        coordenação do curso) antes do uso com alunos reais, e passar a citar o regimento interno.
      </AvisoDeAprovacao>
    </Documento>
  )
}
