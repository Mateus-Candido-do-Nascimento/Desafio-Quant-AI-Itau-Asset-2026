"""
Robô Fundamento — as regras de alocação.

Duas estratégias, para poder comparar (ablation):

  ESTÁTICA  — mantém a alocação-alvo fixa, só rebalanceia de volta a ela.
              É o "rebalanceamento periódico puro".

  TÁTICA    — parte da mesma alocação-alvo, mas ajusta conforme o cenário:
              (a) filtro de tendência: classe de risco em queda sai da carteira
                  e o peso dela vai para o CDI;
              (b) inclinação por juro real: com juro real alto, parte do peso de
                  ações migra para o CDI.

DISCIPLINA POINT-IN-TIME: os pesos do mês t são decididos com informação até
t-1. Nenhuma função aqui enxerga o próprio mês que está alocando.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as cfg


# ── Sinais ──────────────────────────────────────────────────────────────────
def sinal_tendencia(painel: pd.DataFrame) -> pd.DataFrame:
    """Classe de risco está acima da própria média móvel? (True = comprada)

    Regra clássica de alocação tática (Faber, 2007): segurar a classe enquanto
    ela está em tendência de alta; sair quando perde a média móvel. O `shift(1)`
    garante que a decisão do mês t usa apenas dados até t-1.
    """
    out = pd.DataFrame(index=painel.index)
    for c in cfg.CLASSES_RISCO:
        nivel = painel[f"nivel_{c}"]
        media = nivel.rolling(cfg.JANELA_TENDENCIA).mean()
        out[c] = (nivel > media).shift(1)
    return out


def sinal_juro_real(painel: pd.DataFrame) -> pd.Series:
    """Juro real está alto em relação à própria história? (True = alto)

    Juro real ≈ CDI acumulado 12m menos IPCA 12m. "Alto" = acima da mediana de
    tudo que se conhecia até o mês anterior (expanding median) — sem olhar o
    futuro. Com juro real alto, renda fixa paga bem demais para correr risco.
    """
    cdi_12m = (1 + painel["ret_CDI"]).rolling(12).apply(lambda x: x.prod(), raw=True) - 1
    juro_real = (1 + cdi_12m) / (1 + painel["ipca_12m"]) - 1
    mediana = juro_real.expanding(min_periods=24).median()
    return (juro_real > mediana).shift(1)


# ── Regras de alocação ──────────────────────────────────────────────────────
def aplicar_teto_cripto(pesos: pd.DataFrame) -> pd.DataFrame:
    """Limita cripto a TETO_CRIPTO; o excedente vai para o caixa.

    Regra de construção de carteira, não de sinal — por isso vale para TODAS as
    estratégias (inclusive os benchmarks). Sem ela, a comparação ficaria injusta:
    uma carteira de pesos iguais com 1/6 em um ativo de ~70% de volatilidade não
    é um benchmark razoável de multiativos.
    """
    if "Cripto" not in pesos.columns:
        return pesos
    out = pesos.copy()
    excedente = (out["Cripto"] - cfg.TETO_CRIPTO).clip(lower=0)
    out["Cripto"] -= excedente
    out[cfg.CAIXA] += excedente
    return out


def pesos_estatico(painel: pd.DataFrame) -> pd.DataFrame:
    """Alocação-alvo fixa, todo mês. O rebalanceamento puro."""
    return aplicar_teto_cripto(pd.DataFrame(
        [cfg.PESO_ALVO] * len(painel), index=painel.index
    )[cfg.CLASSES])


def pesos_tatico(painel: pd.DataFrame) -> pd.DataFrame:
    """Alocação-alvo ajustada pelo cenário (tendência + juro real)."""
    tend = sinal_tendencia(painel)
    juro_alto = sinal_juro_real(painel)

    linhas = []
    for dt in painel.index:
        p = dict(cfg.PESO_ALVO)

        # (a) filtro de tendência: classe em queda vira caixa (CDI)
        for c in cfg.CLASSES_RISCO:
            ligado = tend.loc[dt, c]
            if ligado is not True:  # False ou NaN (histórico insuficiente) -> fora
                p[cfg.CAIXA] += p[c]
                p[c] = 0.0

        # (b) inclinação por juro real: renda fixa pagando bem -> menos ações
        if juro_alto.loc[dt] is True and p["Acoes"] > 0:
            desloca = min(cfg.TILT_JURO_REAL, p["Acoes"])
            p["Acoes"] -= desloca
            p[cfg.CAIXA] += desloca

        linhas.append(p)
    return aplicar_teto_cripto(pd.DataFrame(linhas, index=painel.index)[cfg.CLASSES])


def pesos_ranking(painel: pd.DataFrame) -> pd.DataFrame:
    """RANKING no rebalanceamento — a alocação por mérito.

    Todo mês o robô ordena as 4 classes (CDI incluído) pelo retorno dos últimos
    12 meses e concentra a carteira nas melhores, em vez de dividir igual. Duas
    travas herdadas da literatura de dual momentum (Antonacci; Faber):

      · momentum absoluto — uma classe de risco só entra se estiver rendendo
        mais que o CDI. Se nenhuma estiver, o robô fica 100% em CDI.
      · momentum relativo — entre as aprovadas, a melhor pesa mais.

    Pesos por posição no ranking: 50% / 30% / 20%. O que sobra vai para o CDI.
    Tudo com `shift(1)`: a decisão do mês t usa retorno até t-1.
    """
    mom = pd.DataFrame(index=painel.index)
    for c in cfg.CLASSES:
        nivel = painel[f"nivel_{c}"]
        mom[c] = (nivel / nivel.shift(12) - 1).shift(1)

    escala = cfg.PESOS_RANKING
    linhas = []
    for dt in painel.index:
        m = mom.loc[dt]
        p = {c: 0.0 for c in cfg.CLASSES}
        if m.isna().any():                      # histórico insuficiente -> caixa
            p[cfg.CAIXA] = 1.0
            linhas.append(p)
            continue

        # momentum absoluto: só classe de risco rendendo mais que o CDI
        aprovadas = [c for c in cfg.CLASSES_RISCO if m[c] > m[cfg.CAIXA]]
        # momentum relativo: ordena as aprovadas da melhor para a pior
        aprovadas.sort(key=lambda c: -m[c])

        for peso, c in zip(escala, aprovadas):
            p[c] = peso

        # teto de risco: cripto é volátil demais (~70% a.a.) para receber o peso
        # cheio do ranking. O excedente vai para o caixa, não para outra classe.
        if "Cripto" in p and p["Cripto"] > cfg.TETO_CRIPTO:
            p["Cripto"] = cfg.TETO_CRIPTO

        p[cfg.CAIXA] = 1.0 - sum(p[c] for c in cfg.CLASSES_RISCO)  # resto em caixa
        linhas.append(p)
    return pd.DataFrame(linhas, index=painel.index)[cfg.CLASSES]


def pesos_ranking_ia(painel: pd.DataFrame, regime: pd.Series,
                     tilt: float | None = None) -> pd.DataFrame:
    """RANKING + o regime de juros lido nas atas do Copom (a camada de IA).

    Parte da carteira que `pesos_ranking` produziria e a INCLINA conforme o que
    o Banco Central comunicou na última ata publicada:

        aperto        -> peso de risco x (1 - tilt)   [sobra vai para o CDI]
        afrouxamento  -> peso de risco x (1 + tilt)   [tirado do CDI]
        neutro / sem ata -> não mexe

    A intuição é a tese do robô aplicada à política monetária: em aperto, o CDI
    fica mais caro de abrir mão e o custo de oportunidade do risco sobe; em
    afrouxamento, acontece o contrário. O momentum de 12 meses só percebe isso
    depois que apareceu no preço — a ata diz antes.

    DUAS TRAVAS, herdadas das nossas próprias rejeições anteriores:
      · a exposição a risco é limitada a 100% (`min(..., 1.0)`) — nada de
        alavancagem, que foi o motivo de rejeitarmos o vol-targeting;
      · a inclinação NUNCA reabilita uma classe reprovada no momentum absoluto.
        Ela só redimensiona o que o ranking já aprovou. A trava do CDI continua
        soberana: se nenhuma classe bate o CDI, o robô fica 100% em CDI,
        independentemente do que a ata disser.

    POINT-IN-TIME: `regime` já vem defasado de `copom.regime_mensal()` — só
    contém atas publicadas até o fim do mês anterior.
    """
    tilt = cfg.TILT_COPOM if tilt is None else tilt
    base = pesos_ranking(painel)
    fator = {"aperto": 1.0 - tilt, "afrouxamento": 1.0 + tilt}

    regime = regime.reindex(base.index)
    linhas = []
    for dt in base.index:
        p = base.loc[dt].to_dict()
        f = fator.get(regime.loc[dt], 1.0)            # neutro/NaN -> 1.0

        risco = sum(p[c] for c in cfg.CLASSES_RISCO)
        if f != 1.0 and risco > 0:
            # Reescala proporcionalmente, respeitando o teto de 100% em risco.
            escala = min(f, 1.0 / risco)
            for c in cfg.CLASSES_RISCO:
                p[c] *= escala
            p[cfg.CAIXA] = 1.0 - sum(p[c] for c in cfg.CLASSES_RISCO)
        linhas.append(p)

    return aplicar_teto_cripto(pd.DataFrame(linhas, index=base.index)[cfg.CLASSES])


def pesos_benchmark_balanceado(painel: pd.DataFrame) -> pd.DataFrame:
    """Carteira balanceada clássica (60% CDI / 40% ações), rebalanceada."""
    return pd.DataFrame(
        [cfg.BENCH_BALANCEADO] * len(painel), index=painel.index
    )[cfg.CLASSES]
