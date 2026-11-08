export interface TipoMateria { tipo: string; curto: string; texto: string }

/** Explicações gerais sobre cada tipo de matéria (texto institucional, não extraído das atas). */
export const glossario: TipoMateria[] = [
  {
    tipo: 'Projeto de Lei',
    curto: 'Proposta de uma nova lei municipal ou de mudança numa lei existente.',
    texto: 'Proposta de uma nova lei municipal ou de alteração de uma lei que já existe. É votada pelos vereadores e, se aprovada, vai ao prefeito, que pode sancionar (vira lei) ou vetar. Pode ser de iniciativa de vereadores ou do prefeito.',
  },
  {
    tipo: 'Projeto de Lei Complementar',
    curto: 'Proposta de lei sobre temas que exigem regras mais rígidas, como plano diretor e código de obras.',
    texto: 'Proposta de lei que trata de temas que a Lei Orgânica do município reserva a esse formato, como plano diretor, código de obras e estatuto dos servidores. Costuma exigir maioria absoluta dos vereadores, e não só dos presentes.',
  },
  {
    tipo: 'Projeto de Decreto Legislativo',
    curto: 'Norma da Câmara sobre assuntos só dela, como título de cidadão honorário. Não passa pelo prefeito.',
    texto: 'Norma aprovada pela Câmara sobre assuntos de sua competência exclusiva, como conceder título de cidadão honorário ou aprovar as contas do prefeito. Não precisa de sanção do prefeito.',
  },
  {
    tipo: 'Projeto de Resolução',
    curto: 'Norma sobre o funcionamento interno da Câmara, como o regimento e a organização dos serviços.',
    texto: 'Norma sobre a organização e o funcionamento interno da Câmara, como mudanças no regimento interno, na estrutura de cargos e nas comissões. Também não passa pelo prefeito.',
  },
  {
    tipo: 'Requerimento',
    curto: 'Pedido formal de um vereador, por exemplo de informações ao prefeito ou de providências da própria Câmara.',
    texto: 'Pedido formal feito por um ou mais vereadores, por exemplo para solicitar informações à Prefeitura, convocar alguém ou tomar uma providência dentro da Câmara. Em geral é votado em plenário, e o resultado vale como decisão da Câmara. Não cria lei.',
  },
  {
    tipo: 'Indicação',
    curto: 'Sugestão de um vereador ao prefeito para uma obra, serviço ou medida. O prefeito não é obrigado a atender.',
    texto: 'Sugestão de um vereador ao prefeito para uma obra, serviço ou medida de competência da Prefeitura, como tapar buracos ou instalar iluminação numa rua. Aprovar a indicação só encaminha o pedido: o prefeito não é obrigado a atendê-lo.',
  },
  {
    tipo: 'Moção',
    curto: 'Manifestação da Câmara, como aplauso, apelo ou repúdio sobre algum assunto.',
    texto: 'Manifestação formal da Câmara sobre um assunto, como aplauso a uma pessoa ou entidade, apelo a alguma autoridade ou repúdio a um fato. Tem valor simbólico e não cria obrigação.',
  },
];

export const glossarioPorTipo = new Map(glossario.map((g) => [g.tipo, g]));
