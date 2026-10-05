"""O material em PDF da demonstração: textos de medicina de verdade.

Usado pelo seed_demo.py e pelo seed_semestre.py. Antes o exemplo era
inventado (um remédio, uma escala e um protocolo que não existem), para provar
que o assistente lia o material e não respondia de memória. A prova continua
de pé por outro caminho: cada resposta mostra de qual PDF e de qual trecho
saiu, e o que não está no material ele não responde.

O conteúdo segue livros-texto e diretrizes citados no fim de cada aula. É
material didático de exemplo: não substitui a diretriz atualizada.

O gerador de PDF do projeto (seed_demo.gerar_pdf) escreve em WinAnsi: acento
pode, mas "≥", "≤", setas e índices como "₂" não existem nessa codificação.
Por isso "maior ou igual a" por extenso e "CHA2DS2-VASc" sem subscrito. O
teste TestesMaterialDeDemonstracao confere isso e a largura das linhas.
"""

# --------------------------------------------------------------- Cardiologia

IC_AGUDA = {
    "titulo": "Aula 3 - Insuficiência cardíaca aguda",
    "arquivo": "cardiologia_aula3.pdf",
    "assunto": "Cardiologia",
    "topico": "Insuficiência cardíaca",
    "texto": """Cardiologia I - Aula 3
Insuficiência cardíaca aguda: avaliação e manejo inicial

1. DEFINIÇÃO

Insuficiência cardíaca (IC) aguda é o início rápido, ou a piora, de sinais e
sintomas de IC que leva o paciente a procurar atendimento de urgência. Na maior
parte dos casos é a descompensação de uma IC crônica; nos demais, é uma IC nova,
como a que surge depois de um infarto.

2. FATORES PRECIPITANTES

Os mais comuns: síndrome coronariana aguda, arritmias (sobretudo fibrilação
atrial com resposta ventricular rápida), hipertensão não controlada, infecções,
má adesão aos remédios ou à restrição de sal, uso de anti-inflamatórios não
esteroides, piora da função renal e embolia pulmonar.

Cinco causas pedem tratamento específico imediato (mnemônico CHAMP): síndrome
Coronariana aguda, emergência Hipertensiva, Arritmia, causa Mecânica aguda (por
exemplo, ruptura de músculo papilar) e embolia Pulmonar.

3. CLASSIFICAÇÃO PELA FRAÇÃO DE EJEÇÃO

- IC com fração de ejeção reduzida: 40% ou menos.
- IC com fração de ejeção levemente reduzida: de 41% a 49%.
- IC com fração de ejeção preservada: 50% ou mais.

4. PERFIS CLÍNICO-HEMODINÂMICOS (CLASSIFICAÇÃO DE STEVENSON)

Dois eixos, avaliados à beira do leito: congestão (úmido ou seco) e perfusão
(quente ou frio).

Sinais de congestão: ortopneia, turgência jugular, estertores pulmonares,
refluxo hepatojugular, edema de membros inferiores e terceira bulha (B3).
Sinais de baixa perfusão: extremidades frias, pressão de pulso estreita,
sonolência ou confusão, oligúria e hipotensão.

Perfil A (quente e seco): compensado. Ajuste do tratamento oral.
Perfil B (quente e úmido): o mais frequente. Congestão com perfusão
preservada. Base do tratamento: diurético de alça intravenoso; vasodilatador
quando a pressão estiver elevada.
Perfil C (frio e úmido): congestão com baixa perfusão; é o de pior prognóstico.
Diurético associado a suporte inotrópico quando há hipotensão ou sinais de
hipoperfusão, em unidade de terapia intensiva.
Perfil L (frio e seco): baixa perfusão sem congestão; é o menos comum. Avaliar
a volemia: pode haver benefício com reposição volêmica cautelosa.

5. CLASSES FUNCIONAIS DA NYHA

Classe I: sem limitação; a atividade habitual não causa sintomas.
Classe II: limitação leve; sintomas com a atividade habitual.
Classe III: limitação acentuada; sintomas com atividade menor que a habitual.
Classe IV: sintomas em repouso.

6. AVALIAÇÃO INICIAL

Eletrocardiograma, radiografia de tórax, ecocardiograma, peptídeos
natriuréticos, troponina, função renal, eletrólitos, hemograma e glicemia.
No quadro agudo, BNP abaixo de 100 pg/mL ou NT-proBNP abaixo de 300 pg/mL tornam
o diagnóstico de IC improvável.

7. TRATAMENTO INICIAL

Oxigênio: só se a saturação estiver abaixo de 90%. Ventilação não invasiva no
edema agudo de pulmão com desconforto respiratório.

Diurético de alça intravenoso (furosemida): em quem não usava diurético, 20 a
40 mg; em quem já usava, de uma a duas vezes a dose oral diária. A resposta é
adequada quando o sódio urinário passa de 50 a 70 mEq/L em 2 horas, ou a
diurese passa de 100 a 150 mL por hora nas primeiras 6 horas.

Vasodilatador (nitrato): pode ser usado com pressão sistólica acima de
110 mmHg. Inotrópico (dobutamina): reservado à hipotensão, com pressão
sistólica abaixo de 90 mmHg, com sinais de hipoperfusão; não é de uso rotineiro.
Profilaxia de tromboembolismo venoso durante a internação.

8. MONITORIZAÇÃO

Peso diário, sempre no mesmo horário; balanço hídrico e diurese; função renal
e potássio diariamente; pressão arterial, frequência cardíaca e saturação.

9. ANTES DA ALTA

Na IC com fração de ejeção reduzida, iniciar ou otimizar os quatro pilares:
inibidor do sistema renina-angiotensina (IECA, BRA ou sacubitril-valsartana),
betabloqueador, antagonista mineralocorticoide (espironolactona) e inibidor de
SGLT2 (dapagliflozina ou empagliflozina). Retorno em 1 a 2 semanas após a alta.

Referências: Diretriz de IC da Sociedade Europeia de Cardiologia (2021, com a
atualização de 2023); Diretriz Brasileira de IC Crônica e Aguda (SBC, 2018).
Material didático: não substitui a diretriz atualizada nem o julgamento clínico.
""",
}

