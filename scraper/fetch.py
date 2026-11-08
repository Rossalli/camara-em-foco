"""Baixa sessões, atas (PDF -> texto) e vereadores do Siscam da Câmara de Neves Paulista.

Requer `pdftotext` (poppler) no PATH. Cache em scraper/raw/ (ignorado pelo git).
Uso: python scraper/fetch.py [--max-id 230]
"""
import html
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

BASE = "http://consulta.siscam.com.br/camaranevespaulista"
RAW = Path(__file__).parent / "raw"
(RAW / "atas").mkdir(parents=True, exist_ok=True)
(RAW / "sessoes").mkdir(parents=True, exist_ok=True)


def get(url, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": "camara-em-foco/0.1 (projeto cívico)"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                data = r.read()
            return data if binary else data.decode("utf-8", "replace")
        except Exception:
            time.sleep(1 + attempt)
    return None


def cached_page(path, url):
    if not path.exists():
        page = get(url)
        if page is None:
            return None
        path.write_text(page, encoding="utf-8")
        time.sleep(0.2)
    return path.read_text(encoding="utf-8")


def fetch_sessions(max_id):
    for sid in range(1, max_id + 1):
        page = cached_page(RAW / "sessoes" / f"{sid}.html", f"{BASE}/Sessoes/Sessao/{sid}")
        if not page:
            continue
        title = re.search(r"<title>[^<]*Sessões - ([^<]+)</title>", page)
        data = re.search(r"Data:</strong>\s*(\d\d/\d\d/\d{4})", page)
        if not title or not data:
            continue
        ata = re.search(r'href="/arquivo\?Id=(\d+)"', page)
        video = re.search(r'href="([^"]+)"[^>]*>\s*Assista', page)
        end = re.search(r"Hora T[ée]rmino:</strong>\s*([\d:]+)", page)
        yield {
            "id": sid,
            "titulo": html.unescape(title.group(1)).strip(),
            "data": data.group(1),
            "fim": end.group(1) if end else None,
            "ata_id": ata.group(1) if ata else None,
            "video": html.unescape(video.group(1)) if video else None,
        }


def ata_text(ata_id):
    txt = RAW / "atas" / f"{ata_id}.txt"
    if not txt.exists():
        pdf = RAW / "atas" / f"{ata_id}.pdf"
        data = get(f"{BASE}/arquivo?Id={ata_id}", binary=True)
        if not data:
            return None
        pdf.write_bytes(data)
        subprocess.run(["pdftotext", "-enc", "UTF-8", str(pdf), str(txt)], check=False)
        time.sleep(0.2)
    return txt.read_text(encoding="utf-8", errors="replace") if txt.exists() else None


def fetch_vereadores():
    out = []
    for path, atual in (("vereadores", True), ("vereadores/Anteriores", False)):
        page = cached_page(RAW / f"{path.replace('/', '_')}.html", f"{BASE}/{path}")
        if not page:
            continue
        for vid, nome, partido in re.findall(
            r'<h4><a href="/Vereadores/Vereador/(\d+)">([^<]+)</a></h4>\s*<p>\s*<strong>Partido:</strong>\s*([^<]*?)\s*</p>', page
        ):
            out.append({"siscam_id": int(vid), "nome": html.unescape(nome).strip(), "partido": partido.strip(), "atual": atual})
    return out


if __name__ == "__main__":
    import json
    max_id = int(sys.argv[sys.argv.index("--max-id") + 1]) if "--max-id" in sys.argv else 230
    sessions = []
    for s in fetch_sessions(max_id):
        s["texto"] = ata_text(s["ata_id"]) if s["ata_id"] else None
        sessions.append(s)
        print(s["id"], s["titulo"], s["data"], "ata" if s["texto"] else "SEM ATA", flush=True)
    (RAW / "sessions.json").write_text(json.dumps(sessions, ensure_ascii=False), encoding="utf-8")
    ver = fetch_vereadores()
    (RAW / "vereadores.json").write_text(json.dumps(ver, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(sessions), "sessões,", len(ver), "vereadores")
