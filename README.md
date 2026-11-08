# Câmara em Foco

Site estático (Astro) com as sessões da Câmara Municipal de Neves Paulista: resumo, o que foi votado, quem votou contra, por sessão, por pauta e por vereador.

## Como funciona

1. `scraper/fetch.py` baixa sessões e atas (PDF) do Siscam e extrai o texto com `pdftotext` (poppler precisa estar no PATH). O cache fica em `scraper/raw/`, ignorado pelo git.
2. `scraper/parse.py` lê o texto das atas e gera `data/sessoes.json`, `data/pautas.json` e `data/vereadores.json`.
3. O Astro gera as páginas a partir desses JSON.

```
npm install
npm run dados   # atualiza os dados (fetch + parse)
npm run dev     # http://localhost:4321
npm run build
```

## Limites conhecidos

- Atas de 2016 a 2020 e parte de 2021 são imagens sem texto; precisam de OCR.
- O Siscam não tem sessões de 2024 nem de 2026.
- A ata só nomeia votos contra e abstenções, não os votos a favor.
- A extração é por regex sobre texto com ruído de OCR; confira os casos importantes na ata original.