FIBRILACAO_ATRIAL = {
    "titulo": "Aula 4 - Fibrilação atrial e flutter",
    "arquivo": "cardiologia_aula4.pdf",
    "assunto": "Cardiologia",
    "topico": "Arritmias",
    "texto": """Cardiologia I - Aula 4
Fibrilação atrial e flutter atrial

1. FIBRILAÇÃO ATRIAL (FA)

É a arritmia sustentada mais comum em adultos. A ativação dos átrios é
desorganizada e não há contração atrial efetiva. No eletrocardiograma: ausência
de ondas P, ondas f irregulares na linha de base e intervalos RR irregularmente
irregulares.

Fatores de risco: idade, hipertensão, insuficiência cardíaca, valvopatias,
diabetes, obesidade, apneia obstrutiva do sono, consumo de álcool e
hipertireoidismo.

2. CLASSIFICAÇÃO PELO TEMPO

- Primeiro diagnóstico: FA nunca documentada antes.
- Paroxística: termina sozinha ou com intervenção em até 7 dias.
- Persistente: dura mais de 7 dias.
- Persistente de longa duração: mais de 12 meses, quando se decide buscar o ritmo.
- Permanente: paciente e médico decidem não tentar mais restaurar o ritmo.

3. RISCO DE AVC: ESCORE CHA2DS2-VASc

C - insuficiência cardíaca: 1 ponto
H - hipertensão: 1 ponto
A2 - idade de 75 anos ou mais: 2 pontos
D - diabetes: 1 ponto
S2 - AVC, ataque isquêmico transitório ou tromboembolismo prévio: 2 pontos
V - doença vascular (infarto prévio, doença arterial periférica, placa aórtica): 1
A - idade de 65 a 74 anos: 1 ponto
Sc - sexo feminino: 1 ponto
Pontuação máxima: 9.

Pela diretriz europeia de 2020, a anticoagulação é recomendada com escore de 2
ou mais em homens e de 3 ou mais em mulheres, e deve ser considerada com 1 ponto
em homens e 2 em mulheres. A diretriz europeia de 2024 passou a usar o
CHA2DS2-VA, sem o critério de sexo: anticoagular com 2 pontos ou mais e
considerar com 1.

4. RISCO DE SANGRAMENTO

O escore HAS-BLED de 3 ou mais indica risco alto de sangramento. Ele serve para
corrigir o que é modificável (pressão descontrolada, álcool, uso de
anti-inflamatórios), e não para negar a anticoagulação.

5. ANTICOAGULANTES

Os anticoagulantes orais diretos (apixabana, rivaroxabana, edoxabana e
dabigatrana) são preferidos à varfarina. As exceções são a estenose mitral
moderada a grave e a prótese valvar mecânica: nesses casos, varfarina.

6. CONTROLE DA FREQUÊNCIA

Betabloqueadores, bloqueadores de canal de cálcio não di-hidropiridínicos
(diltiazem e verapamil, que devem ser evitados na IC com fração de ejeção
reduzida) e digoxina. Meta inicial: frequência em repouso abaixo de 110 bpm.

7. CONTROLE DO RITMO

Cardioversão elétrica ou farmacológica e ablação por cateter, que isola as
veias pulmonares. Com instabilidade hemodinâmica, cardioversão elétrica
sincronizada imediata.

Pela diretriz americana (AHA/ACC), na FA com 48 horas ou mais, ou de duração
desconhecida, a cardioversão eletiva exige anticoagulação por pelo menos 3
semanas antes (ou um ecocardiograma transesofágico sem trombo) e por pelo menos
4 semanas depois.

8. FLUTTER ATRIAL TÍPICO

Macrorreentrada no átrio direito que depende do istmo cavotricuspídeo. No
eletrocardiograma, ondas F "em dente de serra", mais visíveis em DII, DIII e aVF.
A frequência atrial fica em torno de 300 bpm; com condução 2:1, a ventricular
fica em torno de 150 bpm. A ablação do istmo tem alta taxa de sucesso. O
critério de anticoagulação é o mesmo da FA.

Referências: Diretrizes de FA da Sociedade Europeia de Cardiologia (2020 e
2024); Diretriz de FA da AHA/ACC/ACCP/HRS (2023).
Material didático: não substitui a diretriz atualizada nem o julgamento clínico.
""",
}

