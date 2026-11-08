"""Transforma o texto das atas em data/*.json (sessões, pautas, vereadores).

Uso: python scraper/parse.py   (depois de scraper/fetch.py)
"""
import difflib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from descricao import curta

ROOT = Path(__file__).parent.parent
RAW = Path(__file__).parent / "raw"
OUT = ROOT / "data"
OUT.mkdir(exist_ok=True)

TIPOS = r"(Projeto de Lei Complementar|Projeto de Lei|Projeto de Resolução|Projeto de Decreto Legislativo|Projeto de Decreto|Requerimento|Indicação|Moção|Veto|Emenda|Substitutivo)"
REF = re.compile(TIPOS + r"\s*(?:n[\.ºo°�\s]*)+\s*(\d{1,4})\s*/\s*(\d{4})", re.I)


def plain(s):
    s = unicodedata.normalize("NFD", s.lower())
    return re.sub(r"[^a-z]", "", "".join(c for c in s if unicodedata.category(c) != "Mn"))


def plain_sp(s):
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def clean(txt):
    txt = re.sub(r"(Rua Benjamin Constant|Neves Paulista/SP - Fone|Email: camara|Site: w+\.camara)[^\n]*", " ", txt)
    return re.sub(r"\s+", " ", txt)


def tipo_norm(t):
    t = t.lower()
    for k in ("lei complementar", "lei", "resolução", "decreto legislativo", "decreto"):
        if k in t and t.startswith("projeto"):
            return "Projeto de " + {"decreto": "Decreto Legislativo"}.get(k, k.title() if k != "lei complementar" else "Lei Complementar")
    return t.title()


class Roster:
    """Agrupa variantes de grafia (OCR) de um mesmo vereador."""

    def __init__(self):
        self.canon = []  # nomes canônicos
        self.counts = Counter()
        self.variants = defaultdict(Counter)  # canon -> variantes de grafia

    def key(self, name):
        toks = [plain(t) for t in name.split() if len(t) > 2]
        return (toks[0] + toks[-1]) if toks else plain(name)

    def add(self, name):
        name = re.sub(r"\s+", " ", name).strip(" ,.")
        k = self.key(name)
        for c in self.canon:
            if plain(c) == plain(name) or difflib.SequenceMatcher(None, k, self.key(c)).ratio() >= 0.85:
                self.counts[c] += 1
                self.variants[c][name] += 1
                return c
        self.canon.append(name)
        self.counts[name] += 1
        self.variants[name][name] += 1
        return name

    def find_all(self, phrase):
        """Quais vereadores conhecidos aparecem numa frase (tolerante a nomes colados)."""
        p = plain(phrase)
        out = []
        for c in self.canon:
            toks = [plain(t) for t in c.split() if len(t) > 2]
            if toks and toks[0] in p and toks[-1] in p:
                out.append(c)
            elif difflib.SequenceMatcher(None, self.key(c), self.key(phrase)).ratio() > 0.9:
                out.append(c)
        return out


def limpa_nome(n):
    n = re.sub(r"\(.*?(\)|$)", " ", n)
    n = re.sub(r"(Vereador(?:a|es|as)?|Edil|Edis|Edila)", " ", n, flags=re.I)
    n = re.sub(r"[^A-Za-zÀ-ú ]", " ", n)
    return " ".join(t for t in n.split() if len(t) > 1)


def presentes(txt):
    m = re.search(r"comparecimento d[oa]s? Vereadores?:?\s*(.+?)(?:\.\s|Havendo)", txt, re.I)
    if not m:
        return []
    nomes = [limpa_nome(n) for n in re.split(r",| e (?=[A-ZÁÉÍÓÚ])", m.group(1))]
    return [n for n in nomes if 2 <= len(n.split()) <= 6]


def resultado(seg):
    low = seg.lower()
    m = re.search(r"(rejeitad[oa]s?|reprovad[oa]s?|aprovad[oa]s?|retirad[oa]|adiad[oa]|baixad[oa] em diligência|pedido de vista)", low)
    return m.group(1) if m else None


