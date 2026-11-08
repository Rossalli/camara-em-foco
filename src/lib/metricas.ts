import { sessoes, eventos, materias, vereadores } from './data';

/** Anos com matérias cadastradas, do mais recente ao mais antigo. */
export const anosMetricas = [...new Set(materias.map((m) => m.ano))].sort((a, b) => b - a);

/** Último ano com atas lidas: é o padrão da página (2024 e 2026 não têm sessões no Siscam). */
export const anoPadrao = Math.max(...sessoes.filter((s) => s.status === 'ok').map((s) => Number(s.data_iso.slice(0, 4))));

const pct = (n: number, total: number) => (total ? (n / total) * 100 : 0);
const soProjeto = (t: string) => t.startsWith('Projeto');

export interface LinhaVereador {
  nome: string;
  slug: string;
  presentes: number;
  presencaPct: number;
  indicacoes: number;
  requerimentos: number;
  projetos: number;
  outras: number;
  solicitacoes: number; // indicações + requerimentos
  proposicoes: number;
  aprovadas: number;
  rejeitadas: number;
  contra: number;
  abstencoes: number;
}

export function metricas(ano: number) {
  const sessoesAno = sessoes.filter((s) => s.data_iso.startsWith(String(ano)));
  // Presença só é confiável quando a lista de presentes foi lida por inteiro (quórum = 5 de 9).
  const lidas = sessoesAno.filter((s) => s.status === 'ok' && s.presentes.length >= 5);
  const matAno = materias.filter((m) => m.ano === ano);

  const tipos = [...new Set(matAno.map((m) => m.tipo))].map((tipo) => {
    const ms = matAno.filter((m) => m.tipo === tipo);
    const apr = ms.filter((m) => m.situacao === 'aprovada').length;
    const rej = ms.filter((m) => m.situacao === 'rejeitada').length;
    return { tipo, total: ms.length, pct: pct(ms.length, matAno.length), aprovadas: apr, rejeitadas: rej, outras: ms.length - apr - rej };
  }).sort((a, b) => b.total - a.total);

  const situacoes = {
    aprovada: matAno.filter((m) => m.situacao === 'aprovada').length,
    rejeitada: matAno.filter((m) => m.situacao === 'rejeitada').length,
    encaminhada: matAno.filter((m) => m.situacao === 'encaminhada').length,
  };

  const votacoes = eventos.filter((e) => e.data_iso.startsWith(String(ano)) && !e.parecer && (e.resultado === 'aprovada' || e.resultado === 'rejeitada'));
  const divididas = votacoes.filter((e) => e.contra.length || e.abstencoes.length);

  const linhas: LinhaVereador[] = vereadores.map((v) => {
    const presentes = lidas.filter((s) => (s.presentes as string[]).includes(v.nome)).length;
    const ms = matAno.filter((m) => m.autoria.includes(v.nome));
    const n = (f: (t: string) => boolean) => ms.filter((m) => f(m.tipo)).length;
    const indicacoes = n((t) => t === 'Indicação');
    const requerimentos = n((t) => t === 'Requerimento');
    const projetos = n(soProjeto);
    return {
      nome: v.nome, slug: v.slug, presentes, presencaPct: pct(presentes, lidas.length),
      indicacoes, requerimentos, projetos, outras: ms.length - indicacoes - requerimentos - projetos,
      solicitacoes: indicacoes + requerimentos, proposicoes: ms.length,
      aprovadas: ms.filter((m) => m.situacao === 'aprovada').length,
      rejeitadas: ms.filter((m) => m.situacao === 'rejeitada').length,
      contra: votacoes.filter((e) => e.contra.includes(v.nome)).length,
      abstencoes: votacoes.filter((e) => e.abstencoes.includes(v.nome)).length,
    };
  }).filter((l) => l.presentes > 0 || l.proposicoes > 0 || l.contra > 0);

  return {
    ano, sessoesAno, lidas, matAno, tipos, situacoes, votacoes, divididas, linhas,
    temAtas: lidas.length > 0,
    rejeitadas: matAno.filter((m) => m.situacao === 'rejeitada'),
  };
}

/** Quem lidera (ou fecha) um ranking, incluindo empates. */
export function extremos(linhas: LinhaVereador[], campo: keyof LinhaVereador, maior = true) {
  if (!linhas.length) return { valor: 0, nomes: [] as string[] };
  const valores = linhas.map((l) => l[campo] as number);
  const valor = maior ? Math.max(...valores) : Math.min(...valores);
  return { valor, nomes: linhas.filter((l) => l[campo] === valor).map((l) => l.nome) };
}