SAUDE_MENTAL_E_CORACAO = {
    "titulo": "Aula 7 - Saúde mental e doença cardiovascular",
    "arquivo": "cardiologia_aula7.pdf",
    "assunto": "Cardiologia",
    "topico": "Saúde mental",
    "texto": """Cardiologia I - Aula 7
Saúde mental e doença cardiovascular

1. DEPRESSÃO DEPOIS DO INFARTO

Cerca de 1 em cada 5 pacientes tem depressão maior depois de um infarto. A
depressão está associada a menor adesão aos remédios, menor participação na
reabilitação cardíaca e maior mortalidade. Por isso, a American Heart
Association (2014) a considera um fator de risco para pior evolução depois de
uma síndrome coronariana aguda.

2. RASTREIO

PHQ-2: as duas primeiras perguntas do PHQ-9 (humor deprimido e perda de
interesse nas duas últimas semanas). Pontuação de 3 ou mais: aplicar o PHQ-9.

PHQ-9: nove itens, de 0 a 27 pontos. De 5 a 9, sintomas leves; de 10 a 14,
moderados; de 15 a 19, moderadamente graves; 20 ou mais, graves.
O item 9 pergunta sobre pensamentos de morte ou de se ferir: qualquer resposta
positiva exige avaliar o risco de suicídio na mesma consulta.

GAD-7 (ansiedade): sete itens, de 0 a 21 pontos. Cortes de 5, 10 e 15 para
sintomas leves, moderados e graves; 10 ou mais indica investigar.

3. TRATAMENTO

Psicoterapia (terapia cognitivo-comportamental), atividade física e
reabilitação cardíaca ajudam tanto no humor quanto no coração.

Antidepressivos: os inibidores seletivos da recaptação de serotonina (ISRS)
são a primeira escolha. A sertralina foi estudada depois de síndrome
coronariana aguda (estudo SADHART) e se mostrou segura. O citalopram prolonga o
intervalo QT conforme a dose: a FDA limita a 40 mg por dia, e a 20 mg acima de
60 anos.

Os antidepressivos tricíclicos devem ser evitados no cardiopata: alargam o QRS,
prolongam o QT, causam hipotensão ortostática e podem desencadear arritmias.

Atenção: ISRS associados a antiagregantes ou anticoagulantes aumentam o risco
de sangramento.

4. CARDIOMIOPATIA DE TAKOTSUBO

Também chamada cardiomiopatia induzida por estresse. Disfunção transitória do
ventrículo esquerdo, em geral com balonamento da ponta (apical), que costuma
surgir depois de um estresse emocional ou físico intenso. Cerca de 90% dos
casos são em mulheres, a maioria depois da menopausa.

O quadro imita um infarto: dor torácica, alterações no eletrocardiograma e
troponina elevada, mas sem obstrução coronariana que explique a disfunção. A
função costuma se recuperar em dias a semanas. Não é benigna: na fase aguda,
as complicações são semelhantes às da síndrome coronariana aguda.

5. ESTRESSE E RISCO CARDIOVASCULAR

Estresse crônico, isolamento social e solidão estão associados a maior risco
de doença coronariana e de AVC. Perguntar sobre sono, humor e rede de apoio faz
parte da consulta cardiológica.

Referências: Lichtman e cols., Circulation 2014 (AHA, depressão após síndrome
coronariana aguda); Glassman e cols., JAMA 2002 (SADHART); Templin e cols.,
NEJM 2015 (registro internacional de Takotsubo).
Material didático: não substitui a diretriz atualizada nem o julgamento clínico.
""",
}

