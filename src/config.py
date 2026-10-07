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
# O BC só publica trimestral a partir de 2017. Antes era mensal/semestral.
# O ETL trata TODOS os trimestres (a F2/aceleração precisa do trimestre t-1),
# mas o EVENT STUDY usa só os eventos com data de divulgação confirmada — ver
# DATAS_DIVULGACAO abaixo.
ANO_INICIO = 2017

# ── Datas de divulgação do ranking (EVENT STUDY) ────────────────────────────
# Decisão de escopo: o calendário OFICIAL do BC só vai até 2022. Para 2017-2021
# as datas só existem em notícias (imprecisas), o que sujaria o dia 0. Optamos
# por restringir o event study a 2022+, onde toda data é exata e defensável.
#
# Sem fórmula: o BC mudou o esquema de divulgação (2022+ cai em quinta/terça
# irregular, não há regra de calendário que acerte). Esta tabela É a verdade,
# copiada do calendário oficial (ranking de Bancos; ignorados os de Consórcio).
# 2022 Q2 não existe (transição de metodologia do BC).
DATAS_DIVULGACAO: dict[tuple[int, int], "dt.date"] = {
    (2022, 1): dt.date(2022, 7, 21),   # atrasado (transição de metodologia)
    (2022, 3): dt.date(2022, 10, 20),
    (2022, 4): dt.date(2023, 1, 19),
    (2023, 1): dt.date(2023, 4, 20),
    (2023, 2): dt.date(2023, 7, 25),   # terça
    (2023, 3): dt.date(2023, 10, 31),  # terça
    (2023, 4): dt.date(2024, 1, 25),
    (2024, 1): dt.date(2024, 4, 25),
    (2024, 2): dt.date(2024, 7, 30),   # terça
    (2024, 3): dt.date(2024, 10, 24),
    (2024, 4): dt.date(2025, 1, 23),
    (2025, 1): dt.date(2025, 4, 24),
    (2025, 2): dt.date(2025, 7, 24),
    (2025, 3): dt.date(2025, 10, 23),
    (2025, 4): dt.date(2026, 1, 22),
    # (2026, 1): FALTA — pegar do calendário (divulgado ~abr/2026)
}

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
