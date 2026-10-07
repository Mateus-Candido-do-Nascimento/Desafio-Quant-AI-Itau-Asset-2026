"""
Robô Fundamento — parâmetros da estratégia.

Fonte única de verdade: toda decisão de escopo mora aqui. Se você quer entender
as escolhas do robô sem ler o resto do código, comece por este arquivo.
"""
from __future__ import annotations

from pathlib import Path

# ── Caminhos ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROC = ROOT / "data" / "processed"

# ── Universo: as 4 classes de ativo ─────────────────────────────────────────
# CDI é a classe "sem risco" (e o caixa para onde o robô foge). As outras três
# são as classes de risco, cada uma com um papel diferente na carteira:
#   Ações  -> crescimento
#   Ouro   -> proteção contra crise/inflação
#   Dólar  -> proteção contra risco Brasil
#   Global -> bolsa internacional (diversificação e proteção cambial)
#
# CRIPTO fica FORA da estratégia principal — é uma EXTENSÃO documentada.
# Motivo (decisão metodológica, ver docs/resultados_robo.md §4c): ETFs de bitcoin
# na B3 só existem desde 2021. Incluí-la no backtest desde 2015 significaria
# alocar no ativo de melhor desempenho da década num período em que ele não era
# investível de forma regulada no Brasil — e, no subperíodo investível (2021+),
# o ganho perde significância (p = 0,50). Aplicamos a ela o mesmo critério que
# usamos para rejeitar o vol-targeting e o risk parity: se só funciona num
# recorte, não vira estratégia principal.
#
# Para rodar a extensão: INCLUIR_CRIPTO = True (o robô passa a 6 classes).
INCLUIR_CRIPTO = False

CLASSES_RISCO = ["Acoes", "Global", "Ouro", "Dolar"]
if INCLUIR_CRIPTO:
    CLASSES_RISCO = CLASSES_RISCO + ["Cripto"]
CAIXA = "CDI"
CLASSES = [CAIXA] + CLASSES_RISCO

# Tickers no yfinance. Ouro, S&P e BTC são cotados em USD -> convertemos para
# BRL, que é a moeda do investidor.
#   Global: usamos ^SP500TR (TOTAL return) e não ^GSPC (price return) — o índice
#   de preço ignora dividendos e subestima a classe em ~2% ao ano. Quem compra
#   IVVB11 recebe os dividendos reinvestidos.
TICKER_ACOES = "^BVSP"
TICKER_GLOBAL_USD = "^SP500TR"
TICKER_OURO_USD = "GC=F"
TICKER_DOLAR = "BRL=X"
TICKER_CRIPTO_USD = "BTC-USD"

# Teto de alocação em cripto. Sem teto, o ranking chegaria a colocar 40% da
# carteira num ativo de ~70% de volatilidade — irreal para um multiativos. Com
# 10% capturamos a assimetria sem descaracterizar a carteira: o drawdown quase
# não muda (-11% -> -12%) e o Sharpe sobe de 0,53 para 0,85.
# RESSALVA (documentada): acesso regulado via ETF na B3 (HASH11 etc.) existe
# desde 2021; antes disso, só por corretora de cripto. Ver docs/resultados_robo.md.
TETO_CRIPTO = 0.10

# Séries do Banco Central (API SGS, gratuita)
SGS_CDI = 12    # CDI diário (% ao dia)
SGS_IPCA = 433  # IPCA mensal (% ao mês)

# ── Período do backtest ─────────────────────────────────────────────────────
DATA_INICIO = "2010-01-01"

# ── Alocação-alvo (a carteira "neutra") ─────────────────────────────────────
# Ponto de partida: peso igual entre as classes. A camada tática desvia daqui.
PESO_ALVO = {c: 0.20 for c in CLASSES}

# A partir de quando a bolsa global é investível na B3 (IVVB11, nov/2014).
# O backtest principal começa aqui para não usar uma classe que o investidor
# brasileiro ainda não conseguia comprar via ETF.
DATA_INICIO_INVESTIVEL = "2015-01-01"

# ── Camada tática ───────────────────────────────────────────────────────────
# Filtro de tendência (Faber, 2007): uma classe de risco só entra na carteira
# se estiver acima da própria média móvel. Se não estiver, o peso dela vai para
# o CDI. É a regra que faz o robô "sair" antes de uma queda prolongada.
JANELA_TENDENCIA = 10  # meses

# Inclinação por juro real: quando o juro real está alto (acima da mediana
# histórica conhecida ATÉ AQUELE MÊS), o robô move parte do peso de ações para
# o CDI — porque renda fixa está pagando bem demais para correr risco.
TILT_JURO_REAL = 0.10  # 10 p.p. deslocados de Ações -> CDI

# Pesos por posição no ranking (estratégia de alocação por mérito): a melhor
# classe do mês leva 40%, depois 30/20/10/5%. O que
# sobra vai para o CDI — inclusive tudo, se nenhuma classe de risco estiver
# rendendo mais que ele.
PESOS_RANKING = [0.40, 0.30, 0.20, 0.10, 0.05][:len(CLASSES_RISCO)]

# ── Camada de IA generativa: as atas do Copom ───────────────────────────────
# Um LLM lê cada ata e classifica o regime de juros que o documento comunica
# (aperto / neutro / afrouxamento). O regime INCLINA a alocação do ranking:
#
#   aperto        -> multiplica os pesos de risco por (1 - TILT_COPOM)
#   afrouxamento  -> multiplica os pesos de risco por (1 + TILT_COPOM)
#   neutro / sem ata publicada -> não mexe
#
# O que sobra (ou falta) vai para o CDI. A exposição total a risco nunca passa
# de 100%: NÃO há alavancagem — foi exatamente por alavancagem disfarçada que
# rejeitamos o vol-targeting (ver docs/busca_significancia.md).
#
# TILT_COPOM = 0,25 é escolha A PRIORI ("um quarto da exposição a risco"), não
# resultado de otimização. `rodar_ia.py` testa 0,10 a 0,50 para mostrar que a
# conclusão não depende deste número.
TILT_COPOM = 0.25

# As atas só estão disponíveis em PDF pela API do BC a partir da 200ª reunião
# (jul/2016). Antes disso o site serve página HTML renderizada por JavaScript,
# sem texto acessível. Portanto a camada de IA só atua de ago/2016 em diante;
# nos meses anteriores o robô com IA é IDÊNTICO ao robô sem IA. Isso é uma
# limitação de disponibilidade de dado, não uma escolha — e está reportada.
COPOM_PRIMEIRA_ATA = "2016-08-01"

# ── Execução ────────────────────────────────────────────────────────────────
FREQ_REBALANCE = 1   # meses entre rebalanceamentos (1 = mensal)
CUSTO_GIRO = 0.0010  # 10 bps por unidade de giro (corretagem + emolumentos)

# ── Benchmarks ──────────────────────────────────────────────────────────────
# CDI é a régua principal: no Brasil, uma estratégia só vale a pena se render
# mais que dinheiro parado sem risco. O 60/40 é a carteira balanceada clássica.
BENCH_BALANCEADO = {c: 0.0 for c in CLASSES} | {"CDI": 0.60, "Acoes": 0.40}