def parse_session(s, roster):
    txt = clean(s["texto"])
    pres = sorted({c for n in presentes(txt) for c in roster.find_all(n)[:1]})
    refs = list(REF.finditer(txt))
    itens = []
    for i, m in enumerate(refs):
        fim = refs[i + 1].start() if i + 1 < len(refs) else len(txt)
        seg = txt[m.start():fim]
        # pareceres repetem a ref do projeto; só vale o texto até a próxima leitura
        tipo = tipo_norm(m.group(1))
        num, ano = int(m.group(2)), int(m.group(3))
        if abs(ano - int(s["data"][-4:])) > 1:  # erro de OCR no ano (ex.: 2921)
            ano = int(s["data"][-4:])
        antes = txt[max(0, m.start() - 40):m.start()].lower()
        parecer = "parecer" in antes or "pareceres" in antes
        res = resultado(seg)
        autor = re.search(r"de autoria (.{0,160})", seg)
        if autor:
            autor = re.match(r"(.*?)(?:\. | Em seguida| - )", autor.group(1) + ". ")
        contra = []
        mc = re.search(r"votos?\s*contr\w*\s*(.+?)(?:\.\s|Leitura|$)", seg, re.I)
        if mc:
            contra = roster.find_all(mc.group(1))
        abst = []
        ma = re.search(r"absten\w*\s*(?:-\s*se)?\s*(?:do voto)?\s*(.+?)(?:\.\s|Leitura|$)", seg, re.I)
        if ma:
            abst = roster.find_all(ma.group(1))
        unanime = "unanimidade" in seg.lower()
        if not res and tipo == "Indicação":
            res = "encaminhada"
        if not res:
            continue
        itens.append({
            "tipo": tipo, "numero": num, "ano": ano, "parecer": parecer,
            "autoria": roster.find_all(autor.group(1)) if autor else [],
            "resultado": ("rejeitada" if res.startswith(("rejeit", "reprov")) else "aprovada" if res.startswith("aprov") else res),
            "unanime": unanime and not contra and not abst,
            "contra": contra, "abstencoes": abst,
            "trecho": seg[:600].strip(),
        })
    return pres, itens


def build_roster(sessions):
    roster = Roster()
    for s in sessions:
        for n in presentes(clean(s["texto"] or "")):
            roster.add(n)
    # nome canônico = variante mais frequente do grupo; descarta ruído (poucas ocorrências ou nome contido em outro)
    grupos = [(v.most_common(1)[0][0], roster.counts[c]) for c, v in roster.variants.items()]
    grupos = [(n, k) for n, k in grupos if k >= 5]
    grupos = [(n, k) for n, k in grupos if not any(
        o != n and (plain(o) in plain(n) or plain(n) in plain(o)) and (k2 > k or (k2 == k and o < n)) for o, k2 in grupos)]
    final = Roster()
    final.canon = [n for n, _ in grupos]
    final.counts = Counter(dict(grupos))
    return final


SITUACAO_SISCAM = {"aprovada": "aprovada", "rejeitada": "rejeitada", "retirado": "retirada", "em andamento": "em andamento"}
TIPOS_MATERIA = {"Indicação", "Requerimento", "Moção", "Projeto de Lei", "Projeto de Lei Complementar", "Projeto de Resolução", "Projeto de Decreto Legislativo"}


def estimar_pls(pautas):
    """Descrição estimada dos PLs: resumo da ementa da lei sancionada que provavelmente corresponde (ver associar_pls.py)."""
    arq_assoc, arq_res = RAW / "associacoes.json", Path(__file__).parent / "resumos_pl.json"
    if not (arq_assoc.exists() and arq_res.exists()):
        return
    assoc = json.load(open(arq_assoc, encoding="utf-8"))
    resumos = json.load(open(arq_res, encoding="utf-8"))
    n = 0
    for p in pautas:
        a = assoc.get(f"{p['tipo']}|{p['numero']}|{p['ano']}")
        r = a and resumos.get(f"{int(a['lei_complementar'])}-{a['lei_numero']}")
        if r and not p.get("descricao"):
            p["descricao"] = r
            p["descricao_estimada"] = True
            p["lei"] = {"numero": a["lei_numero"], "complementar": a["lei_complementar"], "data": a["lei_data"], "url": a["lei_url"], "ementa": a["ementa"]}
            n += 1
    print(f"descrições estimadas de PL: {n} eventos")


