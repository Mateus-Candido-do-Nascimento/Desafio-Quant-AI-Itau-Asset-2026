"""
Camada de IA generativa — o teste honesto de se ela agrega alguma coisa.

Uso:  python src/robo/rodar_ia.py            (braço mecânico — não precisa de chave)
      python src/robo/copom.py --classificar (roda o LLM, uma vez, e grava o CSV)
      python src/robo/rodar_ia.py            (agora com os dois braços)

O QUE ESTE ARQUIVO RESPONDE
---------------------------
Não é "a IA melhorou o robô?" — essa pergunta é fácil de responder para o lado
que a gente quiser. É:

  1. O robô com a leitura das atas bate o robô sem ela?
  2. E bate o MESMO SINAL construído sem nenhuma IA (a direção da última
     mudança da Selic)? Se não bater, o LLM não agregou — só reproduziu uma
     informação que já estava num número público, e reportamos isso.
  3. A conclusão sobrevive a mudar o tamanho da inclinação (0,10 a 0,50)?
  4. E no período em que a camada foi desenhada para ajudar (2022-23, a virada
     de regime que é a única derrota do robô)?

A pergunta 2 é a que protege o projeto. Um LLM treinado em 2026 lendo uma ata
de 2016 conhece o desfecho; o braço mecânico não conhece nada além do que era
público na data. Se os dois empatam, não há vantagem escondida a explicar.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import backtest as bt
import config as cfg
import copom
import dados
import estrategia as est

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

TILTS = (0.10, 0.25, 0.40, 0.50)
SUBPERIODOS = {
    "2016-08 a 2019": ("2016-08-01", "2019-12-31"),
    "2020-21 (covid)": ("2020-01-01", "2021-12-31"),
    "2022-23 (virada)": ("2022-01-01", "2023-12-31"),
    "2024 em diante": ("2024-01-01", "2030-12-31"),
}


def _cab() -> str:
    return (f"{'braço':30s}{'retorno':>8s}{'exCDI':>9s}{'Sharpe':>8s}"
            f"{'MaxDD':>8s}{'t':>7s}{'p':>8s}")


def _linha(nome: str, m: dict) -> str:
    return (f"{nome:30s}{m['retorno_aa']:>8.1%}{m['excedente_cdi_aa']:>9.1%}"
            f"{m['sharpe']:>8.2f}{m['max_dd']:>8.0%}{m['t']:>7.2f}{m['p']:>8.3f}")


def main() -> None:
    print("=" * 78)
    print("CAMADA DE IA — o robô lendo as atas do Copom")
    print("=" * 78)

    completo = dados.carregar_painel()
    hoje = pd.Timestamp.today()
    if completo.index[-1].month == hoje.month and completo.index[-1].year == hoje.year:
        completo = completo.iloc[:-1]

    # ── os sinais de regime ─────────────────────────────────────────────────
    ROTULOS = {
        "llm": "Robô + IA (regime)",             # sinal PRIMÁRIO pré-registrado
        "llm_vies": "Robô + IA (viés prosp.)",   # secundário — hipótese H3
        "mecanico": "Robô + Selic (controle)",   # o braço sem nenhuma IA
    }

    fontes: dict[str, pd.Series] = {}
    try:
        for f in ("llm", "llm_vies"):
            fontes[f] = copom.regime_mensal(completo.index, fonte=f)
        print("Sinais do LLM    : carregados de data/processed/copom_regimes.csv")
    except FileNotFoundError:
        print("Sinais do LLM    : AUSENTES — rode `python src/robo/copom.py "
              "--classificar` com uma chave de API para preencher.")
    fontes["mecanico"] = copom.regime_mensal(completo.index, fonte="mecanico")
    print("Sinal mecânico   : direção da última mudança da Selic (sem IA)")

    # ── as carteiras ────────────────────────────────────────────────────────
    carteiras = {"Robô sem IA (base)": est.pesos_ranking(completo)}
    for nome, reg in fontes.items():
        carteiras[ROTULOS[nome]] = est.pesos_ranking_ia(completo, reg)

    painel = completo[completo.index >= cfg.DATA_INICIO_INVESTIVEL]
    carteiras = {k: v.loc[painel.index] for k, v in carteiras.items()}
    cdi = painel["ret_CDI"]
    print(f"\nPeríodo do backtest: {painel.index.min().date()} a "
          f"{painel.index.max().date()} ({len(painel)} meses)")
    print(f"Camada de IA ativa a partir de {cfg.COPOM_PRIMEIRA_ATA[:7]} "
          "(quando as atas viram PDF na API do BC)\n")

    retornos = {k: bt.rodar_backtest(painel, v)["retorno"] for k, v in carteiras.items()}

    # ── 1. o quadro principal ───────────────────────────────────────────────
    print("─" * 78)
    print("1. PERÍODO COMPLETO")
    print("─" * 78)
    print(_cab())
    metricas = {}
    for nome, r in retornos.items():
        metricas[nome] = bt.avaliar(r, cdi)
        print(_linha(nome, metricas[nome]))

    # ── 2. só onde o sinal existe ───────────────────────────────────────────
    # Antes de ago/2016 os braços são idênticos por construção; incluir esse
    # trecho dilui o efeito (para os dois lados) e esconde o que está em teste.
    jan = painel.index >= cfg.COPOM_PRIMEIRA_ATA
    print("\n" + "─" * 78)
    print(f"2. SÓ ONDE A CAMADA ATUA ({cfg.COPOM_PRIMEIRA_ATA[:7]} em diante, "
          f"{int(jan.sum())} meses)")
    print("─" * 78)
    print(_cab())
    for nome, r in retornos.items():
        print(_linha(nome, bt.avaliar(r[jan], cdi[jan])))

    # ── 3. sensibilidade ao tamanho da inclinação ───────────────────────────
    print("\n" + "─" * 78)
    print("3. A CONCLUSÃO DEPENDE DO TAMANHO DA INCLINAÇÃO?")
    print("─" * 78)
    print(f"{'tilt':>6s}" + "".join(f"{n:>26s}" for n in fontes))
    for t in TILTS:
        cel = []
        for nome, reg in fontes.items():
            p = est.pesos_ranking_ia(completo, reg, tilt=t).loc[painel.index]
            m = bt.avaliar(bt.rodar_backtest(painel, p)["retorno"], cdi)
            cel.append(f"{m['excedente_cdi_aa']:>14.1%} (Sh {m['sharpe']:.2f})")
        marca = "  <- a priori" if t == cfg.TILT_COPOM else ""
        print(f"{t:>6.0%}" + "".join(cel) + marca)

    # ── 4. subperíodos ──────────────────────────────────────────────────────
    print("\n" + "─" * 78)
    print("4. POR SUBPERÍODO (excedente sobre o CDI, ao ano)")
    print("─" * 78)
    print(f"{'subperíodo':20s}" + "".join(f"{n:>22s}" for n in retornos))
    for rot, (ini, fim) in SUBPERIODOS.items():
        m = (painel.index >= ini) & (painel.index <= fim)
        if m.sum() < 6:
            continue
        cel = [f"{bt.avaliar(r[m], cdi[m])['excedente_cdi_aa']:>22.1%}"
               for r in retornos.values()]
        print(f"{rot:20s}" + "".join(cel))

    # ── 5. o teste que reprovou o vol-targeting ─────────────────────────────
    # Rejeitamos o vol-targeting (p=0,029) por ser alavancagem disfarçada:
    # ele subia a exposição a risco de 62% para 70%, escala média 1,16x. Toda
    # variante nova passa pela mesma régua, inclusive esta. Se a inclinação só
    # melhora o Sharpe porque aumentou o risco, ela é reprovada pelo mesmo
    # motivo — e o script diz isso na cara.
    print("\n" + "─" * 78)
    print("5. É ALAVANCAGEM DISFARÇADA? (a régua que reprovou o vol-targeting)")
    print("─" * 78)
    r_base = carteiras["Robô sem IA (base)"][cfg.CLASSES_RISCO].sum(axis=1)
    print(f"{'braço':30s}{'exposição':>12s}{'escala':>9s}{'meses 100% CDI':>17s}")
    print(f"{'Robô sem IA (base)':30s}{r_base.mean():>12.1%}{1.0:>9.3f}"
          f"{int((r_base < 1e-9).sum()):>17d}")
    for rot, w in carteiras.items():
        if rot == "Robô sem IA (base)":
            continue
        r_ia = w[cfg.CLASSES_RISCO].sum(axis=1)
        escala = (r_ia / r_base.replace(0, float("nan"))).mean()
        print(f"{rot:30s}{r_ia.mean():>12.1%}{escala:>9.3f}"
              f"{int((r_ia < 1e-9).sum()):>17d}")
        if r_ia.mean() > r_base.mean() + 0.01 or escala > 1.02:
            print(f"  >> ALERTA: '{rot}' AUMENTA a exposição a risco. Pelo mesmo")
            print("     critério que reprovou o vol-targeting, esta variante NÃO")
            print("     pode ser vendida como melhora de Sharpe. REPROVAR.")
        else:
            print("  OK: melhora o Sharpe REDUZINDO exposição a risco — o oposto")
            print("      do vol-targeting. Não é alavancagem.")

    # ── 6. o LLM diz algo diferente do número? ──────────────────────────────
    if "llm" in fontes:
        print("\n" + "─" * 78)
        print("6. O LLM CONCORDA COM O SINAL MECÂNICO?")
        print("─" * 78)
        a, b = fontes["llm"].reindex(painel.index), fontes["mecanico"].reindex(painel.index)
        val = a.notna() & b.notna()
        conc = (a[val] == b[val]).mean()
        print(f"Concordância: {conc:.0%} dos {int(val.sum())} meses com os dois sinais")
        print("\nMatriz (linhas = LLM, colunas = Selic):")
        print(pd.crosstab(a[val], b[val]).to_string())
        print("\nSe a concordância fosse ~100%, o LLM estaria só reproduzindo a")
        print("direção da Selic — e a camada de IA não teria conteúdo próprio.")

    # ── 7. H3: a vantagem vem da parte que o número NÃO tem? ────────────────
    # Este é o teste pré-registrado contra contaminação (docs/pre_registro_ia.md).
    #
    # A decisão do Copom já está na Selic — o LLM não precisa ler nada para
    # saber dela. O que SÓ existe no texto é a sinalização prospectiva. Então
    # separamos os meses em que a leitura DIVERGE do número: se a vantagem do
    # LLM se concentra aí, é leitura genuína do texto. Se está espalhada por
    # igual, inclusive onde texto e número dizem a mesma coisa, o ganho não veio
    # da leitura — e aí é suspeita de contaminação, não mérito.
    if "llm_vies" in fontes:
        print("\n" + "─" * 78)
        print("7. A VANTAGEM VEM DO QUE O NÚMERO NÃO TEM? (teste pré-registrado H3)")
        print("─" * 78)
        vies = fontes["llm_vies"].reindex(painel.index)
        mec = fontes["mecanico"].reindex(painel.index)
        val = vies.notna() & mec.notna()
        diverge, concorda = val & (vies != mec), val & (vies == mec)

        r_ia = retornos[ROTULOS["llm_vies"]]
        r_mec = retornos[ROTULOS["mecanico"]]
        print(f"{'meses':28s}{'n':>5s}{'IA − controle (a.a.)':>24s}")
        for rot, m in (("texto DIVERGE do número", diverge),
                       ("texto CONCORDA com número", concorda)):
            if m.sum() < 6:
                print(f"{rot:28s}{int(m.sum()):>5d}{'(poucos meses)':>24s}")
                continue
            d = (bt.avaliar(r_ia[m], cdi[m])["excedente_cdi_aa"]
                 - bt.avaliar(r_mec[m], cdi[m])["excedente_cdi_aa"])
            print(f"{rot:28s}{int(m.sum()):>5d}{d:>23.1%}")

        print("\nLeitura do resultado (regra escrita ANTES de rodar o LLM):")
        print("  · vantagem concentrada na DIVERGÊNCIA -> leitura genuína, aceitar")
        print("  · vantagem espalhada por igual        -> suspeita de contaminação,")
        print("    não usar como resultado principal")

    # ── salva ───────────────────────────────────────────────────────────────
    saida = cfg.DATA_PROC / "robo_ia_metricas.csv"
    saida.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(metricas).T.to_csv(saida, encoding="utf-8")
    pd.DataFrame(retornos).to_csv(cfg.DATA_PROC / "robo_ia_retornos.csv",
                                  encoding="utf-8")
    print(f"\nSalvo em {saida}")

    if "llm" not in fontes:
        print("\n" + "!" * 78)
        print("ATENÇÃO: rodou só com o braço de controle (sem IA). O número do")
        print("LLM ainda não existe — não escreva nada sobre ele no relatório")
        print("até rodar `python src/robo/copom.py --classificar`.")
        print("!" * 78)


if __name__ == "__main__":
    main()
