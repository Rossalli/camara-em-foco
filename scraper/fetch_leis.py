"""Baixa leis ordinárias e complementares (módulo Legislação do Siscam): número, data, autoria e ementa.

Usadas para estimar a descrição dos Projetos de Lei, cujo texto não é publicado.
Uso: python scraper/fetch_leis.py
"""
import html
import json
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

B = "http://consulta.siscam.com.br/camaranevespaulista"
RAW = Path(__file__).parent / "raw"
(RAW / "leis").mkdir(parents=True, exist_ok=True)


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "camara-em-foco/0.1 (projeto cívico)"})
    return urllib.request.urlopen(req, timeout=90).read().decode("utf-8", "replace")


def listar(ano):
    ids = {}
    pg = 1
    while True:
        t = get(f"{B}/Documentos/Pesquisa?Pesquisa=Simples&id=81&pagina={pg}&Modulo=8&Documento=0&AnoInicial={ano}&AnoFinal={ano}")
        achados = re.findall(r'href="/Documentos/Documento/(\d+)"[^>]*title="(Lei (?:Ordin|Complementar)[^"]*)"', t)
        novos = [a for a in achados if int(a[0]) not in ids]
        if not novos:
            return ids
        for i, titulo in novos:
            ids[int(i)] = html.unescape(titulo)
        pg += 1


def detalhe(item):
    i, titulo = item
    f = RAW / "leis" / f"{i}.html"
    p = f.read_text(encoding="utf-8") if f.exists() else get(f"{B}/Documentos/Documento/{i}")
    f.write_text(p, encoding="utf-8")

    def campo(n):
        m = re.search(n + r":</strong>\s*([^<]*)", p)
        return html.unescape(m.group(1)).strip() if m else None

    num = re.search(r"N[ºo]\s*([\d.]+)", titulo)
    arq = re.search(r'href="(/arquivo\?Id=\d+)"', p)
    return {
        "doc_id": i, "titulo": titulo, "complementar": "Complementar" in titulo,
        "numero": int(num.group(1).replace(".", "")) if num else None,
        "data": campo("Data"), "autoria": campo("Autoria"), "ementa": campo("Assunto"),
        "classificacao": campo("Classifica(?:&#231;|ç)(?:&#227;|ã)o"),
        "arquivo": B + arq.group(1) if arq else None,
    }


if __name__ == "__main__":
    todos = {}
    for ano in range(2021, 2026):
        got = listar(ano)
        print(ano, len(got), "leis", flush=True)
        todos.update(got)
    with ThreadPoolExecutor(8) as ex:
        leis = list(ex.map(detalhe, sorted(todos.items())))
    (RAW / "leis.json").write_text(json.dumps(leis, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(leis), "leis salvas")
