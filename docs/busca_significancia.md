# Busca por significância — o que tentamos e por que rejeitamos

> Documento de rigor metodológico. O excedente do robô sobre o CDI é **+5,1% a.a.
> com p = 0,082** — marginal. Este documento registra as tentativas de cruzar o
> corte de 5%, **por que rejeitamos as que "funcionaram"**, e a matemática que
> mostra que o limite é da amostra, não da estratégia.
> Resultados: [[resultados_robo]] · Metodologia: [[metodologia_robo]]

---

## 1. Por que este documento existe

A tentação natural, diante de p = 0,082, é testar variantes até uma dar p < 0,05
e apresentar essa. **Isso é exatamente o Erro Crítico 2 da masterclass do Itaú
(overfitting/superotimização)** — e é indetectável no slide, mas fatal no Q&A.

Optamos pelo caminho oposto: definimos as variantes **antes** de rodar, testamos
todas, **reportamos todas** e aplicamos os mesmos critérios de rejeição a cada
uma. O resultado é que **rejeitamos as duas variantes que cruzaram 5%.**

---

## 2. A matemática do poder estatístico

A estatística t de um excedente médio se aproxima de:

$$
t \;\approx\; \text{Sharpe} \times \sqrt{\text{anos}}
$$

Invertendo, os anos necessários para provar um Sharpe com 95% de confiança:

$$
\text{anos} = \left(\frac{1{,}96}{\text{Sharpe}}\right)^{2}
$$

| Sharpe da estratégia | Anos necessários para p < 0,05 |
|---|---|
| 0,30 | 43 anos |
| 0,50 | 15,4 anos |
| **0,52 (o nosso)** | **14,2 anos** |
| 0,75 | 6,8 anos |
| 1,00 | 3,8 anos |

**Temos 11,6 anos.** Faltam ~2,6 anos de dados — não uma estratégia melhor.

Isso não é uma fraqueza do nosso robô: é a natureza do dado financeiro. Um fundo
com Sharpe 0,5 (excelente para multiativos) **não consegue provar significância
em uma década**. Quem apresenta p < 0,01 num backtest de 10 anos geralmente está
com um Sharpe inflado por viés, alavancagem ou garimpo.

---

## 3. As variantes testadas (todas reportadas)

Oito combinações definidas *a priori*: dois recortes de período × quatro
desenhos. Todas com o mesmo motor, custos e disciplina point-in-time.

| Período | Variante | Anos | Acima do CDI | Sharpe | p (bicaudal) |
|---|---|---|---|---|---|
| 2015+ | base (janela 12m) | 11,6 | +5,1% | 0,52 | 0,082 |
| 2015+ | ensemble 6/9/12/18m | 11,6 | +4,8% | 0,50 | 0,094 |
| 2015+ | base + vol-target | 11,6 | +6,4% | 0,61 | **0,040** |
| 2015+ | ensemble + vol-target | 11,6 | +6,1% | 0,58 | **0,049** |
| 2010+ | base (janela 12m) | 15,5 | +4,5% | 0,49 | 0,056 |
| 2010+ | ensemble 6/9/12/18m | 15,5 | +4,2% | 0,47 | 0,067 |
| 2010+ | base + vol-target | 15,5 | +5,7% | 0,56 | **0,029** |
| 2010+ | ensemble + vol-target | 15,5 | +5,4% | 0,53 | **0,037** |

**Correção por múltiplos testes (Bonferroni):** com 8 testes, o menor p (0,029)
vira **0,232**. Nenhuma variante sobrevive à correção — primeiro sinal de alerta.

---

## 4. Por que rejeitamos o vol-targeting (que deu p = 0,029)

O vol-targeting escala a exposição para uma volatilidade-alvo constante. É
técnica documentada (Moreira & Muir, *Volatility-Managed Portfolios*, Journal of
Finance, 2017), e melhorou o Sharpe nos dois períodos. Parecia legítimo.

**Aplicamos dois testes de sanidade — e ele falhou nos dois:**

**(a) Consistência por subperíodo** — melhorou em apenas **3 de 6**:

