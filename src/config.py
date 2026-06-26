"""
Fonte única de verdade do projeto.

Tudo que é "decisão de escopo" ou "mapa feito à mão" mora aqui, pra que
nenhum script tenha sua própria cópia divergente. Se você quer entender as
escolhas do projeto, comece por este arquivo.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

# ── Caminhos ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
CSV_DIR = ROOT / "csv"                    # CSVs crus do BC (não versionados)
DATA_RAW = ROOT / "data" / "raw"          # preços crus baixados (não versionados)
DATA_PROC = ROOT / "data" / "processed"   # tudo que tratamos (auditável)

# ── Escopo temporal ─────────────────────────────────────────────────────────
# O BC só publica trimestral a partir de 2017. Antes era mensal/semestral,
# com universo de bancos menor. Decisão: event study só no trimestral.
ANO_INICIO = 2017

# Nomes possíveis do arquivo de reclamações (o BC mudou o layout em 2024Q3).
ARQ_RECLAMACOES_NOVO = (
    "Bancos+e+financeiras+-+Reclamacoes+por+instituicao+financeira+e+conglomerado.csv"
)
ARQ_RECLAMACOES_ANTIGO = (
    "Bancos+e+financeiras+-+Reclamacoes+e+quantidades+de+clientes+por+instituicao+financeira.csv"
)

# ── Mapa nome-no-BC → ticker B3 (feito à mão) ───────────────────────────────
# Busca por substring gera falso positivo (ex.: "ITA" casa em "CNH INDUSTRIAL"),
# por isso o mapa é explícito. Chave = nome exato do conglomerado no CSV do BC.
MAPA_TICKER: dict[str, str] = {
    "ITAU": "ITUB4",
    "BRADESCO": "BBDC4",
    "BB": "BBAS3",
    "SANTANDER": "SANB11",
    "BTG PACTUAL/BANCO PAN": "BPAC11",
    "BANRISUL": "BRSR6",
    "ABC-BRASIL": "ABCB4",
    "BANESTES": "BEES3",
    "BMG": "BMGB4",
    "MERCANTIL DO BRASIL": "BMEB4",
    "SOFISA": "SFSA4",
    # BDRs — tratados à parte (ver IS_BDR). Mantidos no mapa pra rastrear.
    "NUBANK": "ROXO34",
    "INTER": "INBR",
}

# BDRs: papel doméstico é recibo de ação negociada lá fora (NYSE/Nasdaq).
# A reação ao ranking do BC é contaminada por câmbio e pelo mercado americano.
# Marcamos e deixamos FORA da análise principal (entram só como robustez).
IS_BDR: set[str] = {"ROXO34", "INBR"}

# Bancos com índice (F1) sólido — presente em (quase) todos os trimestres em
# que aparecem. SÓ estes entram no ablation central "índice cru vs. severidade
# LLM", porque o ablation exige F1 nos dois lados da comparação.
#
# Decisão (ver docs/tratamento_dados.md §5): NÃO reconstruímos um índice caseiro
# para os demais. O BC não calcular o índice é informação — significa volume de
# reclamações abaixo do limiar material. Esses bancos (ABCB4, BEES3, SFSA4) têm
# sinal de reclamação fino E ação ilíquida (event study ruidoso). Ficam fora do
# head-to-head; ainda participam pela via do LLM (F4/F5), que lê o perfil de
# irregularidades e não depende do índice.
BANCOS_F1_SOLIDA: set[str] = {
    "ITUB4", "BBDC4", "BBAS3", "SANB11",
    "BMEB4", "BMGB4", "BRSR6", "BPAC11",
}

# Data em que o ticker passou a ser negociável na B3 (point-in-time).
# Tickers antigos recebem 2000-01-01 (= "muito antes do nosso recorte").
DATA_LISTAGEM: dict[str, dt.date] = {
    "ITUB4": dt.date(2000, 1, 1),
    "BBDC4": dt.date(2000, 1, 1),
    "BBAS3": dt.date(2000, 1, 1),
    "SANB11": dt.date(2009, 10, 7),
    "BPAC11": dt.date(2018, 4, 26),
    "BRSR6": dt.date(2000, 1, 1),
    "ABCB4": dt.date(2007, 7, 24),
    "BEES3": dt.date(2000, 1, 1),
    "BMGB4": dt.date(2019, 10, 29),
    "BMEB4": dt.date(2000, 1, 1),
    "SFSA4": dt.date(2007, 4, 30),
    "ROXO34": dt.date(2021, 12, 9),
    "INBR": dt.date(2022, 6, 23),
}


def num_br(s) -> float:
    """Número em formato brasileiro -> float. '1.665,06' -> 1665.06.

    Ponto = separador de milhar, vírgula = decimal. String vazia/espaço -> NaN.
    """
    import pandas as pd

    if pd.isna(s):
        return float("nan")
    s = str(s).strip()
    if not s or s.lower() == "nan":
        return float("nan")
    return float(s.replace(".", "").replace(",", "."))