def integrar_docs(pautas, roster):
    """Anexa descrição e link às pautas das atas; devolve matérias do Siscam que não aparecem em nenhuma ata (ex.: 2024 e 2026)."""
    docs = json.load(open(RAW / "docs.json", encoding="utf-8"))
    por_chave = {(d["tipo"], d["numero"], d["ano"]): d for d in docs if d["tipo"] in TIPOS_MATERIA}
    usadas = set()
    for p in pautas:
        d = por_chave.get((p["tipo"], p["numero"], p["ano"]))
        p["descricao"] = curta(d["assunto"], d["tipo"]) if d else None
        p["doc_url"] = d["arquivo"] if d else None
        if d:
            usadas.add((d["tipo"], d["numero"], d["ano"]))
    estimar_pls(pautas)
    extra = []
    for chave, d in por_chave.items():
        if chave in usadas or d["ano"] < 2021 or not d["data"]:
            continue
        dd, mm, aa = d["data"].split("/")
        extra.append({
            "tipo": d["tipo"], "numero": d["numero"], "ano": d["ano"], "data_iso": f"{aa}-{mm}-{dd}",
            "resultado": SITUACAO_SISCAM.get((d["situacao"] or "").lower(), (d["situacao"] or "").lower()),
            "autoria": sorted({c for n in (d["autoria"] or "").split(",") for c in roster.find_all(n.title())[:1]}),
            "descricao": curta(d["assunto"], d["tipo"]), "doc_url": d["arquivo"],
        })
    extra.sort(key=lambda x: x["data_iso"], reverse=True)
    com = sum(1 for p in pautas if p["descricao"])
    print(f"descrições: {com}/{len(pautas)} pautas de ata; {len(extra)} matérias só no Siscam")
    return extra


def main():
    sessions = json.load(open(RAW / "sessions.json", encoding="utf-8"))
    roster = build_roster(sessions)
    out_sessions, out_pautas = [], []
    for s in sessions:
        base = {k: s[k] for k in ("id", "titulo", "data", "fim", "video")}
        base["ata_url"] = f"http://consulta.siscam.com.br/camaranevespaulista/arquivo?Id={s['ata_id']}" if s["ata_id"] else None
        base["url"] = f"http://consulta.siscam.com.br/camaranevespaulista/Sessoes/Sessao/{s['id']}"
        d, mth, y = s["data"].split("/")
        base["data_iso"] = f"{y}-{mth}-{d}"
        txt = s["texto"] or ""
        if len(re.sub(r"\s+", "", txt)) < 800:
            base.update(status="sem-texto", presentes=[], pautas=[])
            out_sessions.append(base)
            continue
        pres, itens = parse_session(s, roster)
        for n, it in enumerate(itens):
            it["id"] = f"{base['data_iso']}-{n:02d}"
            it["sessao"] = s["id"]
            it["data_iso"] = base["data_iso"]
        base.update(status="ok", presentes=pres, pautas=[i["id"] for i in itens])
        out_sessions.append(base)
        out_pautas += itens
    out_extra = integrar_docs(out_pautas, roster)
    out_sessions.sort(key=lambda x: x["data_iso"], reverse=True)
    (OUT / "materias_siscam.json").write_text(json.dumps(out_extra, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "sessoes.json").write_text(json.dumps(out_sessions, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "pautas.json").write_text(json.dumps(out_pautas, ensure_ascii=False, indent=1), encoding="utf-8")
    (RAW / "roster.json").write_text(json.dumps(roster.counts.most_common(), ensure_ascii=False, indent=1), encoding="utf-8")
    atuais = json.load(open(RAW / "vereadores.json", encoding="utf-8"))
    out_ver = []
    for c in roster.canon:
        siscam = next((v for v in atuais if c in roster.find_all(v["nome"].title())), None)
        out_ver.append({
            "slug": re.sub(r"[^a-z]+", "-", plain_sp(c)).strip("-"),
            "nome": c,
            "partido": siscam["partido"] if siscam else None,
            "atual": bool(siscam),
            "siscam_id": siscam["siscam_id"] if siscam else None,
            "sessoes_presente": sum(1 for x in out_sessions if c in x["presentes"]),
        })
    out_ver.sort(key=lambda v: (not v["atual"], v["nome"]))
    (OUT / "vereadores.json").write_text(json.dumps(out_ver, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len([s for s in out_sessions if s["status"] == "ok"]), "sessões com texto;", len(out_pautas), "pautas")
    print(Counter(p["resultado"] for p in out_pautas))
    print("com contra:", sum(1 for p in out_pautas if p["contra"]))


if __name__ == "__main__":
    main()