| Período | Base | Vol-target | |
|---|---|---|---|
| 2011–2014 | 0,40 | 0,39 | pior |
| 2015–2017 | 0,42 | 0,60 | melhor |
| 2018–2019 | 0,65 | 0,63 | pior |
| 2020–2021 | 1,34 | 1,35 | melhor |
| 2022–2023 | −1,56 | −1,58 | pior |
| 2024–2026 | 0,68 | 0,87 | melhor |

**(b) O mecanismo** — o ganho não veio de gestão de risco, veio de **alavancagem**:

| Diagnóstico | Valor |
|---|---|
| Escala média aplicada | **1,16×** (acima de 1 = alavanca) |
| Meses no teto de 1,5× | 49 de 198 |
| Meses reduzindo risco (<1) | apenas 53 de 198 |
| Exposição média a risco | **62% → 70%** |

> **Veredito:** o "vol-targeting" estava, na prática, **aumentando a exposição em
> períodos calmos** — e o período testado foi favorável a risco. O Sharpe maior é
> beta disfarçado, não habilidade. **Rejeitado.**

---

## 5. Por que rejeitamos o risk parity (que deu p = 0,036)

Ponderar as classes aprovadas pelo inverso da volatilidade (mais peso ao que
oscila menos) é princípio sólido e **não** é alavancagem — a exposição a risco
até *caiu* (62% → 51%) e o drawdown melhorou (−11% → −9%).

**Mas o resultado depende do recorte escolhido:**

| Período | Pesos fixos (nosso) | Risk parity |
|---|---|---|
| **2015+** | **0,52** | 0,46 ← **pior** |
| **2010+** | 0,49 | **0,54** ← melhor (p = 0,036) |

Melhorou em 4 de 6 subperíodos, mas **piorou justamente no recorte principal**.

> **Veredito:** adotar o risk parity exigiria escolher o período em que ele ganha
> — que é cherry-picking de janela. **Rejeitado como mudança de modelo**, mantido
> como hipótese a testar com disciplina out-of-sample no futuro.

---

## 6. O que sobra: a alavanca legítima é tempo

A única melhora sem contrapartida metodológica foi **estender o histórico**
(2010+ em vez de 2015+): p vai de 0,082 para **0,056**, puramente por ter mais
observações — sem tocar na estratégia.

**Mas há uma ressalva de investibilidade:** antes de nov/2014 não existia o
IVVB11, o ETF que torna a bolsa global acessível na B3. A classe existia (via
fundos internacionais), mas era menos acessível ao investidor comum. Por isso
mantivemos **2015 como recorte principal** e reportamos 2010+ como robustez.

Preferimos o recorte mais conservador com p pior, a um p melhor com premissa
mais frouxa.

---

## 7. Conclusão

**Não é possível, com esta amostra e sem comprometer o método, cruzar p < 0,05.**

O que temos, e que sustentamos:

| Evidência | Status |
|---|---|
| Excedente ao CDI | +5,1% a.a. |
| Significância | p = 0,082 bicaudal (0,040 unicaudal / bootstrap) |
| Fora da amostra (2020+) | mantém: +4,5%, Sharpe 0,53 |
| Todas as janelas de momentum (6–24m) | positivas |
| Todas as frequências (mensal–semestral) | positivas |
| Custo 2,5× maior | sobrevive |
| Remoção de qualquer classe | sobrevive |
| Subperíodos | positivo em 4 de 5 |
| Variantes que cruzaram 5% | **rejeitadas por falharem os testes de sanidade** |

**A frase para a banca:**

> *"Nosso excedente sobre o CDI é +5,1% a.a. com p = 0,08. Testamos caminhos para
> cruzar 5% — vol-targeting e risk parity — e rejeitamos os dois: o primeiro era
> alavancagem disfarçada, o segundo só funcionava num recorte de período. A
> matemática do poder estatístico mostra que precisaríamos de ~14 anos para
> provar um Sharpe de 0,52, e temos 11,6. Preferimos reportar um resultado
> marginal robusto a um resultado significativo garimpado."*

O edital (Q22) diz explicitamente que resultado bem analisado não elimina. Um
resultado marginal com esta bateria de robustez é mais defensável — e mais raro —
que um p < 0,05 obtido por busca.
