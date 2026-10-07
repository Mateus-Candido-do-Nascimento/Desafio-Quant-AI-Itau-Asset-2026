"""
Baixa preços diários (fechamento ajustado) dos bancos do universo + Ibovespa.

Fonte: yfinance (Yahoo). Escolhida por ser gratuita e REPRODUTÍVEL — qualquer
um da banca roda este script e obtém a mesma base (ver docs). Bloomberg seria
gold standard mas não é reproduzível sem terminal.

Só baixa e reporta qualidade. O cálculo de retorno/event study vive em outro
módulo (separação de responsabilidades).

Saída:
  data/raw/precos/{ticker}.csv         — cru do Yahoo, um por ticker (auditável)
  data/processed/precos_ajustados.csv  — fechamento ajustado, formato largo
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import pandas as pd
import yfinance as yf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as cfg

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DATA_INICIO = "2016-01-01"   # folga antes do 1º evento (abr/2017) p/ estimação
INDICE_MERCADO = "^BVSP"     # Ibovespa, o R_m do modelo de mercado


def tickers_para_baixar() -> list[str]:
    """11 não-BDR do universo + Ibovespa. BDR fica fora (ver config.IS_BDR)."""
    acoes = sorted(
        t for t in set(cfg.MAPA_TICKER.values()) if t not in cfg.IS_BDR
    )
    return acoes


def baixar_um(ticker: str, fim: str) -> pd.DataFrame:
    """Baixa um ticker e devolve DataFrame de colunas planas (Close ajustado)."""
    yahoo = INDICE_MERCADO if ticker == INDICE_MERCADO else f"{ticker}.SA"
    df = yf.download(yahoo, start=DATA_INICIO, end=fim,
                     progress=False, auto_adjust=True)
    if df.empty:
        return df
    # yfinance devolve colunas MultiIndex (campo, ticker); achata
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    return df


def diagnostico(ticker: str, df: pd.DataFrame) -> str:
    if df.empty:
        return f"  {ticker:8s} → VAZIO (Yahoo não devolveu nada)"
    close = df["Close"]
    n = len(df)
    zeros = int((close == 0).sum())
    nans = int(close.isna().sum())
    ini, fim = df.index.min().date(), df.index.max().date()
    alerta = ""
    if zeros or nans:
        alerta = f"  ⚠ {zeros} zeros, {nans} NaN"
    return f"  {ticker:8s} → {n:4d} pregões  [{ini} … {fim}]{alerta}"


def main() -> None:
    fim = (dt.date.today() + dt.timedelta(days=1)).isoformat()
    raw_dir = cfg.DATA_RAW / "precos"
    raw_dir.mkdir(parents=True, exist_ok=True)
    cfg.DATA_PROC.mkdir(parents=True, exist_ok=True)

    print("=" * 64)
    print(f"BAIXANDO PREÇOS  ({DATA_INICIO} → {fim})")
    print("=" * 64)

    alvos = tickers_para_baixar() + [INDICE_MERCADO]
    series_close: dict[str, pd.Series] = {}

    for ticker in alvos:
        df = baixar_um(ticker, fim)
        if not df.empty:
            df.to_csv(raw_dir / f"{ticker}.csv", encoding="utf-8")
            series_close[ticker] = df["Close"].rename(ticker)
        print(diagnostico(ticker, df))

    # tabela combinada (formato largo): índice = data, colunas = tickers
    combinado = pd.concat(series_close.values(), axis=1).sort_index()
    out = cfg.DATA_PROC / "precos_ajustados.csv"
    combinado.to_csv(out, encoding="utf-8-sig")

    print()
    print(f"Salvo cru: {raw_dir.relative_to(cfg.ROOT)}/ ({len(series_close)} arquivos)")
    print(f"Salvo combinado: {out.relative_to(cfg.ROOT)} "
          f"({combinado.shape[0]} pregões × {combinado.shape[1]} tickers)")

    # checagem de cobertura: todo banco do ablation tem preço?
    faltam = [t for t in cfg.BANCOS_F1_SOLIDA if t not in series_close]
    if faltam:
        print(f"\n⚠ ATENÇÃO: sem preço para bancos do ablation: {faltam}")
    else:
        print("\n✓ Todos os 8 bancos do ablation têm série de preço.")


if __name__ == "__main__":
    main()
