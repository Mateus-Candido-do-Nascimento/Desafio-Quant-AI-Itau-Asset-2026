"""
Event study — motor básico (PoC sobre ITUB4).

Pergunta da PoC: a divulgação do ranking do BC move o preço do Itaú?

Pipeline (ver docs/metodologia_event_study.md):
  retorno -> modelo de mercado -> retorno anormal (AR) -> CAR -> CAAR -> teste t

Entrada:
  data/processed/precos_ajustados.csv   (fechamento ajustado)
  config.DATAS_DIVULGACAO               (datas de evento, do calendário oficial)

Saída:
  data/processed/es_{ticker}_ar.csv     (AR por evento × dia relativo)
  data/processed/es_{ticker}_car.csv    (CAR por evento, várias janelas)
  data/processed/es_{ticker}_caar.csv   (AR médio por dia relativo + teste)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as cfg

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ── Janelas (em pregões), relativas ao dia 0 = dia da divulgação ────────────
EST_INI, EST_FIM = -130, -11   # janela de estimação: 120 pregões
EVT_INI, EVT_FIM = -5, +5      # janela do evento: 11 pregões
# janelas de CAR a reportar (datas exatas → podemos usar janelas estreitas)
JANELAS_CAR = {"CAR(0,0)": (0, 0), "CAR(0,1)": (0, 1),
               "CAR(-1,1)": (-1, 1), "CAR(-5,5)": (-5, 5)}
MERCADO = "^BVSP"


def carregar_retornos(ticker: str) -> pd.DataFrame:
    """Retornos simples diários do ticker e do mercado, alinhados (inner join)."""
    precos = pd.read_csv(
        cfg.DATA_PROC / "precos_ajustados.csv",  # vírgula (saída do yfinance)
        parse_dates=["Date"], index_col="Date",
    )
    ret = precos[[ticker, MERCADO]].pct_change()
    return ret.dropna().rename(columns={ticker: "r_acao", MERCADO: "r_mkt"})


def estimar_modelo_mercado(est: pd.DataFrame) -> tuple[float, float]:
    """OLS R_acao ~ alpha + beta*R_mkt na janela de estimação. Retorna (a, b)."""
    beta, alpha = np.polyfit(est["r_mkt"].values, est["r_acao"].values, 1)
    return alpha, beta


def event_study(ticker: str) -> dict:
    ret = carregar_retornos(ticker)
    dias = ret.index  # DatetimeIndex de pregões, ordenado

    ar_por_evento = {}     # (ano,q) -> Series AR indexada por dia relativo
    linhas_car = []

    for (ano, q), data in sorted(cfg.DATAS_DIVULGACAO.items()):
        ev = pd.Timestamp(data)
        # dia 0 = 1º pregão >= data de divulgação (snap p/ feriado/fim de semana)
        t0 = dias.searchsorted(ev)
        if t0 + EST_INI < 0 or t0 + EVT_FIM >= len(dias):
            continue  # histórico insuficiente nas pontas

        est = ret.iloc[t0 + EST_INI : t0 + EST_FIM + 1]   # 120 pregões
        alpha, beta = estimar_modelo_mercado(est)

        evt = ret.iloc[t0 + EVT_INI : t0 + EVT_FIM + 1].copy()
        evt["esperado"] = alpha + beta * evt["r_mkt"]
        evt["AR"] = evt["r_acao"] - evt["esperado"]
        evt.index = range(EVT_INI, EVT_FIM + 1)  # dia relativo
        ar_por_evento[(ano, q)] = evt["AR"]

        linha = {"ano": ano, "trimestre": q,
                 "dia0": dias[t0].date(), "alpha": alpha, "beta": beta}
        for nome, (a, b) in JANELAS_CAR.items():
            linha[nome] = evt.loc[a:b, "AR"].sum()
        linhas_car.append(linha)

    car = pd.DataFrame(linhas_car)
    ar_mat = pd.DataFrame(ar_por_evento)  # linhas = dia relativo, colunas = evento
    caar = ar_mat.mean(axis=1)            # AR médio por dia relativo

    return {"ticker": ticker, "car": car, "ar_mat": ar_mat, "caar": caar}


def testar(valores: pd.Series) -> dict:
    """Testa H0: efeito = 0, paramétrico (t) e não-paramétrico (sinais).

    Com n pequeno (~15 eventos) o t-test é frágil; o sign test (quantos eventos
    têm CAR negativo vs esperado 50%) não assume normalidade e serve de checagem.
    """
    x = valores.dropna().values
    n = len(x)
    if n < 2:
        return {"n": n, "media": float("nan"), "t": float("nan"),
                "p_t": float("nan"), "neg": 0, "p_sinal": float("nan")}
    t, p_t = stats.ttest_1samp(x, 0.0)            # t bicaudal, df = n-1
    neg = int((x < 0).sum())                       # nº de eventos com efeito < 0
    # sign test bicaudal: P(X=neg) sob Binomial(n, 0.5)
    p_sinal = stats.binomtest(neg, n, 0.5).pvalue
    return {"n": n, "media": float(np.mean(x)), "t": float(t),
            "p_t": float(p_t), "neg": neg, "p_sinal": p_sinal}


def main() -> None:
    ticker = sys.argv[1] if len(sys.argv) > 1 else "ITUB4"
    print("=" * 64)
    print(f"EVENT STUDY — {ticker}  (PoC)")
    print("=" * 64)

    res = event_study(ticker)
    car, caar = res["car"], res["caar"]
    print(f"Eventos processados: {len(car)}")
    print(f"Beta médio: {car['beta'].mean():.2f}  |  alpha médio: {car['alpha'].mean():.5f}")
    print()

    print("CAR médio por janela (H0: CAR = 0):")
    print(f"  {'janela':10s} {'CAR médio':>11s} {'t':>7s} {'p(t)':>7s}"
          f" {'neg/n':>7s} {'p(sinal)':>9s}")
    for nome in JANELAS_CAR:
        r = testar(car[nome])
        sig = "***" if r["p_t"] < 0.01 else ("**" if r["p_t"] < 0.05
                                             else ("*" if r["p_t"] < 0.10 else ""))
        print(f"  {nome:10s} {r['media']:>+11.4%} {r['t']:>7.2f} {r['p_t']:>7.3f}"
              f" {r['neg']:>4d}/{r['n']:<2d} {r['p_sinal']:>9.3f}  {sig}")
    print("  (*** p<0.01  ** p<0.05  * p<0.10; p(sinal)=sign test não-paramétrico)")

    print()
    print("CAAR — AR médio por dia relativo (acumulado):")
    acum = 0.0
    for d in caar.index:
        acum += caar[d]
        marca = "  <- dia 0" if d == 0 else ""
        print(f"  d={d:+d}: AR_médio={caar[d]:>+8.4%}  CAAR={acum:>+8.4%}{marca}")

    # ── salva saídas auditáveis ─────────────────────────────────────────────
    res["ar_mat"].to_csv(cfg.DATA_PROC / f"es_{ticker}_ar.csv",
                         sep=";", encoding="utf-8-sig")
    car.to_csv(cfg.DATA_PROC / f"es_{ticker}_car.csv",
               sep=";", index=False, encoding="utf-8-sig")
    caar.rename("AR_medio").to_csv(cfg.DATA_PROC / f"es_{ticker}_caar.csv",
                                   sep=";", encoding="utf-8-sig")
    print()
    print(f"Salvo: data/processed/es_{ticker}_{{ar,car,caar}}.csv")


if __name__ == "__main__":
    main()
