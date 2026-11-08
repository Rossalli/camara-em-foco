"""Baixa as proposituras do Siscam (tipo, número, data, situação, autoria, assunto).

Dá a descrição de cada matéria e cobre períodos sem ata (ex.: 2026).
Uso: python scraper/fetch_docs.py [--min-id 2600] [--max-id 4600]
Os ids abaixo de ~2600 são legislação antiga e proposituras até 2020 (sem atas com texto).
"""
import html
import json
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE = "http://consulta.siscam.com.br/camaranevespaulista/Documentos/Documento"
RAW = Path(__file__).parent / "raw"
CACHE = RAW / "docs"
CACHE.mkdir(parents=True, exist_ok=True)


def page(i):
    f = CACHE / f"{i}.html"
    if f.exists():
        return f.read_text(encoding="utf-8")
    for attempt in range(3):
        try:
            req = urllib.request.Request(f"{BASE}/{i}", headers={"User-Agent": "camara-em-foco/0.1 (projeto cívico)"})
            txt = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
            f.write_text(txt, encoding="utf-8")
            time.sleep(0.05)
            return txt
        except Exception:
            time.sleep(1 + attempt)
    return ""


def field(p, nome):
    m = re.search(nome + r":</strong>\s*([^<]*)", p)
    return html.unescape(m.group(1)).strip() if m else None


def parse(i):
    p = page(i)
    t = re.search(r"<h\d[^>]*>\s*([^<]*?N(?:&#186;|º)\s*\d+/\d{4})\s*</h", p)
    if not t:
        return None
    titulo = html.unescape(t.group(1))
    m = re.match(r"(.+?)\s*N[º]\s*(\d+)/(\d{4})", titulo)
    if not m:
        return None
    d = field(p, "Data")
    arq = re.search(r'href="(/arquivo\?Id=\d+)"', p)
    return {
        "doc_id": i, "tipo": m.group(1).strip(), "numero": int(m.group(2)), "ano": int(m.group(3)),
        "data": d, "situacao": field(p, "Situa(?:&#231;|ç)(?:&#227;|ã)o"), "regime": field(p, "Regime"),
        "autoria": field(p, "Autoria"), "assunto": field(p, "Assunto"),
        "arquivo": "http://consulta.siscam.com.br/camaranevespaulista" + arq.group(1) if arq else None,
    }


def listar_projetos():
    """Projetos de Lei (133) e Lei Complementar (134) não estão na faixa de ids varrida; lista pela busca."""
    ids = {}
    for tipo in (133, 134):
        pg = 1
        while True:
            url = f"http://consulta.siscam.com.br/camaranevespaulista/Documentos/Pesquisa?Pesquisa=Simples&id=80&pagina={pg}&Modulo=8&Documento={tipo}"
            t = urllib.request.urlopen(url, timeout=60).read().decode("utf-8", "replace")
            achados = re.findall(r'href="/Documentos/Documento/(\d+)"[^>]*title="(Projeto de Lei[^"]*?N(?:&#186;|º) \d+/\d{4})"', t)
            if not achados:
                break
            for i, _ in achados:
                ids[int(i)] = True
            pg += 1
    return sorted(ids)


if __name__ == "__main__":
    mx = int(sys.argv[sys.argv.index("--max-id") + 1]) if "--max-id" in sys.argv else 4600
    mn = int(sys.argv[sys.argv.index("--min-id") + 1]) if "--min-id" in sys.argv else 2600
    with ThreadPoolExecutor(16) as ex:
        docs = [d for d in ex.map(parse, list(range(mn, mx + 1)) + listar_projetos()) if d]
    (RAW / "docs.json").write_text(json.dumps(docs, ensure_ascii=False), encoding="utf-8")
    from collections import Counter
    print(len(docs), "documentos")
    print(Counter((d["tipo"], d["ano"]) for d in docs).most_common(60))
