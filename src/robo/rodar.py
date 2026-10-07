"""
Robô Fundamento — executa o backtest completo e salva os resultados.

Uso:  python src/robo/rodar.py

Compara o robô (tático) contra o rebalanceamento puro, a carteira balanceada
clássica, o CDI e o Ibovespa. Roda ainda os testes de robustez e a validação
fora da amostra.

Saídas em data/processed/:
  robo_retornos.csv   — retorno mês a mês de cada estratégia
  robo_pesos.csv      — a alocação do robô em cada mês (o rebalanceamento)
  robo_metricas.csv   — a tabela de resultados
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import backtest as bt
import config as cfg
import dados
import estrategia as est

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SPLIT_OOS = "2019-12-31"  # treino até aqui; o resto é fora da amostra


def _linha(nome: str, m: dict) -> str:
    return (f"{nome:26s}{m['retorno_aa']:>8.1%}{m['vol_aa']:>7.1%}"
            f"{m['excedente_cdi_aa']:>9.1%}{m['sharpe']:>8.2f}"
            f"{m['max_dd']:>8.0%}{m['t']:>7.2f}")


def _cabecalho() -> str:
    return (f"{'estratégia':26s}{'retorno':>8s}{'vol':>7s}{'exCDI':>9s}"
            f"{'Sharpe':>8s}{'MaxDD':>8s}{'t':>7s}")


def main() -> None:
    print("=" * 72)
    print("ROBÔ FUNDAMENTO — backtest de alocação com rebalanceamento periódico")
    print("=" * 72)
    completo = dados.carregar_painel()
    # descarta o mês corrente incompleto (dados parciais distorcem o retorno)
    hoje = pd.Timestamp.today()
    if completo.index[-1].month == hoje.month and completo.index[-1].year == hoje.year:
        completo = completo.iloc[:-1]

    # Os SINAIS usam todo o histórico (precisam de 12 meses de aquecimento);
    # o BACKTEST só começa quando a bolsa global virou investível na B3.
    pesos = {
        "ranking": est.pesos_ranking(completo),
        "tatico": est.pesos_tatico(completo),
        "estatico": est.pesos_estatico(completo),
        "balanceado": est.pesos_benchmark_balanceado(completo),
    }
    painel = completo[completo.index >= cfg.DATA_INICIO_INVESTIVEL]
    pesos = {k: v.loc[painel.index] for k, v in pesos.items()}
    cdi = painel["ret_CDI"]
    print(f"Período: {painel.index.min().date()} a {painel.index.max().date()} "
          f"({len(painel)} meses)\n")

    # ── as carteiras ────────────────────────────────────────────────────────
    bt_ranking = bt.rodar_backtest(painel, pesos["ranking"])
    bt_tatico = bt.rodar_backtest(painel, pesos["tatico"])
    bt_estatico = bt.rodar_backtest(painel, pesos["estatico"])
    bt_balanceado = bt.rodar_backtest(painel, pesos["balanceado"])

    carteiras = {
        "Robô Fundamento (ranking)": bt_ranking["retorno"],
        "Tático (só tendência)": bt_tatico["retorno"],
        "Rebal. puro (peso igual)": bt_estatico["retorno"],
        "Balanceada 60/40": bt_balanceado["retorno"],
        "Ibovespa (100% ações)": painel["ret_Acoes"],
        "CDI (régua)": cdi,
    }

    print(_cabecalho())
    print("-" * 72)
    metricas = {}
    for nome, r in carteiras.items():
        m = bt.avaliar(r, cdi)
        metricas[nome] = m
        print(_linha(nome, m))

    # ── fora da amostra ─────────────────────────────────────────────────────
    print(f"\n{'=' * 72}\nVALIDAÇÃO FORA DA AMOSTRA (a partir de 2020)\n{'=' * 72}")
    oos = painel.index > SPLIT_OOS
    print(_cabecalho())
    print("-" * 72)
    for nome, r in carteiras.items():
        print(_linha(nome, bt.avaliar(r[oos], cdi[oos])))

    # ── robustez ────────────────────────────────────────────────────────────
    print(f"\n{'=' * 72}\nROBUSTEZ (o resultado aguenta mudar os parâmetros?)\n{'=' * 72}")
    print("Frequência de rebalanceamento (robô ranking):")
    pesos_full = est.pesos_ranking(completo)
    for freq, rotulo in [(1, "mensal"), (3, "trimestral"), (6, "semestral")]:
        # roda sobre todo o histórico e só depois recorta, para que a fase do
        # rebalanceamento não dependa de onde o backtest começa
        r = bt.rodar_backtest(completo, pesos_full, freq=freq)["retorno"].loc[painel.index]
        m = bt.avaliar(r, cdi)
        print(f"  {rotulo:12s} exCDI={m['excedente_cdi_aa']:>6.1%}"
              f"  Sharpe={m['sharpe']:>5.2f}  MaxDD={m['max_dd']:>5.0%}")

    print("Concentração do ranking (pesos por posição):")
    escala_orig = cfg.PESOS_RANKING
    for escala, rotulo in [([0.50, 0.30, 0.20], "50/30/20"),
                           ([0.40, 0.35, 0.25], "40/35/25 (suave)"),
                           ([0.60, 0.25, 0.15], "60/25/15 (agressivo)"),
                           ([1.00, 0.00, 0.00], "100/0/0 (só a melhor)")]:
        cfg.PESOS_RANKING = escala
        r = bt.rodar_backtest(painel, est.pesos_ranking(completo).loc[painel.index])["retorno"]
        m = bt.avaliar(r, cdi)
        print(f"  {rotulo:22s} exCDI={m['excedente_cdi_aa']:>6.1%}"
              f"  Sharpe={m['sharpe']:>5.2f}  MaxDD={m['max_dd']:>5.0%}")
    cfg.PESOS_RANKING = escala_orig

    print("Custo de transação (sensibilidade):")
    for c, rotulo in [(0.0005, "5 bps"), (0.0010, "10 bps"), (0.0025, "25 bps")]:
        r = bt.rodar_backtest(painel, pesos["ranking"], custo=c)["retorno"]
        m = bt.avaliar(r, cdi)
        print(f"  {rotulo:12s} exCDI={m['excedente_cdi_aa']:>6.1%}  Sharpe={m['sharpe']:>5.2f}")

    # ── veredito ────────────────────────────────────────────────────────────
    mt, me = metricas["Robô Fundamento (ranking)"], metricas["Rebal. puro (peso igual)"]
    print(f"\n{'=' * 72}\nVEREDITO\n{'=' * 72}")
    print(f"  Robô excede o CDI em {mt['excedente_cdi_aa']:+.1%} a.a. "
          f"(bate o CDI em {mt['meses_acima_cdi']:.0%} dos meses)")
    print(f"  Significância: t={mt['t']:.2f}, p={mt['p']:.4f} -> "
          f"{'SIGNIFICATIVO (95%)' if mt['p'] < 0.05 else 'NÃO significativo'}")
    print(f"  A camada tática agrega? Sharpe {me['sharpe']:.2f} (rebal. puro) "
          f"-> {mt['sharpe']:.2f} (tático)   MaxDD {me['max_dd']:.0%} -> {mt['max_dd']:.0%}")
    print(f"  Giro médio: {bt_ranking['giro'].mean():.1%} ao mês "
          f"(custo total {bt_ranking['custo'].sum():.1%} no período)")

    # ── salva ───────────────────────────────────────────────────────────────
    cfg.DATA_PROC.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(carteiras).to_csv(cfg.DATA_PROC / "robo_retornos.csv",
                                   sep=";", encoding="utf-8-sig")
    bt_ranking[[f"w_{c}" for c in cfg.CLASSES]].to_csv(
        cfg.DATA_PROC / "robo_pesos.csv", sep=";", encoding="utf-8-sig")
    pd.DataFrame(metricas).T.to_csv(cfg.DATA_PROC / "robo_metricas.csv",
                                    sep=";", encoding="utf-8-sig")
    print("\nSalvo em data/processed/: robo_retornos.csv, robo_pesos.csv, robo_metricas.csv")


if __name__ == "__main__":
    main()
