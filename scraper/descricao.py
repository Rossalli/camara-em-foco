"""Gera uma descrição curta (1-2 frases) a partir do campo "Assunto" das proposituras do Siscam."""
import re

PREAMBULO = re.compile(
    r"^.*?\b(?:abaixo assinad[oa]s?|nos termos (?:regimentais|do regimento interno)[^,.]*)[,\s]*(?:nos termos regimentais[,\s]*)?",
    re.I | re.S,
)
VERBO = re.compile(
    r"\b(INDICAM?|REQUEREM|REQUER|SOLICITAM?|PROP[OÕ]E|APRESENTA|MANIFESTA|CONGRATULA|HOMENAGEIA|REPUDIA)\b[:,]?\s*"
)
RUIDO = [
    r"\bao\s+Exm[oª]\.?\s*(?:\(a\)\s*)?Sr\.?(?:\(a\))?\s*Prefeit[oa](?:\s+Municipal)?(?:\s+de Neves Paulista)?",
    r"\bpor meio d[ao]s?\s+",
    r"\bsolicitando-lhe\b",
    r"\bo seguinte pedido de informa[cç][aã]o:?",
    r"\bdo Poder Executivo\b",
]
INICIO = [
    (r"^\d+\s*[-–.)]+\s*[-.]?\s*", ""),
    (r"^que seja encaminhado\s*,?\s*(?:of[ií]cio\s*,?\s*)?(?:ao Exm[^,]*,\s*)?(?:que\s+)?", ""),
    (r"^(?:solicitando(?:-lhe)? )?(?:que )?seja (?:analisada|vista|estudada|verificada) a (possibilidade|viabilidade[^,]*?) d[eao]\s+", r"Avaliar a \1 de "),
    (r"^(?:solicitando(?:-lhe)? )?(?:que )?seja (?:analisada|vista|estudada|verificada) a (possibilidade|viabilidade)\b", r"Avaliar a \1"),
]
SO_PREAMBULO = re.compile(
    r"(?:(?:Vereador|Vereadora|Vereadores)\w*\s+da\s+C[âa]mara\s+Municipal\s+de(?:\s+Neves\s+Paulista)?[\s,]*(?:abaixo)?|\babaixo)\W*$", re.I
)


SO_QUALIFICACAO = re.compile(
    r"\b(?:Vereador|Vereadora|Vereadores)\w*\b|\bda\s+C\S{0,3}mara(?:\s+Municipal)?(?:\s+de(?:\s+Neves(?:\s+Paulista)?)?)?", re.I
)
SO_DESTINATARIO = re.compile(
    r"^(?:(?:ao|[àa]|aos)\s+exm|que oficie o setor respons[áa]vel|solicitando[- ]?(?:lhe)?\s+o seguinte pedido)", re.I
)


def sem_conteudo(t):
    """True quando sobrou só nome/qualificação de autor ou só o destinatário, sem dizer do que se trata."""
    resto = re.sub(r"\s+[e¢]\s+|[,.;]", " ", SO_QUALIFICACAO.sub("", t)).strip()
    if not resto or resto == resto.upper():  # só nomes (em caixa alta) dos vereadores
        return True
    return bool(SO_DESTINATARIO.match(t)) and len(t) < 90


FRACA_FIM = re.compile(
    r"\b(?:as|os|nos|nas|um|uma|uns|umas|em|de|do|da|dos|das|a|o|e|que|para|entre|com|no|na|ao|consistindo em|sejam providenciadas|denominada a rua|empresa especializada)\.?$",
    re.I,
)
FRACA_INICIO = re.compile(r"^(?:refor[çc]ando a indica[çc][ãa]o|referente a[o]?\b|de neves\b)", re.I)


def fraca(t):
    """True para descrição truncada ou que só remete a outro documento, sem dizer do que se trata."""
    return bool(FRACA_FIM.search(t.rstrip(". ")  + ".") or FRACA_INICIO.match(t))


def curta(assunto, tipo, limite=230):
    if not assunto:
        return None
    t = re.sub(r"\s+", " ", assunto).strip()
    t = re.split(r"\bJUSTIFICATIVA\b|\bJustificativa\b", t)[0].strip()
    if SO_PREAMBULO.search(t) and len(t) < 220:
        return None  # texto truncado no sistema, só sobrou a qualificação do autor
    m = VERBO.search(t)
    if m:
        t = t[m.end():]
    else:
        t = PREAMBULO.sub("", t, count=1)
    for r in RUIDO:
        t = re.sub(r, "", t, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip(" :,;.-")
    for padrao, troca in INICIO:
        t = re.sub(padrao, troca, t, flags=re.I).strip(" :,;.-")
    if len(t) < 30 or sem_conteudo(t):
        return None
    t = t[0].upper() + t[1:]
    if len(t) > limite:
        corte = t[:limite]
        ponto = max(corte.rfind(". "), corte.rfind("; "))
        t = corte[: ponto + 1] if ponto > 80 else corte.rsplit(" ", 1)[0] + "…"
    elif not t.endswith((".", "?", "!")):
        t += "."
    if not t.endswith("…") and fraca(t):
        return None
    return t