# ------------------------------------------------------------------ Anatomia

OSSOS_DO_CRANIO = {
    "titulo": "Aula 2 - Ossos do crânio",
    "arquivo": "anatomia_aula2.pdf",
    "assunto": "Anatomia",
    "topico": "Crânio",
    "texto": """Anatomia - Aula 2
Ossos do crânio, suturas e fontanelas

1. QUANTOS OSSOS

O crânio tem 22 ossos, divididos em neurocrânio (que envolve o encéfalo) e
viscerocrânio (o esqueleto da face). Os ossículos da audição e o osso hioide
não entram nessa conta.

2. NEUROCRÂNIO: 8 OSSOS

- Frontal (1)
- Parietais (2)
- Temporais (2)
- Occipital (1)
- Esfenoide (1)
- Etmoide (1)

3. VISCEROCRÂNIO: 14 OSSOS

- Nasais (2)
- Maxilas (2)
- Zigomáticos (2)
- Palatinos (2)
- Lacrimais (2)
- Conchas nasais inferiores (2)
- Vômer (1)
- Mandíbula (1)

A mandíbula é o único osso móvel do crânio: articula-se com o temporal pela
articulação temporomandibular (ATM).

Ossículos da audição: martelo, bigorna e estribo, de cada lado (6 no total).

4. SUTURAS

- Coronal: entre o frontal e os dois parietais.
- Sagital: entre os dois parietais.
- Lambdóidea: entre os parietais e o occipital.
- Escamosa: entre o temporal e o parietal.

Bregma é o encontro das suturas coronal e sagital; lambda, o das suturas
sagital e lambdóidea.

5. PTÉRIO

Região em forma de H onde se encontram o frontal, o parietal, a parte escamosa
do temporal e a asa maior do esfenoide. O osso ali é fino e cobre o ramo
anterior da artéria meníngea média: uma fratura nessa região pode romper a
artéria e causar hematoma extradural (epidural).

6. FONTANELAS DO RECÉM-NASCIDO

Espaços membranosos entre os ossos ainda não fundidos.
- Anterior (bregmática): a maior, em forma de losango. Fecha entre 12 e 24
  meses.
- Posterior (lambdóidea): triangular. Fecha nos primeiros 2 a 3 meses.
- Anterolaterais (esfenoidais) e posterolaterais (mastóideas), de cada lado.

Fontanela anterior abaulada pode indicar aumento da pressão intracraniana;
deprimida, desidratação.

7. CRANIOSSINOSTOSE

Fechamento precoce de uma ou mais suturas, que deforma o crânio porque ele
deixa de crescer perpendicularmente à sutura fechada. A mais comum é a da
sutura sagital, que produz um crânio alongado (escafocefalia).

Referências: Moore, Dalley e Agur, Anatomia Orientada para a Clínica; Netter,
Atlas de Anatomia Humana.
""",
}

BASE_DO_CRANIO = {
    "titulo": "Base do crânio - fossas e forames",
    "arquivo": "anatomia_base_do_cranio.pdf",
    "assunto": "Anatomia",
    "topico": "Crânio",
    "texto": """Anatomia - texto de apoio da Aula 5
Base do crânio: fossas e forames

1. AS TRÊS FOSSAS DO CRÂNIO

Fossa anterior: formada pela parte orbital do frontal, pela lâmina cribriforme
do etmoide e pelas asas menores do esfenoide. Aloja os lobos frontais.

Fossa média: formada pelo corpo e pelas asas maiores do esfenoide e pelas
partes escamosa e petrosa dos temporais. Aloja os lobos temporais. No centro
fica a sela turca, onde se apoia a hipófise.

Fossa posterior: formada principalmente pelo occipital e pelas partes petrosas
dos temporais. Aloja o cerebelo, a ponte e o bulbo.

2. FORAMES E O QUE PASSA POR ELES

Lâmina cribriforme (fossa anterior): filamentos do nervo olfatório (I).

Canal óptico: nervo óptico (II) e artéria oftálmica.

Fissura orbital superior: nervos oculomotor (III), troclear (IV), oftálmico
(V1, primeira divisão do trigêmeo) e abducente (VI), além das veias oftálmicas.

Forame redondo: nervo maxilar (V2).

Forame oval: nervo mandibular (V3) e nervo petroso menor.

Forame espinhoso: artéria e veia meníngeas médias.

Forame lácero: no vivo, fechado por cartilagem. A artéria carótida interna
passa sobre a parte superior dele, depois de sair do canal carótico.

Canal carótico: artéria carótida interna e plexo nervoso simpático.

Meato acústico interno: nervos facial (VII) e vestibulococlear (VIII) e
artéria do labirinto.

Forame jugular: nervos glossofaríngeo (IX), vago (X) e acessório (XI), e a
veia jugular interna, que começa ali.

Canal do hipoglosso: nervo hipoglosso (XII).

Forame magno: o maior de todos, no occipital. Por ele passam a transição entre
o bulbo (medula oblonga) e a medula espinal, as artérias vertebrais, as
meninges e as raízes espinais do nervo acessório.

Forame estilomastóideo (base externa): saída do nervo facial (VII) do crânio.

3. FRATURA DA BASE DO CRÂNIO

Sinais clássicos: equimose ao redor dos olhos (sinal do guaxinim), equimose
atrás da orelha, sobre o processo mastoide (sinal de Battle), e saída de
líquor pelo nariz (rinorreia) ou pelo ouvido (otorreia).

Referências: Moore, Dalley e Agur, Anatomia Orientada para a Clínica; Netter,
Atlas de Anatomia Humana.
""",
}

