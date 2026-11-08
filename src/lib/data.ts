import sessoesRaw from '../../data/sessoes.json';
import pautasRaw from '../../data/pautas.json';
import vereadoresRaw from '../../data/vereadores.json';
import extrasRaw from '../../data/materias_siscam.json';

export type Pauta = (typeof pautasRaw)[number];
export type Sessao = (typeof sessoesRaw)[number];
export type Vereador = (typeof vereadoresRaw)[number];

export const sessoes: Sessao[] = sessoesRaw;
export const vereadores: Vereador[] = vereadoresRaw;
export const sessaoPorId = new Map(sessoes.map((s) => [s.id, s]));
export const vereadorPorNome = new Map(vereadores.map((v) => [v.nome, v]));

const slug = (s: string) =>
  s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');

export const eventos: Pauta[] = pautasRaw;
export const slugMateria = (e: { tipo: string; numero: number; ano: number }) => `${slug(e.tipo)}-${e.numero}-${e.ano}`;

/** Uma matéria (ex.: Projeto de Lei 68/2025) pode aparecer em várias sessões: parecer, votação... */
export interface Materia {
  slug: string;
  tipo: string;
  numero: number;
  ano: number;
  eventos: Pauta[];
  situacao: string;
  autoria: string[];
  contra: string[];
  descricao: string | null;
  /** descrição inferida da lei sancionada (PLs), não do texto do próprio projeto */
  estimada: boolean;
  lei: { numero: number; complementar: boolean; data: string; url: string | null; ementa: string } | null;
  docUrl: string | null;
  dataIso: string;
  /** true quando a matéria só existe no Siscam (sem ata de sessão com texto) */
  semAta: boolean;
}

const mapa = new Map<string, Materia>();
for (const e of [...eventos].sort((a, b) => a.data_iso.localeCompare(b.data_iso))) {
  const s = `${slug(e.tipo)}-${e.numero}-${e.ano}`;
  const m = mapa.get(s) ?? { slug: s, tipo: e.tipo, numero: e.numero, ano: e.ano, eventos: [], situacao: '', autoria: [], contra: [], descricao: null, estimada: false, lei: null, docUrl: null, dataIso: e.data_iso, semAta: false };
  m.eventos.push(e);
  mapa.set(s, m);
}
for (const m of mapa.values()) {
  const decisivo = [...m.eventos].reverse().find((e) => !e.parecer) ?? m.eventos[m.eventos.length - 1];
  m.situacao = decisivo.resultado;
  m.autoria = [...new Set(m.eventos.flatMap((e) => e.autoria))];
  m.contra = [...new Set(m.eventos.filter((e) => !e.parecer).flatMap((e) => e.contra))];
  m.descricao = m.eventos.find((e) => e.descricao)?.descricao ?? null;
  m.estimada = m.eventos.some((e) => e.descricao_estimada);
  m.lei = m.eventos.find((e) => e.lei)?.lei ?? null;
  m.docUrl = m.eventos.find((e) => e.doc_url)?.doc_url ?? null;
  m.dataIso = m.eventos[m.eventos.length - 1].data_iso;
}
for (const x of extrasRaw) {
  const s = `${slug(x.tipo)}-${x.numero}-${x.ano}`;
  if (mapa.has(s)) continue;
  mapa.set(s, { slug: s, tipo: x.tipo, numero: x.numero, ano: x.ano, eventos: [], situacao: x.resultado, autoria: x.autoria, contra: [],
    descricao: x.descricao, estimada: false, lei: null, docUrl: x.doc_url, dataIso: x.data_iso, semAta: true });
}
export const materias = [...mapa.values()].sort((a, b) => b.dataIso.localeCompare(a.dataIso) || b.numero - a.numero);

export const rotuloSituacao: Record<string, string> = {
  aprovada: 'Aprovada',
  rejeitada: 'Rejeitada',
  encaminhada: 'Encaminhada',
  retirada: 'Retirada',
  retirado: 'Retirada',
  'em andamento': 'Em andamento',
  'pedido de vista': 'Pedido de vista',
};
export const classeSituacao = (s: string) => (s === 'retirado' ? 'retirada' : s.replace(/ /g, '-'));

export const nomeLei = (l: { numero: number; complementar: boolean }) => `Lei ${l.complementar ? 'Complementar' : 'Ordinária'} nº ${l.numero}`;
export const dataBR = (iso: string) => iso.split('-').reverse().join('/');
export const nomeMateria = (m: { tipo: string; numero: number; ano: number }) => `${m.tipo} ${m.numero}/${m.ano}`;
export const slugVereador = (nome: string) => vereadorPorNome.get(nome)?.slug;

/** Resumo gerado a partir dos dados extraídos da ata (sem IA). */
export function resumoSessao(s: Sessao): string {
  if (s.status !== 'ok') return 'A ata desta sessão é um documento escaneado sem texto pesquisável, por isso ainda não foi possível extrair o resumo e as votações. Consulte a ata original.';
  const ev = eventos.filter((e) => e.sessao === s.id && !e.parecer);
  const votadas = ev.filter((e) => e.resultado === 'aprovada' || e.resultado === 'rejeitada');
  const apr = votadas.filter((e) => e.resultado === 'aprovada');
  const rej = votadas.filter((e) => e.resultado === 'rejeitada');
  const indic = ev.filter((e) => e.resultado === 'encaminhada').length;
  const dividida = votadas.filter((e) => e.contra.length || e.abstencoes.length).length;
  const partes = [`Com ${s.presentes.length || 'vários'} vereadores presentes, a sessão votou ${votadas.length} matéria${votadas.length === 1 ? '' : 's'}: ${apr.length} aprovada${apr.length === 1 ? '' : 's'} e ${rej.length} rejeitada${rej.length === 1 ? '' : 's'}.`];
  if (dividida) partes.push(`${dividida} votação${dividida === 1 ? '' : 'ões'} teve${dividida === 1 ? '' : 'ram'} votos contrários ou abstenções.`);
  if (indic) partes.push(`${indic} indicaç${indic === 1 ? 'ão foi encaminhada' : 'ões foram encaminhadas'} ao Executivo.`);
  return partes.join(' ');
}

/** Placar de um vereador (somente votações com texto de ata disponível). */
export function estatVereador(nome: string) {
  const votadas = eventos.filter((e) => !e.parecer && (e.resultado === 'aprovada' || e.resultado === 'rejeitada'));
  const contra = votadas.filter((e) => e.contra.includes(nome));
  const abst = votadas.filter((e) => e.abstencoes.includes(nome));
  const autoria = materias.filter((m) => m.autoria.includes(nome));
  return {
    contra,
    abst,
    autoria,
    aprovadasDeAutoria: autoria.filter((m) => m.situacao === 'aprovada').length,
    rejeitadasDeAutoria: autoria.filter((m) => m.situacao === 'rejeitada').length,
  };
}
