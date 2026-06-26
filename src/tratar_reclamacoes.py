"""
ETL das reclamações do BC: CSVs crus (2 formatos) → uma tabela tidy auditável.

Entrada:  csv/{ano}/{q} trimestre/Bancos+...+Reclamacoes...csv
Saída:    data/processed/reclamacoes_conglomerados.csv  (1 linha por banco×trimestre)
          data/processed/tratamento_log.txt             (rastro de cada etapa)

Cada etapa imprime quantas linhas entraram/saíram, pra você seguir o tratamento
sem ler o código. A lógica completa está em docs/tratamento_dados.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

# console do Windows é cp1252; força UTF-8 pra não quebrar em acento/seta
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as cfg


import unicodedata


def _norm(s: str) -> str:
    """'Quantidade total de reclamações' -> 'quantidadetotaldereclamacoes'.

    Remove acentos e tudo que não é letra/dígito, pra casar coluna por
    palavra-chave sem depender de acento ou caractere de encoding.
    """
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return "".join(c.lower() for c in s if c.isalnum())


def _resolver(df: pd.DataFrame, candidatos: list[tuple[set, set]]) -> pd.Series:
    """Acha a coluna por palavras-chave (inclui todas / exclui qualquer).

    'candidatos' é uma lista em ordem de prioridade: tenta o 1º, depois o 2º...
    Cada candidato é (termos_obrigatorios, termos_proibidos). Devolve a coluna
    ou uma série de NaN se nenhum candidato casar (campo ausente neste layout).
    """
    normcols = {c: _norm(c) for c in df.columns}
    for inclui, exclui in candidatos:
        for col, n in normcols.items():
            if all(t in n for t in inclui) and not any(t in n for t in exclui):
                return df[col]
    return pd.Series([pd.NA] * len(df), index=df.index)


# Campos lógicos -> candidatos de coluna, em ordem de prioridade.
# A diversidade de candidatos reflete os 6 layouts do BC (ver docs).
CANDIDATOS = {
    "indice": [({"indice"}, set())],
    "recl_total": [
        ({"total", "reclamacoes", "analisadas"}, set()),          # layout 6
        ({"total", "reclamacoes"}, {"cliente", "respondidas"}),   # layouts 1-4
        ({"total", "reclamacoes", "respondidas"}, {"cliente"}),   # layout 5
    ],
    "recl_procedentes": [
        ({"procedentes"}, {"extrapoladas"}),   # layouts 1-4 e 6 (def. "estrita")
        ({"procedentes", "extrapoladas"}, set()),  # layout 5 (só extrapolada)
    ],
    "clientes": [({"total", "clientes"}, set())],  # ausente no layout 6
}


def detectar_arquivo(q_dir: Path) -> Path | None:
    for arq in (cfg.ARQ_RECLAMACOES_NOVO, cfg.ARQ_RECLAMACOES_ANTIGO):
        if (q_dir / arq).exists():
            return q_dir / arq
    return None


def extrair_conglomerados(csv: Path) -> pd.DataFrame:
    """Lê um CSV (qualquer um dos 6 layouts) e devolve as linhas-mãe."""
    df = pd.read_csv(csv, sep=";", encoding="latin-1")

    if "Conglomerado" in df.columns:
        # layout novo: Conglomerado preenchido E Instituição financeira vazia
        cong = df["Conglomerado"].astype(str).str.strip()
        inst = df["Instituição financeira"].astype(str).str.strip()
        mask = (
            df["Conglomerado"].notna()
            & cong.ne("") & cong.ne("nan")
            & (df["Instituição financeira"].isna() | inst.eq("") | inst.eq("nan"))
        )
        nome = cong
    else:
        # layouts antigos: Tipo == 'Conglomerado'; nome em IF com '(conglomerado)'
        mask = df["Tipo"].astype(str).str.strip().eq("Conglomerado")
        nome = (
            df["Instituição financeira"].astype(str).str.strip()
            .str.replace(r"\s*\(conglomerado\)\s*$", "", regex=True)
        )

    def campo(nome_logico: str) -> pd.Series:
        return _resolver(df, CANDIDATOS[nome_logico])[mask].map(cfg.num_br).values

    return pd.DataFrame(
        {
            "banco_bc": nome[mask].values,
            "categoria": df.loc[mask, "Categoria"].astype(str).str.strip().values,
            "indice": campo("indice"),
            "recl_total": campo("recl_total"),
            "recl_procedentes": campo("recl_procedentes"),
            "clientes": campo("clientes"),
        }
    )


def main() -> None:
    log_linhas: list[str] = []

    def log(msg: str) -> None:
        print(msg)
        log_linhas.append(msg)

    log("=" * 70)
    log("TRATAMENTO DAS RECLAMAÇÕES DO BC")
    log("=" * 70)

    frames = []
    for ano_dir in sorted(cfg.CSV_DIR.iterdir()):
        if not ano_dir.is_dir():
            continue
        try:
            ano = int(ano_dir.name)
        except ValueError:
            continue
        if ano < cfg.ANO_INICIO:
            continue
        for q in (1, 2, 3, 4):
            q_dir = ano_dir / f"{q} trimestre"
            csv = detectar_arquivo(q_dir)
            if csv is None:
                continue
            sub = extrair_conglomerados(csv)
            sub.insert(0, "ano", ano)
            sub.insert(1, "trimestre", q)
            frames.append(sub)
            log(f"  {ano} Q{q} → {len(sub):3d} conglomerados")

    df = pd.concat(frames, ignore_index=True)
    log("")
    log(f"[1] Linhas-mãe extraídas (todos os bancos):      {len(df):5d}")

    # ── Mapeia ticker e marca universo ──────────────────────────────────────
    df["ticker"] = df["banco_bc"].map(cfg.MAPA_TICKER)
    df["no_universo"] = df["ticker"].notna()
    df["eh_bdr"] = df["ticker"].isin(cfg.IS_BDR)
    # entra no ablation central F1-vs-LLM? (ver config.BANCOS_F1_SOLIDA)
    df["f1_solida"] = df["ticker"].isin(cfg.BANCOS_F1_SOLIDA)
    n_univ = df["no_universo"].sum()
    log(f"[2] Linhas no nosso universo (têm ticker):       {n_univ:5d}")
    log(f"      dos quais BDR (ROXO34/INBR):               {df['eh_bdr'].sum():5d}")

    # ── Feature derivada: razão procedente/total (F3 candidata) ─────────────
    df["razao_procedente"] = df["recl_procedentes"] / df["recl_total"]
    df.loc[df["recl_total"].fillna(0).eq(0), "razao_procedente"] = pd.NA

    # ── Diagnóstico de completude do índice (F1) no universo ────────────────
    univ = df[df["no_universo"]]
    sem_indice = univ["indice"].isna().sum()
    log(f"[3] No universo, linhas SEM índice (F1 ausente): {sem_indice:5d}")
    if sem_indice:
        faltantes = univ[univ["indice"].isna()]
        log("      bancos com índice ausente em algum trimestre:")
        for tk, n in faltantes["ticker"].value_counts().items():
            log(f"        {tk}: {n} trimestre(s)")

    # ── Salva ───────────────────────────────────────────────────────────────
    cfg.DATA_PROC.mkdir(parents=True, exist_ok=True)
    out = cfg.DATA_PROC / "reclamacoes_conglomerados.csv"
    # ordena colunas pra leitura humana
    ordem = [
        "ano", "trimestre", "banco_bc", "ticker", "no_universo",
        "eh_bdr", "f1_solida", "categoria", "indice", "recl_total",
        "recl_procedentes", "razao_procedente", "clientes",
    ]
    df[ordem].to_csv(out, sep=";", index=False, encoding="utf-8-sig")
    log("")
    log(f"[4] Salvo: {out.relative_to(cfg.ROOT)}")
    log(f"      → abra no Excel: {len(df)} linhas, {len(ordem)} colunas")

    # também uma versão só do universo, mais fácil de inspecionar
    out_univ = cfg.DATA_PROC / "reclamacoes_universo.csv"
    univ[ordem].sort_values(["ticker", "ano", "trimestre"]).to_csv(
        out_univ, sep=";", index=False, encoding="utf-8-sig"
    )
    log(f"[5] Salvo (só universo): {out_univ.relative_to(cfg.ROOT)} ({len(univ)} linhas)")

    (cfg.DATA_PROC / "tratamento_log.txt").write_text(
        "\n".join(log_linhas), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