# ---------------------------------------------------------------- Fisiologia

CICLO_CARDIACO = {
    "titulo": "Aula 3 - Ciclo cardíaco",
    "arquivo": "fisiologia_aula3.pdf",
    "assunto": "Fisiologia",
    "topico": "Coração",
    "texto": """Fisiologia - Aula 3
Ciclo cardíaco

1. AS FASES, NA ORDEM

Sístole ventricular:
- Contração isovolumétrica: começa com o fechamento das valvas mitral e
  tricúspide (primeira bulha). Todas as valvas estão fechadas; a pressão sobe
  sem mudar o volume.
- Ejeção: quando a pressão do ventrículo supera a da aorta e a da artéria
  pulmonar, as valvas semilunares abrem. Primeiro ejeção rápida, depois lenta.

Diástole ventricular:
- Relaxamento isovolumétrico: começa com o fechamento das valvas aórtica e
  pulmonar (segunda bulha). Todas as valvas fechadas de novo.
- Enchimento rápido: as valvas atrioventriculares abrem e o sangue acumulado
  nos átrios entra no ventrículo.
- Diástase: enchimento lento.
- Contração atrial: completa o enchimento. Em repouso, cerca de 80% do sangue
  já passou dos átrios para os ventrículos antes dela; ela acrescenta em torno
  de 20%.

2. VOLUMES (ADULTO EM REPOUSO)

Volume diastólico final: cerca de 110 a 120 mL.
Volume sistólico: cerca de 70 mL.
Volume sistólico final: cerca de 40 a 50 mL.
Fração de ejeção (volume sistólico dividido pelo diastólico final): cerca de 60%.

Débito cardíaco = frequência cardíaca x volume sistólico. Em repouso, cerca de
5 litros por minuto.

3. PRESSÕES

Ventrículo esquerdo: cerca de 120 mmHg na sístole. Aorta: cerca de 120/80 mmHg.
Ventrículo direito: cerca de 25 mmHg na sístole. Artéria pulmonar: cerca de
25/8 mmHg.

4. BULHAS

B1: fechamento das valvas mitral e tricúspide.
B2: fechamento das valvas aórtica e pulmonar. Na inspiração, o retorno venoso
ao lado direito aumenta e a valva pulmonar fecha um pouco depois: é o
desdobramento fisiológico de B2.
B3: no enchimento rápido. Normal em crianças e jovens; no adulto, sugere
insuficiência cardíaca.
B4: na contração atrial, contra um ventrículo rígido. Não existe na fibrilação
atrial, porque não há contração atrial.

5. O CICLO E O ELETROCARDIOGRAMA

Onda P: despolarização atrial, seguida da contração dos átrios.
Complexo QRS: despolarização ventricular, logo antes da contração ventricular.
Onda T: repolarização ventricular, que precede o relaxamento.

6. PULSO VENOSO JUGULAR

Onda a: contração atrial. Onda c: abaulamento da valva tricúspide durante a
contração isovolumétrica. Onda v: enchimento do átrio com a tricúspide fechada.
Descendente x: relaxamento atrial; descendente y: abertura da tricúspide.

7. O QUE DETERMINA O VOLUME SISTÓLICO

Pré-carga (o enchimento: quanto mais o ventrículo é distendido, mais forte a
contração, dentro de limites; é a lei de Frank-Starling), pós-carga (a
resistência que o ventrículo vence para ejetar) e contratilidade.

Referência: Guyton e Hall, Tratado de Fisiologia Médica.
""",
}

