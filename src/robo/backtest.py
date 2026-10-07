"""
Robô Fundamento — motor de backtest e métricas.

Implementado por nós (exigência do edital: nada de plataforma que entrega o
backtest pronto). Simula mês a mês, respeitando as três regras de ouro:

  1. Sem olhar o futuro  — os pesos do mês t vêm de informação até t-1.
  2. Com custo           — cada rebalanceamento paga o giro.
  3. Com deriva          — entre rebalanceamentos os pesos andam sozinhos,
                           como numa carteira de verdade.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as cfg


def rodar_backtest(painel: pd.DataFrame, pesos_alvo: pd.DataFrame,
                   freq: int | None = None,
                   custo: float | None = None) -> pd.DataFrame:
    """Simula a carteira. Devolve retorno, custo e pesos efetivos de cada mês.

    `pesos_alvo` é o que a estratégia QUER ter. `pesos_efetivos` é o que ela
    realmente tem — os dois só coincidem no mês do rebalanceamento; depois a
    carteira deriva com o retorno de cada classe.
    """
    freq = cfg.FREQ_REBALANCE if freq is None else freq
    custo = cfg.CUSTO_GIRO if custo is None else custo
    rets = painel[[f"ret_{c}" for c in cfg.CLASSES]]
    rets.columns = cfg.CLASSES

    efetivos = pesos_alvo.iloc[0].copy()
    linhas = []
    for i, dt in enumerate(painel.index):
        alvo = pesos_alvo.loc[dt]

        # rebalanceamento periódico: volta para o alvo e paga o giro
        if i % freq == 0:
            giro = float((alvo - efetivos).abs().sum())
            efetivos = alvo.copy()
        else:
            giro = 0.0
        custo_mes = giro * custo

        r_classes = rets.loc[dt]
        r_bruto = float((efetivos * r_classes).sum())
        linhas.append({"retorno": r_bruto - custo_mes, "bruto": r_bruto,
                       "custo": custo_mes, "giro": giro,
                       **{f"w_{c}": efetivos[c] for c in cfg.CLASSES}})

        # deriva: quem subiu passa a pesar mais até o próximo rebalanceamento
        efetivos = efetivos * (1 + r_classes)
        soma = efetivos.sum()
        if soma > 0:
            efetivos = efetivos / soma

    return pd.DataFrame(linhas, index=painel.index)


# ── Métricas ────────────────────────────────────────────────────────────────
def max_drawdown(r: pd.Series) -> float:
    eq = (1 + r.dropna()).cumprod()
    return float((eq / eq.cummax() - 1).min())


def avaliar(r: pd.Series, cdi: pd.Series) -> dict:
    """Métricas com a régua correta: excedente ao CDI.

    No Brasil, ignorar o CDI infla qualquer Sharpe — dinheiro parado rende ~10%
    ao ano sem risco. O que importa é quanto a estratégia rende ALÉM disso.
    """
    d = pd.concat([r.rename("r"), cdi.rename("cdi")], axis=1).dropna()
    exc = d["r"] - d["cdi"]
    n = len(d)
    cagr = float((1 + d["r"]).prod() ** (12 / n) - 1)
    vol = float(d["r"].std() * np.sqrt(12))
    sharpe = float(exc.mean() / exc.std() * np.sqrt(12)) if exc.std() > 0 else np.nan
    t, p = stats.ttest_1samp(exc, 0.0) if n > 2 else (np.nan, np.nan)
    return {
        "meses": n,
        "retorno_aa": cagr,
        "vol_aa": vol,
        "excedente_cdi_aa": float((1 + exc).prod() ** (12 / n) - 1),
        "sharpe": sharpe,
        "max_dd": max_drawdown(d["r"]),
        "t": float(t),
        "p": float(p),
        "meses_acima_cdi": float((exc > 0).mean()),
    }
