"""Estima a lei sancionada que corresponde a cada Projeto de Lei aprovado.

O Siscam não liga PL e lei. Regra conservadora: numa sessão, se o número de PLs aprovados (ordinários ou
complementares, separadamente) é igual ao de leis sancionadas nos dias seguintes, e a ordem numérica bate,
associa um a um. Em qualquer outro caso o PL fica sem associação.

Uso: python scraper/associar_pls.py   -> scraper/raw/associacoes.json
"""
import datetime as dt
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
RAW = Path(__file__).parent / "raw"
JANELA_DIAS = 7


def data(s):
    a, b, c = s.split("/")
    return dt.date(int(c), int(b), int(a))


def main():
    pautas = json.load(open(ROOT / "data" / "pautas.json", encoding="utf-8"))
    leis = [l for l in json.load(open(RAW / "leis.json", encoding="utf-8")) if l["data"] and l["ementa"]]
    for l in leis:
        l["d"] = data(l["data"])

    # PLs aprovados em votação (não parecer), uma vez por matéria, na última aprovação
    aprov = {}
    for p in pautas:
        if p["tipo"] in ("Projeto de Lei", "Projeto de Lei Complementar") and not p["parecer"] and p["resultado"] == "aprovada":
            aprov[(p["tipo"], p["numero"], p["ano"])] = p
    por_dia = defaultdict(list)
    for chave, p in aprov.items():
        por_dia[(p["data_iso"], p["tipo"])].append((p["numero"], chave))

    saida, usadas = {}, set()
    for (iso, tipo), itens in sorted(por_dia.items()):
        d0 = dt.date.fromisoformat(iso)
        compl = tipo.endswith("Complementar")
        cand = [l for l in leis if l["complementar"] == compl and d0 <= l["d"] <= d0 + dt.timedelta(days=JANELA_DIAS) and l["doc_id"] not in usadas]
        itens.sort()
        cand.sort(key=lambda l: l["numero"])
        if len(itens) == len(cand) and itens:
            for (num, chave), lei in zip(itens, cand):
                usadas.add(lei["doc_id"])
                saida["|".join(map(str, chave))] = {
                    "lei_numero": lei["numero"], "lei_complementar": compl, "lei_data": lei["data"], "ementa": lei["ementa"],
                    "lei_url": lei["arquivo"], "confianca": "unico" if len(itens) == 1 else "ordem",
                }
    total = len(aprov)
    print(f"{len(saida)} de {total} PLs aprovados associados ({sum(1 for v in saida.values() if v['confianca'] == 'unico')} únicos, resto por ordem)")
    (RAW / "associacoes.json").write_text(json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
