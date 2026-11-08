"""Resume em linguagem simples a ementa das leis associadas aos PLs, usando a API da Anthropic.

Requer ANTHROPIC_API_KEY. Resultado em scraper/resumos_pl.json (versionado) (chave: "<complementar>-<numero>").
Uso: python scraper/resumir_pls.py
"""
import json
import os
import urllib.request
from pathlib import Path

RAW = Path(__file__).parent / "raw"
MODELO = "claude-sonnet-5-5"
LOTE = 25

PROMPT = """Você escreve descrições para um site cívico que acompanha a Câmara Municipal de Neves Paulista (SP).
Para cada item abaixo, recebe a ementa oficial de uma lei. Escreva UMA frase curta (até 180 caracteres) em português simples,
dizendo do que a lei trata, para um morador sem formação jurídica entender.
Regras: use só o que está na ementa, sem inventar valores, nomes ou detalhes; não comece com "Esta lei"; sem juridiquês.
Responda apenas com JSON: {"<id>": "<frase>", ...}.

Itens:
"""


def chamar(itens):
    corpo = {
        "model": MODELO,
        "max_tokens": 4000,
        "messages": [{"role": "user", "content": PROMPT + json.dumps(itens, ensure_ascii=False)}],
    }
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(corpo).encode(),
        headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01", "content-type": "application/json"},
    )
    resp = json.loads(urllib.request.urlopen(req, timeout=180).read())
    texto = "".join(b["text"] for b in resp["content"] if b["type"] == "text")
    return json.loads(texto[texto.index("{"): texto.rindex("}") + 1])


def main():
    assoc = json.load(open(RAW / "associacoes.json", encoding="utf-8"))
    arq = Path(__file__).parent / "resumos_pl.json"
    resumos = json.load(open(arq, encoding="utf-8")) if arq.exists() else {}
    pend = {}
    for v in assoc.values():
        k = f"{int(v['lei_complementar'])}-{v['lei_numero']}"
        if k not in resumos:
            pend[k] = v["ementa"]
    print(len(pend), "ementas a resumir")
    itens = list(pend.items())
    for i in range(0, len(itens), LOTE):
        resumos.update({k: t.strip() for k, t in chamar(dict(itens[i:i + LOTE])).items() if k in pend})
        arq.write_text(json.dumps(resumos, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  {min(i + LOTE, len(itens))}/{len(itens)}", flush=True)


if __name__ == "__main__":
    main()
