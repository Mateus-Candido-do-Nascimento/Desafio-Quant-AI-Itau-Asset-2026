"""
Robô Fundamento — testes de reforço (ataca as fragilidades do backtest).

Uso:  python src/robo/reforco.py

Os testes de `rodar.py` cobrem o básico. Aqui vão os que um avaliador crítico
faria — e que poderiam derrubar o resultado:

  1. A janela de momentum foi escolhida a dedo? (data snooping)
  2. A significância aguenta um teste que não assume normalidade? (bootstrap)
  3. Funciona em regimes diferentes, ou só num período de sorte?
  4. O resultado depende de uma classe específica ter ido bem?
  5. Não seria melhor simplesmente comprar e segurar a melhor classe?
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import backtest as bt
import config as cfg
import dados
import estrategia as est

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

N_BOOTSTRAP = 10_000
SEMENTE = 42


def pesos_ranking_flex(painel: pd.DataFrame, janela: int,
                       classes: list[str] | None = None) -> pd.DataFrame:
    """Mesma regra de `estrategia.pesos_ranking`, com janela e cardápio abertos.

    Existe para os testes de sensibilidade — a versão de produção fica em
    `estrategia.py` com os parâmetros fixos do `config.py`.
    """
    classes = classes or cfg.CLASSES
    risco = [c for c in classes if c != cfg.CAIXA]
    mom = pd.DataFrame(
        {c: (painel[f"nivel_{c}"] / painel[f"nivel_{c}"].shift(janela) - 1).shift(1)
         for c in classes}
    )
    linhas = []
    for dt in painel.index:
        m = mom.loc[dt]
        p = {c: 0.0 for c in classes}
        if m.isna().any():
            p[cfg.CAIXA] = 1.0
        else:
            aprov = sorted([c for c in risco if m[c] > m[cfg.CAIXA]], key=lambda c: -m[c])
            for peso, c in zip(cfg.PESOS_RANKING, aprov):
                p[c] = peso
            if "Cripto" in p:                      # mesmo teto da versão de produção
                p["Cripto"] = min(p["Cripto"], cfg.TETO_CRIPTO)
            p[cfg.CAIXA] = 1.0 - sum(p[c] for c in risco)
        linhas.append(p)
    return pd.DataFrame(linhas, index=painel.index)[classes]


def main() -> None:
    completo = dados.carregar_painel()
    hoje = pd.Timestamp.today()
    if completo.index[-1].month == hoje.month and completo.index[-1].year == hoje.year:
        completo = completo.iloc[:-1]
    rec = completo.index[completo.index >= cfg.DATA_INICIO_INVESTIVEL]
    cdi = completo["ret_CDI"].loc[rec]

    def backtest_em(pesos):
        return bt.rodar_backtest(completo, pesos)["retorno"].loc[rec]

    # ── 1. Janela de momentum ───────────────────────────────────────────────
    print("=" * 66)
    print("1. A JANELA DE MOMENTUM FOI ESCOLHIDA A DEDO?")
    print("=" * 66)
    for j in (6, 9, 12, 18, 24):
        m = bt.avaliar(backtest_em(pesos_ranking_flex(completo, j)), cdi)
        marca = "  <- a que usamos" if j == 12 else ""
        print(f"  {j:2d} meses: exCDI={m['excedente_cdi_aa']:>+6.1%}  "
              f"Sharpe={m['sharpe']:>5.2f}  MaxDD={m['max_dd']:>5.0%}{marca}")
    print("  -> se todas forem positivas, não garimpamos o parâmetro")

    # ── 2. Bootstrap ────────────────────────────────────────────────────────
    print("\n" + "=" * 66)
    print("2. SIGNIFICÂNCIA SEM ASSUMIR NORMALIDADE (bootstrap)")
    print("=" * 66)
    r_base = backtest_em(est.pesos_ranking(completo))
    exc = (r_base - cdi).dropna().values
    rng = np.random.default_rng(SEMENTE)
    medias = np.array([rng.choice(exc, size=len(exc), replace=True).mean()
                       for _ in range(N_BOOTSTRAP)])
    p_boot = float((medias <= 0).mean())
    ic = np.percentile(medias, [2.5, 97.5]) * 12
    print(f"  Excedente médio ao CDI: {exc.mean() * 12:+.2%} a.a.")
    print(f"  IC 95%: [{ic[0]:+.2%}, {ic[1]:+.2%}] a.a.")
    print(f"  P(excedente <= 0) = {p_boot:.4f} (unicaudal)")
    print("  -> compare com o teste t bicaudal de rodar.py: os dois devem concordar")

    # ── 3. Subperíodos ──────────────────────────────────────────────────────
    print("\n" + "=" * 66)
    print("3. FUNCIONA EM REGIMES DIFERENTES?")
    print("=" * 66)
    ibov = completo["ret_Acoes"].loc[rec]
    for nome, ini, fim in [("2015-2017 recessão/recuperação", "2015-01-01", "2017-12-31"),
                           ("2018-2019 juro caindo", "2018-01-01", "2019-12-31"),
                           ("2020-2021 pandemia", "2020-01-01", "2021-12-31"),
                           ("2022-2023 juro alto", "2022-01-01", "2023-12-31"),
                           ("2024-2026 recente", "2024-01-01", "2026-12-31")]:
        jan = (r_base.index >= ini) & (r_base.index <= fim)
        if jan.sum() < 6:
            continue
        m = bt.avaliar(r_base[jan], cdi[jan])
        mi = bt.avaliar(ibov[jan], cdi[jan])
        print(f"  {nome:32s} robô={m['excedente_cdi_aa']:>+6.1%}  "
              f"ibov={mi['excedente_cdi_aa']:>+6.1%}  (vs CDI)")

    # ── 4. Dependência de uma classe ────────────────────────────────────────
    print("\n" + "=" * 66)
    print("4. O RESULTADO DEPENDE DE UMA CLASSE ESPECÍFICA?")
    print("=" * 66)
    original = cfg.CLASSES
    try:
        for fora in cfg.CLASSES_RISCO:
            subset = [c for c in original if c != fora]
            cfg.CLASSES = subset  # o motor reporta pesos por classe
            m = bt.avaliar(backtest_em(pesos_ranking_flex(completo, 12, subset)), cdi)
            print(f"  sem {fora:7s}: exCDI={m['excedente_cdi_aa']:>+6.1%}  "
                  f"Sharpe={m['sharpe']:>5.2f}  MaxDD={m['max_dd']:>5.0%}")
    finally:
        cfg.CLASSES = original

    # ── 5. Comprar e segurar a melhor ───────────────────────────────────────
    print("\n" + "=" * 66)
    print("5. NÃO SERIA MELHOR COMPRAR E SEGURAR A MELHOR CLASSE?")
    print("=" * 66)
    refs = {"Robô Fundamento": r_base}
    for c in cfg.CLASSES_RISCO:
        refs[f"Buy&hold {c}"] = completo[f"ret_{c}"].loc[rec]
    for nome, r in refs.items():
        m = bt.avaliar(r, cdi)
        print(f"  {nome:22s} ret={m['retorno_aa']:>6.1%}  "
              f"exCDI={m['excedente_cdi_aa']:>+6.1%}  Sharpe={m['sharpe']:>5.2f}  "
              f"MaxDD={m['max_dd']:>5.0%}")
    print("  -> comprar e segurar a campeã só é resposta OLHANDO PARA TRÁS;")
    print("     o robô não precisa adivinhar qual será a campeã.")


if __name__ == "__main__":
    main()