ESTRESSE = {
    "titulo": "Aula 6 - Resposta ao estresse",
    "arquivo": "fisiologia_aula6.pdf",
    "assunto": "Fisiologia",
    "topico": "Estresse",
    "texto": """Fisiologia - Aula 6
Resposta ao estresse: sistema nervoso autônomo e eixo HHA

1. DOIS BRAÇOS DA RESPOSTA

Rápido, em segundos: o sistema simpático-adrenomedular. As fibras simpáticas
liberam noradrenalina, e a medula da adrenal libera adrenalina na circulação.

Mais lento, em minutos: o eixo hipotálamo-hipófise-adrenal (HHA).

2. A RESPOSTA SIMPÁTICA ("LUTA OU FUGA")

Aumento da frequência e da contratilidade cardíacas, broncodilatação, dilatação
das pupilas (midríase), quebra de glicogênio no fígado (glicogenólise) e
redistribuição do fluxo de sangue para os músculos esqueléticos, com
vasoconstrição na pele e nas vísceras.

3. O EIXO HIPOTÁLAMO-HIPÓFISE-ADRENAL

O núcleo paraventricular do hipotálamo libera o hormônio liberador de
corticotrofina (CRH). Na adeno-hipófise, o CRH estimula a liberação do
hormônio adrenocorticotrófico (ACTH). O ACTH age no córtex da adrenal (zona
fasciculada), que libera cortisol.

O próprio cortisol freia o eixo, agindo no hipotálamo e na hipófise
(retroalimentação negativa). O hipocampo, rico em receptores de
glicocorticoide, também participa desse freio.

Ritmo circadiano: o cortisol é mais alto ao despertar e mais baixo por volta
da meia-noite.

4. EFEITOS DO CORTISOL

- Aumenta a glicemia: estimula a gliconeogênese no fígado e reduz a captação
  de glicose pelos tecidos periféricos.
- Mobiliza gordura (lipólise) e proteína (catabolismo muscular).
- É anti-inflamatório e imunossupressor.
- Efeito permissivo: mantém a resposta dos vasos às catecolaminas.

5. ESTRESSE AGUDO E CRÔNICO

A síndrome geral de adaptação, descrita por Hans Selye, tem três fases:
alarme, resistência e exaustão.

A relação entre ativação e desempenho segue uma curva em U invertido (lei de
Yerkes-Dodson): um pouco de ativação melhora o desempenho; ativação excessiva
o piora.

O estresse crônico mantém o eixo ativado e está associado a hipertensão,
resistência à insulina, obesidade abdominal, menor resposta imune e alterações
do sono e do humor.

6. EIXO HHA E SAÚDE MENTAL

Na depressão maior é frequente a hiperatividade do eixo HHA; parte dos
pacientes não suprime o cortisol no teste da dexametasona. Estudos associam o
estresse crônico à redução de volume do hipocampo.

7. NA CLÍNICA

Quem usa glicocorticoide por tempo prolongado tem o eixo suprimido: o remédio
não pode ser suspenso de uma vez, pelo risco de insuficiência adrenal aguda
(crise adrenal), sobretudo diante de infecção, cirurgia ou trauma.
Excesso crônico de cortisol: síndrome de Cushing. Falta por destruição do
córtex da adrenal: doença de Addison.

Referências: Guyton e Hall, Tratado de Fisiologia Médica; Selye, The Stress of
Life (1956).
""",
}

