# Fundamentação — por que o Robô Fundamento não é um chute

> A estratégia não foi inventada por nós: ela é a adaptação ao Brasil de um
> método **publicado e replicado**. Este documento mostra a linhagem, o que a
> literatura brasileira diz, e onde está a nossa contribuição.
> Metodologia: [[metodologia_robo]] · Resultados: [[resultados_robo]]

---

## 1. A linhagem do método

Nossa regra tem nome na literatura: **Dual Momentum** (Gary Antonacci), que
combina duas ideias já documentadas isoladamente.

| Componente | Nome na literatura | O que faz no nosso robô |
|---|---|---|
| **Momentum absoluto** (*time-series*) | o retorno passado do próprio ativo prevê o futuro dele | a **trava**: classe só entra se render mais que o CDI |
| **Momentum relativo** (*cross-sectional*) | o desempenho relativo entre ativos prevê o desempenho relativo futuro | o **ranking**: a melhor classe pesa mais |

> *"O modelo de dual momentum usa o momentum relativo para selecionar os ativos
> de melhor desempenho e incorpora o momentum absoluto como filtro para investir
> em caixa quando o retorno excedente do ativo escolhido sobre o caixa é
> negativo."*

É **exatamente** a nossa regra — com o CDI no papel de caixa, que no Brasil é
muito mais forte do que o cash americano.

**Faber (2007), *A Quantitative Approach to Tactical Asset Allocation*:** aplicou
uma regra de média móvel de 10 meses sobre várias classes (ações EUA, ações
internacionais, commodities, REITs, títulos) e mostrou que ela **reduz
drasticamente o drawdown mantendo retorno de renda variável**.

**Isso é exatamente o que encontramos:** retorno acima da bolsa (15,5% vs 11,6%)
com **um terço do tombo** (−11% vs −37%). Nosso resultado não é uma surpresa
isolada — é a replicação de um efeito conhecido, em outro mercado.

---

## 2. O que a literatura brasileira diz (e por que isso nos favorece)

Aqui há uma nuance importante que **fortalece nossa escolha de desenho**:

- Um estudo de **momentum em ações individuais brasileiras** (2000–2023) concluiu
  que a aplicação estrita da teoria **não se mostrou robusta** no mercado
  brasileiro, com portfólios frequentemente **abaixo do Ibovespa**.
- Outros trabalhos encontram momentum funcionando, mas com resultados
  heterogêneos e sensíveis ao período.

**Por que isso é bom para nós:** o momentum contestado é o de **stock picking**
(escolher ações). O nosso é **momentum entre classes de ativo** — um problema
diferente, com menos ruído (5 séries em vez de centenas), menos custo e menos
sensibilidade a eventos idiossincráticos de empresa.

Ou seja: a evidência brasileira **desaconselha exatamente o que não fizemos**, e
não contradiz o que fizemos. Testamos os dois caminhos e escolhemos o robusto.

---

## 3. Onde está a nossa contribuição

O método é conhecido; o que é nosso:

1. **Adaptação ao Brasil com o CDI como caixa.** É a diferença que mais importa:
   nos EUA, o "cash" rende ~0–4%; aqui rende ~10% **sem risco**. Isso torna a
   trava de momentum absoluto muito mais poderosa — o robô tem para onde fugir.
   Todas as métricas medidas como **excedente ao CDI**, não sobre a bolsa.
2. **Cardápio de classes desenhado para o investidor brasileiro:** CDI, Ibovespa,
   S&P 500 **em reais** (IVVB11), ouro em reais e dólar. A inclusão da bolsa
   global foi decisiva — o Ibovespa sozinho mal supera o CDI.
3. **Backtest próprio, com rigor explícito** contra as três armadilhas do edital.
4. **Ablation honesto:** medimos separadamente o valor do rebalanceamento puro e
   o do ranking — e reportamos que a estrutura entrega mais que a esperteza.

---

## 4. Referências

**Momentum e alocação tática**
- Antonacci, G. (2014). *Dual Momentum Investing*. McGraw-Hill.
- Faber, M. (2007). *A Quantitative Approach to Tactical Asset Allocation*.
  Journal of Wealth Management —
  [resumo](https://www.researchgate.net/publication/228202718_A_Quantitative_Approach_to_Tactical_Asset_Allocation).
- Moskowitz, T., Ooi, Y. H., & Pedersen, L. H. (2012). *Time Series Momentum*.
  Journal of Financial Economics.
- Jegadeesh, N., & Titman, S. (1993). *Returns to Buying Winners and Selling
  Losers*. Journal of Finance.

**Discussões aplicadas (replicações independentes)**
- [Alpha Architect — TAA horserace: Robust Asset Allocation vs Dual Momentum](https://alphaarchitect.com/asset-allocation-horserace-robust-asset-allocation-raa-vs-dual-momentum/)
- [QuantPedia — Active Dual Momentum GTAA Strategy](https://quantpedia.com/active-dual-momentum-gtaa-strategy/)

**Evidência brasileira**
- [UNIFESP — Análise da teoria do momentum: portfólio de ações do mercado brasileiro (2000–2023)](https://repositorio.unifesp.br/items/a407f24d-3f99-447a-8bec-87be304d6d07)
- [UFPE — Anomalias de mercado: a estratégia de impulso](https://repositorio.ufpe.br/bitstream/123456789/1193/1/arquivo2698_1.pdf)
- [UFU — Backtesting do efeito momentum em portfólios](https://repositorio.ufu.br/bitstream/123456789/35341/1/BacktestingDoEfeito.pdf)
