"""
Robô Fundamento — camada de dados.

Monta o painel mensal com as 4 classes de ativo + o insumo macro (IPCA), a
partir de fontes públicas e gratuitas:
  - Banco Central (API SGS): CDI e IPCA
  - Yahoo Finance: Ibovespa, ouro (USD) e dólar

Saída: DataFrame mensal com NÍVEIS (para o filtro de tendência) e RETORNOS
(para o backtest), mais o IPCA acumulado 12 meses.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as cfg


def _sgs(codigo: int, inicio: str = "01/01/2009", fim: str = "31/12/2026") -> pd.Series:
    """Baixa uma série do Banco Central (API SGS).

    A API limita ~10 anos por requisição, então buscamos em blocos. Precisa de
    User-Agent de navegador — sem ele o BCB devolve erro.
    """
    partes: list[dict] = []
    blocos = [("01/01/2009", "31/12/2016"), ("01/01/2017", fim)]
    for ini_b, fim_b in blocos:
        url = (f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"
               f"?formato=json&dataInicial={ini_b}&dataFinal={fim_b}")
        # O SGS falha de duas formas diferentes, e as duas são transitórias:
        #   1. rajada de requisições -> HTTP 200 com pagina HTML de erro
        #      (por isso a checagem é pelo CONTEÚDO, não só pelo status);
        #   2. instabilidade do servidor -> 502/503/504.
        # Ambas são tratadas com a mesma espera exponencial.
        for tentativa in range(5):
            try:
                resp = requests.get(url, timeout=60,
                                    headers={"User-Agent": "Mozilla/5.0"})
                resp.raise_for_status()
                if resp.text.lstrip().startswith("["):
                    break
            except requests.exceptions.RequestException:
                pass
            time.sleep(2 ** tentativa)
        else:
            raise RuntimeError(
                f"SGS {codigo} recusou o bloco {ini_b}-{fim_b} apos 5 tentativas"
            )
        partes += resp.json()
    df = pd.DataFrame(partes)
    df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
    df["valor"] = df["valor"].astype(float) / 100.0  # % -> fração
    return df.set_index("data")["valor"].sort_index()


def carregar_painel() -> pd.DataFrame:
    """Painel mensal: níveis das classes, retornos e IPCA 12m.

    Índice = fim de cada mês. Colunas:
      nivel_{classe}  -> série de preço/índice (para o filtro de tendência)
      ret_{classe}    -> retorno do mês
      ipca_12m        -> inflação acumulada em 12 meses
    """
    # ── Banco Central ───────────────────────────────────────────────────────
    cdi_diario = _sgs(cfg.SGS_CDI)
    cdi_mensal = (1 + cdi_diario).resample("ME").prod() - 1  # compõe o dia no mês
    ipca_mensal = _sgs(cfg.SGS_IPCA)
    ipca_mensal = ipca_mensal.resample("ME").last()
    ipca_12m = (1 + ipca_mensal).rolling(12).apply(lambda x: x.prod(), raw=True) - 1

    # ── Mercado ─────────────────────────────────────────────────────────────
    tickers = [cfg.TICKER_ACOES, cfg.TICKER_GLOBAL_USD, cfg.TICKER_OURO_USD,
               cfg.TICKER_DOLAR]
    if cfg.INCLUIR_CRIPTO:
        tickers.append(cfg.TICKER_CRIPTO_USD)
    px = yf.download(tickers, start=cfg.DATA_INICIO, auto_adjust=True,
                     progress=False)["Close"]
    pm = px.resample("ME").last()

    dolar = pm[cfg.TICKER_DOLAR]
    niveis = pd.DataFrame(index=pm.index)
    niveis["Acoes"] = pm[cfg.TICKER_ACOES]
    niveis["Global"] = pm[cfg.TICKER_GLOBAL_USD] * dolar  # S&P total return em BRL
    niveis["Ouro"] = pm[cfg.TICKER_OURO_USD] * dolar      # ouro em BRL
    niveis["Dolar"] = dolar
    if cfg.INCLUIR_CRIPTO:
        niveis["Cripto"] = pm[cfg.TICKER_CRIPTO_USD] * dolar  # BTC em BRL
    # o CDI vira um "índice" acumulando o rendimento (nunca cai)
    niveis["CDI"] = (1 + cdi_mensal.reindex(pm.index).fillna(0)).cumprod()

    rets = pd.DataFrame(index=pm.index)
    for c in cfg.CLASSES_RISCO:
        rets[c] = niveis[c].pct_change()
    rets["CDI"] = cdi_mensal.reindex(pm.index)

    painel = pd.concat(
        [niveis.add_prefix("nivel_"), rets.add_prefix("ret_"),
         ipca_12m.rename("ipca_12m").reindex(pm.index)],
        axis=1,
    )
    return painel.dropna(subset=[f"ret_{c}" for c in cfg.CLASSES])


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = carregar_painel()
    print(f"Painel: {len(p)} meses, de {p.index.min().date()} a {p.index.max().date()}")
    print(p.tail(3).round(4).to_string())