SONO = {
    "titulo": "Aula 7 - Fisiologia do sono",
    "arquivo": "fisiologia_aula7.pdf",
    "assunto": "Fisiologia",
    "topico": "Sono",
    "texto": """Fisiologia - Aula 7
Fisiologia do sono

1. OS ESTÁGIOS

Vigília relaxada, de olhos fechados: ritmo alfa no eletroencefalograma (EEG).
N1: sono leve, transição; predominam ondas teta.
N2: fusos do sono e complexos K.
N3: sono profundo, de ondas lentas (ondas delta).
REM: EEG parecido com o da vigília, movimentos rápidos dos olhos e atonia dos
músculos esqueléticos (poupando o diafragma e os músculos dos olhos). É a fase
dos sonhos mais vívidos.

2. A ARQUITETURA DA NOITE

Cada ciclo dura cerca de 90 minutos; são de 4 a 6 por noite. O sono N3
predomina na primeira metade da noite, e o REM aumenta na segunda metade.

3. QUEM REGULA O SONO

Processo homeostático: durante a vigília a adenosina se acumula no cérebro e
aumenta a pressão para dormir. A cafeína bloqueia os receptores de adenosina.

Processo circadiano: o relógio central é o núcleo supraquiasmático do
hipotálamo, acertado pela luz que chega da retina. No escuro, a glândula
pineal libera melatonina.

4. QUANTO DORMIR

Adultos: 7 horas ou mais por noite. Adolescentes: de 8 a 10 horas.

5. PRIVAÇÃO DE SONO

Piora a atenção, a memória e o humor, e aumenta o risco de acidentes. Está
associada a obesidade, diabetes tipo 2 e hipertensão.

Depois de 17 a 19 horas acordado, o desempenho em testes de atenção e reação
fica igual ou pior que o de uma pessoa com 0,05% de álcool no sangue
(Williamson e Feyer, 2000). Vale para plantões.

6. SONO E SAÚDE MENTAL

A insônia é um sintoma frequente da depressão e também um fator de risco para
desenvolvê-la. O tratamento de primeira linha da insônia crônica é a terapia
cognitivo-comportamental para insônia (TCC-I), antes de remédios.

7. APNEIA OBSTRUTIVA DO SONO

Colapso repetido da via aérea superior durante o sono: ronco, pausas na
respiração observadas por quem dorme junto e sonolência durante o dia.
Diagnóstico por polissonografia, pelo índice de apneia e hipopneia (IAH) por
hora: de 5 a 14, leve; de 15 a 29, moderada; 30 ou mais, grave.
Está associada a hipertensão resistente e a fibrilação atrial. O tratamento de
escolha nos casos moderados e graves é o CPAP.

Referências: Manual de estagiamento do sono da AASM; Watson e cols., Sleep 2015
(recomendação de horas de sono para adultos); Qaseem e cols., Annals of Internal
Medicine 2016 (tratamento da insônia).
""",
}

# ---------------------------------------------------------------- Histologia

TECIDO_EPITELIAL = {
    "titulo": "Aula 4 - Tecido epitelial",
    "arquivo": "histologia_aula4.pdf",
    "assunto": "Histologia",
    "topico": "Epitélio",
    "texto": """Histologia - Aula 4
Tecido epitelial de revestimento

1. CARACTERÍSTICAS

Células justapostas, com pouca matriz extracelular. É avascular: recebe
nutrientes por difusão a partir do tecido conjuntivo, sobre o qual se apoia
pela lâmina basal. As células têm polaridade (faces apical, lateral e basal) e
se renovam continuamente.

2. CLASSIFICAÇÃO

Pelo número de camadas: simples, estratificado ou pseudoestratificado.
Pela forma das células da camada superficial: pavimentoso, cúbico ou
cilíndrico (prismático).

3. EXEMPLOS

Simples pavimentoso: endotélio dos vasos, mesotélio das serosas, alvéolos.
Simples cúbico: túbulos renais, ductos de glândulas, folículos da tireoide.
Simples cilíndrico: estômago e intestino (no intestino, com microvilosidades e
células caliciformes); ciliado na tuba uterina.
Pseudoestratificado cilíndrico ciliado com células caliciformes: traqueia e
brônquios (o epitélio respiratório).
Estratificado pavimentoso queratinizado: epiderme.
Estratificado pavimentoso não queratinizado: boca, esôfago, vagina e córnea.
Estratificado cúbico: ductos das glândulas sudoríparas.
De transição (urotélio): pelve renal, ureteres e bexiga. As células
superficiais, em guarda-chuva, permitem a distensão.

4. ESPECIALIZAÇÕES DA SUPERFÍCIE

Microvilosidades: projeções com eixo de actina que aumentam a área de absorção
(borda em escova no túbulo renal, borda estriada no intestino).
Estereocílios: microvilosidades longas, no epidídimo e no ducto deferente.
Cílios: móveis, com axonema 9+2 e dineína. Defeitos na dineína causam a
discinesia ciliar primária; com situs inversus, é a síndrome de Kartagener
(bronquiectasias, sinusite e infertilidade).

5. JUNÇÕES

Zônula de oclusão: veda o espaço entre as células (claudinas e ocludinas).
Zônula de adesão: caderinas ligadas à actina.
Desmossomos: caderinas (desmogleínas) ligadas a filamentos intermediários.
Hemidesmossomos: integrinas, prendem a célula à lâmina basal.
Junções comunicantes: canais de conexina entre células vizinhas.

Na clínica: no pênfigo vulgar, anticorpos contra a desmogleína 3 separam as
células da epiderme e formam bolhas dentro dela (intraepidérmicas). No
penfigoide bolhoso, os anticorpos atacam componentes dos hemidesmossomos e a
bolha fica abaixo da epiderme (subepidérmica).

6. METAPLASIA E TUMORES

Metaplasia é a troca de um tipo de epitélio por outro, como adaptação. No
fumante, o epitélio respiratório pode virar pavimentoso estratificado. No
esôfago de Barrett, causado pelo refluxo, o epitélio pavimentoso do esôfago é
substituído por epitélio cilíndrico com células caliciformes.
Os tumores malignos de origem epitelial são os carcinomas.

Referência: Junqueira e Carneiro, Histologia Básica.
""",
}

