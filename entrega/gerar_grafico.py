"""
Gera o gráfico do relatório final.

Uso: venv/Scripts/python.exe entrega/gerar_grafico.py
Saída: entrega/grafico.png

Existe porque o relatório embutia um PNG que nenhum código do repositório
produzia. Agora a figura é reprodutível junto com o resto dos números.

DECISÕES DE VISUALIZAÇÃO
------------------------
A primeira versão deste gráfico mostrava a alocação como área empilhada das 5
classes ao longo dos 139 meses. Era ilegível, e o motivo é estrutural: são
cerca de 700 faixas coloridas, e como a posição de cada banda depende do que
está empilhado abaixo dela, o olho não consegue seguir nenhuma classe ao longo
do tempo. O resultado parecia chuvisco.

Agregar por ano também não resolve: achatar 5 classes numa média anual faria o
robô parecer uma carteira estática, destruindo justamente a evidência de que
ele gira entre as classes.

A solução foi separar as duas afirmações do relatório em dois painéis, cada um
respondendo uma pergunta só:

  · **Exposição a risco no tempo** (em cima): quando o robô está defendido?
    Azul é risco, cinza é caixa. Os triângulos marcam os meses em que ele se
    recolheu 100% ao CDI. O bloco cinza de 2022-2023 é a defesa em ação.
  · **Composição média** (embaixo): ele gira mesmo entre as classes, ou é uma
    aposta disfarçada numa só?

A exposição usa `step="post"` porque a alocação é função ESCADA: salta no
rebalanceamento e fica parada até o mês seguinte. Interpolação diagonal
sugeriria uma transição suave que não existe.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter

AQUI = Path(__file__).resolve().parent
SAIDA = AQUI / "grafico.png"
sys.path.insert(0, str(AQUI.parent / "src" / "robo"))

import backtest as bt          # noqa: E402
import config as cfg           # noqa: E402
import dados                   # noqa: E402
import estrategia as est       # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# CDI em cinza neutro (é o caixa, não uma aposta); as classes de risco em cores
# bem separadas entre si e distinguíveis em impressão preto e branco.
COR = {
    "CDI": "#C7CBD1",
    "Acoes": "#1A4F8A",
    "Global": "#2E8B74",
    "Ouro": "#E0A32E",
    "Dolar": "#B0453C",
}
ROTULO = {"CDI": "CDI (caixa)", "Acoes": "Ações", "Global": "Global",
          "Ouro": "Ouro", "Dolar": "Dólar"}


def main() -> None:
    c = dados.carregar_painel()
    hoje = pd.Timestamp.today()
    if c.index[-1].month == hoje.month and c.index[-1].year == hoje.year:
        c = c.iloc[:-1]
    rec = c.index[c.index >= cfg.DATA_INICIO_INVESTIVEL]

    w_robo = est.pesos_ranking(c)
    series = {
        "Robô Fundamento": bt.rodar_backtest(c, w_robo)["retorno"].loc[rec],
        "Rebal. puro": bt.rodar_backtest(c, est.pesos_estatico(c))["retorno"].loc[rec],
        "Ibovespa": c["ret_Acoes"].loc[rec],
        "CDI": c["ret_CDI"].loc[rec],
    }
    # O CDI usa o MESMO cinza nos dois painéis: ele é a régua do projeto, e
    # trocar sua cor entre gráficos obrigaria o leitor a reaprender a legenda.
    # O Ibovespa fica em vermelho para não competir com o azul do robô.
    estilo = {"Robô Fundamento": ("#1A4F8A", 2.1), "Rebal. puro": ("#2E8B74", 1.4),
              "Ibovespa": ("#B0453C", 1.4), "CDI": ("#8A9099", 1.8)}

    ordem = ["CDI"] + [k for k in cfg.CLASSES_RISCO if k in w_robo.columns]

    fig = plt.figure(figsize=(13.2, 5.2))
    gs = fig.add_gridspec(len(ordem), 2, width_ratios=[1.12, 1],
                          wspace=0.16, hspace=0.32)
    ax1 = fig.add_subplot(gs[:, 0])                       # capital acumulado
    faixas = [fig.add_subplot(gs[i, 1]) for i in range(len(ordem))]

    # ── Painel esquerdo: capital acumulado ──────────────────────────────────
    for nome, r in series.items():
        cor, lw = estilo[nome]
        # CDI tracejado: sinaliza visualmente que é linha de referência, não
        # uma estratégia concorrente.
        ax1.plot(rec, (1 + r).cumprod(), color=cor, linewidth=lw, label=nome,
                 linestyle="--" if nome == "CDI" else "-")
    ax1.set_yscale("log")
    ax1.set_yticks([1, 2, 3, 4, 5, 6])
    ax1.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}x"))
    ax1.set_ylabel("capital acumulado", fontsize=10)
    ax1.set_title("Capital acumulado (escala log)", fontsize=11, pad=8)
    ax1.legend(fontsize=9, loc="upper left", frameon=False)
    ax1.grid(alpha=0.25, linewidth=0.6)

    # ── Painéis da direita: uma faixa por classe ────────────────────────────
    # Empilhar as 5 classes num painel só era ilegível: as bandas se deslocam
    # conforme o que está embaixo, e nenhuma cor fica identificável. Aqui cada
    # classe tem a SUA faixa, na SUA cor, com o nome escrito dentro dela.
    # Não existe legenda para consultar: o rótulo está no próprio dado.
    wr = w_robo.loc[rec]
    medias = wr.mean() * 100

    for ax, classe in zip(faixas, ordem):
        peso = wr[classe] * 100
        ax.fill_between(rec, 0, peso, step="post", color=COR[classe], linewidth=0)
        ax.set_ylim(0, 100)
        ax.set_xlim(rec.min(), rec.max())
        ax.set_yticks([])
        ax.set_ylabel("")

        # Nome e peso médio da classe, na cor da classe, dentro da faixa.
        ax.text(0.008, 0.72, f"{ROTULO[classe].split(' ')[0]}", fontsize=9,
                fontweight="bold", color="#2A2A28", transform=ax.transAxes,
                va="center",
                bbox=dict(facecolor="white", edgecolor="none", pad=1.2))
        ax.text(0.998, 0.72, f"média {medias[classe]:.0f}%", fontsize=8,
                color="#5A6068", transform=ax.transAxes, va="center", ha="right",
                bbox=dict(facecolor="white", edgecolor="none", pad=1.2))

        for lado in ("top", "right", "left"):
            ax.spines[lado].set_visible(False)
        ax.spines["bottom"].set_color("#D0D3D7")
        ax.tick_params(labelsize=8.5)
        if ax is not faixas[-1]:
            ax.set_xticklabels([])

    faixas[0].set_title("Quando o robô teve cada classe (peso de 0 a 100%)",
                        fontsize=11, pad=8)
    # A faixa do CDI cheia = robô 100% recolhido ao caixa. É a defesa em ação.
    n_caixa = int((wr["CDI"] > 0.95).sum())
    faixas[-1].set_xlabel(
        f"a faixa cheia do CDI marca os {n_caixa} meses em que o robô "
        f"saiu inteiro do risco", fontsize=8, color="#5A6068", labelpad=6)

    ax1.tick_params(labelsize=9)
    for lado in ("top", "right"):
        ax1.spines[lado].set_visible(False)

    fig.savefig(SAIDA, dpi=170, bbox_inches="tight", facecolor="white")
    meses_caixa = int((wr["CDI"] > 0.95).sum())
    print(f"Grafico gerado: {SAIDA}")
    print(f"  {len(rec)} meses | {meses_caixa} deles 100% em CDI")


if __name__ == "__main__":
    main()
