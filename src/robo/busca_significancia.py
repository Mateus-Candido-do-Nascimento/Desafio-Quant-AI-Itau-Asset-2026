"""
Robô Fundamento — busca por significância (e por que rejeitamos o que "funcionou").

Uso:  python src/robo/busca_significancia.py

O excedente do robô sobre o CDI é marginal (p ~ 0,08). Este script registra a
tentativa DISCIPLINADA de cruzar 5%:

  · variantes definidas A PRIORI (2 recortes × 4 desenhos = 8 testes)
  · TODAS reportadas, com correção de Bonferroni
  · as que cruzarem 5% passam por dois testes de sanidade:
        (1) melhora em quantos subperíodos?
        (2) o ganho vem de habilidade ou de alavancagem?

Conclusão registrada em docs/busca_significancia.md: as duas variantes que
cruzaram 5% (vol-targeting e risk parity) foram REJEITADAS.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import backtest as bt
import config as cfg
import dados

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

JANELAS_ENSEMBLE = (6, 9, 12, 18)
VOL_ALVO = 0.10
TETO_ESCALA = 1.5
SUBPERIODOS = [("2011-2014", "2011-02-01", "2014-12-31"),
               ("2015-2017", "2015-01-01", "2017-12-31"),
               ("2018-2019", "2018-01-01", "2019-12-31"),
               ("2020-2021", "2020-01-01", "2021-12-31"),
               ("2022-2023", "2022-01-01", "2023-12-31"),
               ("2024-2026", "2024-01-01", "2026-12-31")]


def _momentum(painel, janela, classes):
    return pd.DataFrame(
        {c: (painel[f"nivel_{c}"] / painel[f"nivel_{c}"].shift(janela) - 1).shift(1)
         for c in classes})


def pesos(painel, janelas, risk_parity=False):
    """Ranking; com uma janela ou média de várias; pesos fixos ou por 1/vol."""
    classes, risco = cfg.CLASSES, cfg.CLASSES_RISCO
    rets = painel[[f"ret_{c}" for c in classes]]
    rets.columns = classes
    vol12 = rets.rolling(12).std().shift(1) * np.sqrt(12)  # ex-ante

    acumulado = None
    for j in janelas:
        mom = _momentum(painel, j, classes)
        linhas = []
        for dt in painel.index:
            m = mom.loc[dt]
            p = {c: 0.0 for c in classes}
            if m.isna().any() or (risk_parity and vol12.loc[dt].isna().any()):
                p[cfg.CAIXA] = 1.0
            else:
                aprov = sorted([c for c in risco if m[c] > m[cfg.CAIXA]], key=lambda c: -m[c])
                if risk_parity and aprov:
                    inv = {c: 1 / max(vol12.loc[dt, c], 0.02) for c in aprov}
                    s = sum(inv.values())
                    for c in aprov:
                        p[c] = 0.60 * inv[c] / s
                else:
                    for peso, c in zip(cfg.PESOS_RANKING, aprov):
                        p[c] = peso
                p[cfg.CAIXA] = 1.0 - sum(p[c] for c in risco)
            linhas.append(p)
        w = pd.DataFrame(linhas, index=painel.index)[classes]
        acumulado = w if acumulado is None else acumulado + w
    return acumulado / len(janelas)


def vol_target(painel, w, alvo=VOL_ALVO):
    """Escala a perna de risco para vol-alvo. ATENÇÃO: pode virar alavancagem."""
    rets = painel[[f"ret_{c}" for c in cfg.CLASSES]]
    rets.columns = cfg.CLASSES
    vol = (w * rets).sum(axis=1).rolling(12).std().shift(1) * np.sqrt(12)
    escala = (alvo / vol).clip(upper=TETO_ESCALA).fillna(1.0)
    risco = cfg.CLASSES_RISCO
    novo = w.copy()
    novo[risco] = w[risco].mul(escala, axis=0)
    novo[cfg.CAIXA] = 1.0 - novo[risco].sum(axis=1)
    return novo, escala


def _stats(r, cdi):
    d = pd.concat([r.rename("r"), cdi.rename("cdi")], axis=1).dropna()
    exc = d["r"] - d["cdi"]
    t, p = stats.ttest_1samp(exc, 0.0)
    m = bt.avaliar(r, cdi)
    return m, float(t), float(p), len(d) / 12


def main() -> None:
    completo = dados.carregar_painel()
    hoje = pd.Timestamp.today()
    if completo.index[-1].month == hoje.month and completo.index[-1].year == hoje.year:
        completo = completo.iloc[:-1]

    recortes = {"2015+ (IVVB11 investível)": "2015-01-01",
                "2010+ (série completa)": "2011-02-01"}
    desenhos = {
        "base (12m)": lambda p: pesos(p, [12]),
        "ensemble 6/9/12/18m": lambda p: pesos(p, JANELAS_ENSEMBLE),
        "base + vol-target": lambda p: vol_target(p, pesos(p, [12]))[0],
        "ensemble + vol-target": lambda p: vol_target(p, pesos(p, JANELAS_ENSEMBLE))[0],
    }
    n = len(recortes) * len(desenhos)

    print("=" * 100)
    print(f"BUSCA DE SIGNIFICÂNCIA — {n} variantes definidas A PRIORI, todas reportadas")
    print("=" * 100)
    for nome_rec, ini in recortes.items():
        print(f"\n--- {nome_rec} ---")
        rec = completo.index[completo.index >= ini]
        cdi = completo["ret_CDI"].loc[rec]
        for nome_des, gerar in desenhos.items():
            r = bt.rodar_backtest(completo, gerar(completo))["retorno"].loc[rec]
            m, t, p, anos = _stats(r, cdi)
            flag = "<- cruza 5%" if p < 0.05 else ""
            print(f"  {nome_des:24s} anos={anos:>4.1f} exCDI={m['excedente_cdi_aa']:>+6.1%} "
                  f"Sharpe={m['sharpe']:>5.2f} DD={m['max_dd']:>5.0%} "
                  f"p={p:.4f} pBonf={min(1, p * n):.3f} {flag}")

    # ── Teste de sanidade das variantes que cruzaram 5% ─────────────────────
    print("\n" + "=" * 100)
    print("TESTE DE SANIDADE 1 — a melhora é consistente entre subperíodos?")
    print("=" * 100)
    cdi_full = completo["ret_CDI"]
    base = bt.rodar_backtest(completo, pesos(completo, [12]))["retorno"]
    candidatos = {
        "vol-target": bt.rodar_backtest(completo, vol_target(completo, pesos(completo, [12]))[0])["retorno"],
        "risk parity": bt.rodar_backtest(completo, pesos(completo, [12], risk_parity=True))["retorno"],
    }
    for nome, serie in candidatos.items():
        melhorou = 0
        detalhes = []
        for rot, i, f in SUBPERIODOS:
            jan = (base.index >= i) & (base.index <= f)
            if jan.sum() < 6:
                continue
            a, b = bt.avaliar(base[jan], cdi_full[jan]), bt.avaliar(serie[jan], cdi_full[jan])
            ok = b["sharpe"] > a["sharpe"]
            melhorou += ok
            detalhes.append(f"{rot}:{'+' if ok else '-'}")
        print(f"  {nome:14s} melhorou em {melhorou}/{len(detalhes)} subperíodos   "
              + " ".join(detalhes))

    print("\n" + "=" * 100)
    print("TESTE DE SANIDADE 2 — o ganho vem de habilidade ou de alavancagem?")
    print("=" * 100)
    w0 = pesos(completo, [12])
    wv, escala = vol_target(completo, w0)
    exp0 = w0[cfg.CLASSES_RISCO].sum(axis=1).mean()
    expv = wv[cfg.CLASSES_RISCO].sum(axis=1).mean()
    print(f"  vol-target: escala média {escala.mean():.2f}x  "
          f"(meses no teto {TETO_ESCALA}x: {(escala >= TETO_ESCALA).sum()})")
    print(f"              exposição a risco {exp0:.0%} -> {expv:.0%}  "
          f"{'ALAVANCAGEM DISFARÇADA' if expv > exp0 else 'reduz risco (ok)'}")
    wrp = pesos(completo, [12], risk_parity=True)
    exprp = wrp[cfg.CLASSES_RISCO].sum(axis=1).mean()
    print(f"  risk parity: exposição a risco {exp0:.0%} -> {exprp:.0%}  "
          f"{'ALAVANCAGEM DISFARÇADA' if exprp > exp0 else 'reduz risco (ok)'}")

    # ── Poder estatístico ───────────────────────────────────────────────────
    print("\n" + "=" * 100)
    print("QUANTOS ANOS SERIAM NECESSÁRIOS? (anos = (1,96/Sharpe)^2)")
    print("=" * 100)
    rec = completo.index[completo.index >= "2015-01-01"]
    m, t, p, anos = _stats(base.loc[rec], completo["ret_CDI"].loc[rec])
    nec = (1.96 / m["sharpe"]) ** 2
    print(f"  Sharpe atual {m['sharpe']:.2f} -> precisa de {nec:.1f} anos; temos {anos:.1f}")
    print(f"  Faltam {nec - anos:.1f} anos de dados — o limite é a AMOSTRA, não a estratégia.")


if __name__ == "__main__":
    main()