TECIDO_NERVOSO = {
    "titulo": "Aula 6 - Tecido nervoso",
    "arquivo": "histologia_aula6.pdf",
    "assunto": "Histologia",
    "topico": "Tecido nervoso",
    "texto": """Histologia - Aula 6
Tecido nervoso

1. O NEURÔNIO

Corpo celular (pericário), com corpúsculos de Nissl (retículo endoplasmático
rugoso); dendritos, que recebem estímulos; e um axônio, que conduz o impulso.
O potencial de ação começa no segmento inicial do axônio, junto ao cone de
implantação.

Pela forma:
- Multipolares: a maioria, como os neurônios motores.
- Bipolares: retina, epitélio olfatório e gânglios coclear e vestibular.
- Pseudounipolares: gânglios sensitivos das raízes dorsais.

2. NEURÓGLIA DO SISTEMA NERVOSO CENTRAL

Astrócitos: com seus pés vasculares, participam da barreira hematoencefálica;
controlam o ambiente iônico e formam a cicatriz glial. Marcador: GFAP.
Oligodendrócitos: formam a mielina no sistema nervoso central; cada um
mieliniza segmentos de vários axônios.
Micróglia: os macrófagos do sistema nervoso central, de origem no saco vitelino.
Células ependimárias: revestem os ventrículos e o canal central. No plexo
coroide, produzem o líquor.

3. NEURÓGLIA DO SISTEMA NERVOSO PERIFÉRICO

Células de Schwann: cada uma mieliniza um segmento de um único axônio.
Células satélites: envolvem os corpos dos neurônios nos gânglios.

4. MIELINA

Entre um segmento de mielina e outro ficam os nódulos de Ranvier. O impulso
salta de nódulo em nódulo (condução saltatória), o que é muito mais rápido.

Na esclerose múltipla, a desmielinização autoimune é no sistema nervoso
central. Na síndrome de Guillain-Barré, é no sistema nervoso periférico.

5. ENVOLTÓRIOS DO NERVO PERIFÉRICO

Endoneuro: em volta de cada fibra. Perineuro: em volta de cada fascículo, e
funciona como barreira. Epineuro: em volta do nervo inteiro.

6. MENINGES

Dura-máter, aracnoide e pia-máter. O líquor circula no espaço subaracnóideo,
entre a aracnoide e a pia-máter.

7. ORGANIZAÇÃO

Substância cinzenta: corpos de neurônios. Substância branca: axônios
mielinizados. O córtex cerebral mais comum (isocórtex) tem seis camadas; o
córtex do cerebelo tem três: molecular, de células de Purkinje e granular.

8. LESÃO E REGENERAÇÃO

Depois de um corte, o segmento distal do axônio degenera (degeneração
walleriana). No sistema nervoso periférico, o axônio pode crescer de novo,
cerca de 1 mm por dia, guiado pelas células de Schwann. No sistema nervoso
central a regeneração é pobre: a mielina dos oligodendrócitos e a cicatriz
glial inibem o crescimento.

Referência: Junqueira e Carneiro, Histologia Básica.
""",
}

# O material de cada disciplina, pelo nome dela no seed. A Aula 3 de
# Cardiologia (IC_AGUDA) fica de fora: é a do seed_demo, a primeira de todas.
POR_DISCIPLINA = {
    "Cardiologia I": [FIBRILACAO_ATRIAL, SAUDE_MENTAL_E_CORACAO],
    "Anatomia": [OSSOS_DO_CRANIO, BASE_DO_CRANIO],
    "Fisiologia": [CICLO_CARDIACO, ESTRESSE, SONO],
    "Histologia": [TECIDO_EPITELIAL, TECIDO_NERVOSO],
}

TODOS = [IC_AGUDA] + [material for lista in POR_DISCIPLINA.values() for material in lista]
