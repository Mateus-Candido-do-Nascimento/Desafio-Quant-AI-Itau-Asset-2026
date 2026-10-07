"""
Teste 1 — Eventos limpos (point-in-time).

Pergunta: para cada (banco × trimestre de divulgação), o banco já estava
listado na B3 na data do evento? Quantos pares válidos sobram pro event study?

Não constrói modelo. Lê a tabela JÁ TRATADA (reclamacoes_universo.csv) e aplica
o filtro point-in-time. Toda a parte de parsing/limpeza vive em
tratar_reclamacoes.py — aqui é só viabilidade.

Saída:
  data/processed/eventos.csv         — os 36 eventos com data de divulgação
  data/processed/pares_validos.csv   — banco × evento que entram no estudo
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as cfg

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# Datas de divulgação: NÃO há fórmula (o BC mudou o esquema). A verdade está em
# config.DATAS_DIVULGACAO, copiada do calendário oficial. Ver config.py.


# ── Teste ────────────────────────────────────────────────────────────────────
def main() -> None:
    universo = cfg.DATA_PROC / "reclamacoes_universo.csv"
    if not universo.exists():
        raise SystemExit(
            f"Faltou {universo.name}. Rode primeiro: python src/tratar_reclamacoes.py"
        )

    df = pd.read_csv(universo, sep=";")
    print("=" * 64)
    print("TESTE 1 — EVENTOS LIMPOS (point-in-time)")
    print("=" * 64)
    print(f"Aparições banco × trimestre no universo (todos os anos): {len(df)}")

    # data de divulgação: só os (ano, trimestre) com data confirmada entram no
    # event study. Os demais (2017-2021, sem data exata) saem aqui.
    df["data_div"] = df.apply(
        lambda r: cfg.DATAS_DIVULGACAO.get((int(r["ano"]), int(r["trimestre"]))),
        axis=1,
    )
    n_antes_escopo = len(df)
    df = df[df["data_div"].notna()].copy()
    print(f"Após restringir aos {len(cfg.DATAS_DIVULGACAO)} eventos com data "
          f"oficial (2022+): {len(df)}  (-{n_antes_escopo - len(df)})")

    # point-in-time: o ticker já era negociável na data da divulgação?
    df["data_listagem"] = df["ticker"].map(cfg.DATA_LISTAGEM)
    df["ja_listado"] = df.apply(
        lambda r: r["data_listagem"] <= r["data_div"], axis=1
    )

    # ── Filtros em camadas (cada um reportado) ──────────────────────────────
    n_total = len(df)
    apos_pit = df[df["ja_listado"]]
    apos_bdr = apos_pit[~apos_pit["eh_bdr"]]
    apos_f1 = apos_bdr[apos_bdr["f1_solida"]]

    print()
    print("Funil de pares banco × evento:")
    print(f"  [0] no universo:                     {n_total:4d}")
    print(f"  [1] após point-in-time (já listado): {len(apos_pit):4d}"
          f"   (-{n_total - len(apos_pit)})")
    print(f"  [2] após remover BDR:                {len(apos_bdr):4d}"
          f"   (-{len(apos_pit) - len(apos_bdr)})")
    print(f"  [3] só bancos com F1 sólida:         {len(apos_f1):4d}"
          f"   (-{len(apos_bdr) - len(apos_f1)})   <- amostra do ablation")

    print()
    print("Pares válidos (pós point-in-time, sem BDR) por ticker:")
    print(apos_bdr["ticker"].value_counts().to_string())

    print()
    por_evento = apos_bdr.groupby(["ano", "trimestre"]).size()
    print("Bancos por evento (sem BDR):")
    print(f"  eventos: {por_evento.size}")
    print(f"  média:   {por_evento.mean():.1f}")
    print(f"  mínimo:  {por_evento.min()} em {tuple(por_evento.idxmin())}")
    print(f"  máximo:  {por_evento.max()} em {tuple(por_evento.idxmax())}")

    # ── Salva saídas auditáveis ─────────────────────────────────────────────
    eventos = (
        df[["ano", "trimestre", "data_div"]]
        .drop_duplicates()
        .sort_values(["ano", "trimestre"])
        .reset_index(drop=True)
    )
    eventos.to_csv(cfg.DATA_PROC / "eventos.csv", sep=";", index=False,
                   encoding="utf-8-sig")

    cols_out = ["ano", "trimestre", "data_div", "banco_bc", "ticker",
                "eh_bdr", "f1_solida", "indice", "razao_procedente"]
    apos_pit[cols_out].sort_values(["ano", "trimestre", "ticker"]).to_csv(
        cfg.DATA_PROC / "pares_validos.csv", sep=";", index=False,
        encoding="utf-8-sig"
    )

    print()
    print(f"Salvo: data/processed/eventos.csv ({len(eventos)} eventos)")
    print(f"Salvo: data/processed/pares_validos.csv ({len(apos_pit)} pares)")


if __name__ == "__main__":
    main()
