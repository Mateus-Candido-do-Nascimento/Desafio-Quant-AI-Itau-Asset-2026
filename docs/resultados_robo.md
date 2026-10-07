# Resultados — Robô Fundamento

> Números gerados por `python src/robo/rodar.py`. Período **jan/2015 a jul/2026**
> (139 meses), líquido de custo, point-in-time. Metodologia em
> [[metodologia_robo]].

---

## 1. Resultado principal

Cinco classes, todas investíveis por ETF na B3 desde 2015.

| Estratégia | Retorno a.a. | Vol | **Acima do CDI** | Sharpe¹ | Máx. queda | t |
|---|---|---|---|---|---|---|
| **Robô Fundamento (ranking)** | **15,7%** | 10,8% | **+5,3%** | **0,53** | **−11%** | 1,80 |
| Rebalanceamento puro (peso igual) | 14,1% | 7,6% | +3,8% | 0,51 | −9% | 1,75 |
| Tático (filtro de tendência) | 13,3% | 7,4% | +3,1% | 0,44 | −7% | 1,51 |
| Carteira balanceada 60/40 | 11,2% | 8,6% | +1,2% | 0,18 | −15% | 0,60 |
| Ibovespa (100% ações) | 11,6% | 21,5% | +1,5% | 0,18 | **−37%** | 0,61 |
| CDI (a régua) | 9,9% | 1,1% | — | — | 0% | — |

¹ Sharpe sobre o **excedente ao CDI** — a única forma honesta de medir no Brasil.

**As duas leituras que importam:**

- **Contra o CDI:** o robô entrega **+5,3% ao ano** acima de dinheiro parado
  (p = 0,077 — marginal; ver §6 e [[busca_significancia]]).
- **Contra a bolsa:** 15,7% contra 11,6% do Ibovespa, com **um terço do tombo**
  (−11% vs −37%). Participa da alta sem passar pelo susto.

> **Nota de escopo — por que cripto não está aqui.** Testamos incluir bitcoin
> (teto 10%): o resultado saltaria para +8,5% e p = 0,004. **Deixamos de fora da
> estratégia principal por decisão metodológica**, e reportamos como extensão em
> §4c. O motivo, em uma frase: ETFs de bitcoin na B3 só existem desde 2021, e no
> subperíodo investível o ganho perde significância (p = 0,50). Aplicamos à
> cripto o mesmo critério que usamos para rejeitar o vol-targeting e o risk
> parity — se só funciona num recorte, não vira estratégia principal.

---

## 2. A camada de ranking agrega? (ablation)

Comparação limpa entre as versões, para isolar o valor de cada camada:

| Versão | Acima do CDI | Sharpe |
|---|---|---|
| Só rebalancear (pesos iguais fixos) | +3,4% | 0,47 |
| Rebalancear + filtro de tendência | +2,5% | 0,37 |
| **Rebalancear + ranking por mérito** | **+5,1%** | **0,52** |

**Conclusão honesta:** o rebalanceamento periódico sozinho **já entrega a maior
parte do valor** (+3,4%). A camada de ranking adiciona **+1,7 p.p.** — real, mas
incremental. O filtro de tendência puro, isolado, **piorou** o resultado (é
defensivo demais: protege o drawdown mas custa retorno).

Isso é informação, não fracasso: mostra que **a estrutura (rebalancear entre
classes) importa mais que a esperteza do sinal** — exatamente o tipo de achado
que vale reportar.

---

## 3. Validação fora da amostra (2020 em diante)

O teste mais importante: o robô continua funcionando em dados que não usamos
para desenhar a estratégia?

| Estratégia | Retorno a.a. | Acima do CDI | Sharpe | Máx. queda |
|---|---|---|---|---|
| **Robô Fundamento** | **14,9%** | **+4,5%** | **0,53** | −9% |
| Rebalanceamento puro | 12,6% | +2,4% | 0,38 | −9% |
| Balanceada 60/40 | 9,3% | −0,6% | −0,02 | −15% |
| Ibovespa | 6,7% | −3,0% | −0,02 | −36% |

**Aguentou.** O Sharpe fora da amostra (0,53) é até levemente melhor que o do
período completo (0,52), e a vantagem sobre o rebalanceamento puro **aumentou**.
No mesmo período, o Ibovespa e a carteira 60/40 **perderam para o CDI**.

---

## 4. Robustez (o resultado depende de escolhas nossas?)

**Frequência do rebalanceamento**

| Frequência | Acima do CDI | Sharpe | Máx. queda |
|---|---|---|---|
| Mensal | +5,1% | 0,52 | −11% |
| Trimestral | +4,3% | 0,45 | −13% |
| Semestral | +3,7% | 0,39 | −13% |

→ **Todas positivas e próximas.** Mensal é o melhor, mas o resultado não depende
disso: mesmo rebalanceando duas vezes por ano o robô entrega +3,7% sobre o CDI.
Rebalancear com mais frequência captura melhor as viradas de regime.

**Concentração do ranking**

| Pesos | Acima do CDI | Sharpe | Máx. queda |
|---|---|---|---|
| 50/30/20 | +5,5% | 0,49 | −14% |
| 40/35/25 (suave) | +5,2% | 0,49 | −13% |
| 60/25/15 (agressivo) | +5,9% | 0,49 | −14% |
| 100/0/0 (só a melhor) | +7,0% | 0,45 | **−19%** |

→ O retorno sobe com a concentração, mas o **Sharpe cai e o tombo aumenta**.
Diversificar entre as aprovadas é a escolha certa — não é o que rende mais, é o
que rende melhor por unidade de risco.

**Custo de transação**

| Custo | Acima do CDI | Sharpe |
|---|---|---|
| 5 bps | +5,2% | 0,53 |
| 10 bps (nosso) | +5,1% | 0,52 |
| 25 bps | +4,6% | 0,47 |

→ **Sobrevive a custos 2,5× maiores.** O giro médio é 27% ao mês, e o custo
total no período foi 3,7% — o resultado não depende de execução barata.

---

## 4c. As duas correções que mudaram o resultado — e suas ressalvas

### (i) Correção de dado: dividendos do S&P

Usávamos `^GSPC` (índice de **preço**), que ignora dividendos. Quem compra
IVVB11 recebe os dividendos reinvestidos. Trocamos por `^SP500TR` (**total
return**): a classe global passa de 12,7% para **14,8% a.a. em dólar** — eram
**~2 p.p. ao ano** que estávamos jogando fora.

Não é otimização, é **corrigir um erro**. Impacto isolado: Sharpe 0,52 → 0,53,
e melhora em 4 de 5 subperíodos.

### (ii) Extensão testada e NÃO adotada: cripto

Testamos adicionar quatro classes (small caps, títulos americanos, imobiliário
americano, cripto). Só **cripto** passou nos testes de sanidade estatísticos:

| Classe candidata | Sharpe | Melhora em subperíodos | Decisão |
|---|---|---|---|
| Small caps (SMAL11) | 0,36 | 2/5 | ❌ |
| Títulos EUA (IEF) | 0,48 | 0/5 | ❌ |
| Imobiliário EUA (VNQ) | 0,50 | 3/5 | ❌ |
| **Cripto (BTC), teto 10%** | **0,85** | **4/5** | ✅ |

**Por que com teto:** sem limite, o ranking chegaria a alocar 40% num ativo de
~70% de volatilidade — irreal para um multiativos. Com 10% capturamos a
assimetria sem descaracterizar a carteira (o drawdown vai de −11% para apenas
−12%). O teto vale para **todas** as estratégias, inclusive os benchmarks, para
a comparação ser justa.

| Teto em cripto | Acima do CDI | Sharpe | Máx. queda | p |
|---|---|---|---|---|
| sem cripto | +5,3% | 0,53 | −11% | 0,075 |
| 5% | +5,4% | 0,68 | −10% | 0,022 |
| **10% (adotado)** | **+8,4%** | **0,85** | −12% | **0,0044** |
| 15% | +11,5% | 0,93 | −13% | 0,0020 |
| sem teto (40%) | +25,6% | 0,98 | −23% | 0,0011 |

### ⚠️ Por que rejeitamos a cripto como estratégia principal

Apesar de passar nos testes estatísticos, **três problemas de método a
desqualificam** como estratégia principal:

1. **Investibilidade.** ETFs de bitcoin na B3 (HASH11, QBTC11) existem desde
   **2021**. Um backtest desde 2015 alocaria numa classe que o investidor
   brasileiro não conseguia comprar por veículo regulado — o mesmo tipo de
   premissa frouxa que nos fez começar o backtest em 2015 (por causa do IVVB11),
   e não em 2010.
2. **No subperíodo investível, o resultado não se sustenta:** de 2021 em diante o
   ganho cai para **+2,3% com p = 0,50**. Ou seja, **a significância vem
   inteiramente do período em que a classe não era acessível.**
3. **Viés de sobrevivência de classe.** Hoje sabemos que o BTC rendeu ~63% a.a.
   Em 2015, alocar em cripto era decisão radical, não sistemática. Incluí-la
   ex-post é o equivalente, no nível de classe, ao viés de sobrevivência que a
   masterclass do Itaú alerta no nível de ação.

**Coerência metodológica.** Rejeitamos o vol-targeting porque era alavancagem
disfarçada, e o risk parity porque só funcionava num recorte. A cripto tem
**exatamente o mesmo defeito do risk parity, em grau mais forte**. Adotá-la
porque o resultado é bonito, tendo rejeitado as outras por menos, seria
incoerente — e um avaliador experiente identificaria isso em segundos.

**O que fica registrado como extensão** (rodável com `INCLUIR_CRIPTO = True` em
`config.py`): com teto de 10%, o robô entregaria +8,5% sobre o CDI, Sharpe 0,86,
tombo de −12% e p = 0,004; o robô ficaria fora da cripto em 40 dos 139 meses; e
comprar-e-segurar BTC daria Sharpe parecido (0,92) com **−75% de tombo** contra
−12% do robô — o que ilustra bem o valor do mecanismo. É um resultado promissor
**a validar quando houver histórico suficiente de ETF na B3**, não hoje.

---

## 4b. Testes de reforço (as fragilidades que faltavam atacar)

### A janela de momentum é escolha a dedo?

O parâmetro mais perigoso do modelo: por que 12 meses? Testamos todas:

| Janela | Acima do CDI | Sharpe | Máx. queda |
|---|---|---|---|
| 6 meses | +4,2% | 0,41 | −20% |
| 9 meses | **+5,5%** | **0,53** | −12% |
| **12 meses (nossa)** | +5,1% | 0,52 | **−11%** |
| 18 meses | +3,9% | 0,41 | −12% |
| 24 meses | +2,5% | 0,27 | −20% |

→ **Todas positivas.** E a nossa escolha (12m) **não é nem a melhor** — 9 meses
renderia mais. Isso é a evidência mais forte contra a acusação de *data
snooping*: não garimpamos o parâmetro que melhor se ajusta ao passado.

### Significância por bootstrap

O teste t assume normalidade, que retorno mensal não tem. Refizemos com
**bootstrap (10.000 reamostragens)**:

- Excedente médio ao CDI: **+5,5% a.a.**
- Intervalo de confiança 95%: **[−0,6% ; +11,6%]**
- P(excedente ≤ 0) = **0,040**

**Leitura honesta:** o bootstrap dá 4,0% **unicaudal**, que é consistente com o
teste t (p = 0,082 **bicaudal** ≈ 0,041 unicaudal). Os dois métodos **concordam**
— não é que um "salve" o outro. A afirmação defensável é: *significativo a 5% em
teste unicaudal, marginal (10%) em bicaudal, e o IC de 95% ainda toca o zero.*

### Funciona em regimes diferentes?

| Período | Robô (vs CDI) | Ibovespa (vs CDI) |
|---|---|---|
| 2015–2017 (recessão/recuperação) | **+5,0%** | +2,5% |
| 2018–2019 (juro caindo) | +7,1% | +16,1% |
| 2020–2021 (pandemia) | **+15,8%** | −8,3% |
| **2022–2023 (juro alto)** | **−7,2%** ⚠️ | +0,4% |
| 2024–2026 (recente) | **+5,8%** | −1,3% |

→ **Positivo em 4 dos 5 subperíodos**, e brilha justamente na crise (2020–21:
+15,8% enquanto a bolsa fazia −8,3%). **Mas perdeu feio em 2022–2023.**

**Por que 2022–23 falhou (e isso precisa estar no relatório):** foi um ponto de
virada com Selic a 13,75%. O momentum é um sinal *atrasado* — ele reagiu tarde à
mudança de regime e tomou "chicotadas" (*whipsaw*), entrando em classes que já
tinham virado. É a fraqueza conhecida do método, e ela apareceu.

### E se tirarmos a classe que mais rendeu?

| Cardápio | Acima do CDI | Sharpe | Máx. queda |
|---|---|---|---|
| **Completo (5 classes)** | **+5,1%** | 0,52 | −11% |
| Sem dólar | +5,6% | **0,64** | −9% |
| Sem ações Brasil | +6,3% | **0,60** | −12% |
| Sem ouro | +3,3% | 0,42 | −8% |
| Sem bolsa global | +2,0% | 0,27 | −11% |

→ **Sobrevive à remoção de qualquer classe** — o resultado não vem de uma aposta
única. A bolsa global é a que mais contribui (sem ela o excedente cai à metade).

> ⚠️ **Achado incômodo, registrado com honestidade:** o robô fica **melhor sem
> ações Brasil e sem dólar** (Sharpe 0,60 e 0,64 contra 0,52). Faz sentido — foram
> as duas classes que menos entregaram no período (Ibovespa +1,5% sobre o CDI com
> −37% de tombo; dólar −3,9%). **Mas não vamos removê-las:** essa seria uma
> decisão de retrovisor (*hindsight*), exatamente o viés que o método combate. Em
> jan/2015 não havia como saber. Manter as duas é o teste mais duro — e o robô
> passa mesmo assim. Fica como hipótese para investigar com disciplina
> out-of-sample, não como ajuste do modelo.

### A pergunta desconfortável: "por que não comprar só o S&P e segurar?"

| Alternativa | Retorno | Acima do CDI | Sharpe | Máx. queda |
|---|---|---|---|---|
| **Robô Fundamento** | 15,5% | +5,1% | **0,52** | **−11%** |
| Buy & hold só global | 18,2% | **+7,6%** | 0,49 | −27% |
| Buy & hold só ouro | 17,6% | +7,0% | 0,47 | −24% |
| 50% CDI + 50% global | 14,5% | +4,1% | 0,49 | −12% |

**Resposta honesta, em três partes:**
1. **Comprar e segurar a bolsa global rendeu mais** (+7,6% vs +5,1%). Não vamos
   esconder isso.
2. **Mas com risco muito maior:** −27% de tombo contra −11% do robô, e Sharpe
   levemente pior (0,49 vs 0,52). Por unidade de risco, o robô ganha.
3. **E, decisivo:** "comprar S&P" só é a resposta *olhando para trás*. Em
   jan/2015 ninguém sabia que a bolsa global seria a campeã da década — poderia
   ter sido o Ibovespa (que decepcionou) ou o ouro. **O robô não precisa
   adivinhar o vencedor: ele descobre mês a mês.** É isso que se compra com o
   retorno a menos.

---

## 5. O que o robô realmente fez

**Alocação média (2015–2026):**

| CDI | Global | Ouro | Ações BR | Dólar |
|---|---|---|---|---|
| 32,2% | 21,4% | 19,6% | 17,0% | 9,9% |

Ou seja: **não é um robô "comprado em bolsa global"** disfarçado. Ele girou
genuinamente entre as classes, com um terço do tempo em caixa.

**A defesa funcionou:** em **17 dos 139 meses o robô ficou 100% em CDI** —
inclusive em meados de 2022, quando todas as classes de risco viraram. Foi assim
que ele limitou o tombo a −11% enquanto o Ibovespa levava −37%.

**Exemplos de alocação:**
- **Mar/2020 (pandemia):** 40% ouro, 30% global, 20% dólar, 10% ações — fugiu para os defensivos.
- **Jun/2022 (bear market):** 100% CDI — saiu de tudo.
- **Jul/2026:** 40% ações BR, 30% ouro, 30% CDI — voltou para o Brasil.

---

## 6. Significância estatística

- Excedente ao CDI: **+5,1% a.a.**, batendo o CDI em 48% dos meses.
- Teste t: **t = 1,75, p = 0,082** (bicaudal).
- Bootstrap (10.000 reamostragens): **P(excedente ≤ 0) = 0,040**; IC 95%
  **[−0,6% ; +11,6%]**.

**Leitura honesta:** os dois testes concordam — **significativo a 5% em teste
unicaudal, marginal (10%) em bicaudal**, e o intervalo de confiança de 95% ainda
toca o zero. Com 139 meses, não dá para cravar com folga que o ganho não é sorte.

O que sustenta a confiança é o **conjunto de evidências**, não um p-valor isolado:

| Evidência | Resultado |
|---|---|
| Fora da amostra (2020+) | mantém (+4,5%, Sharpe 0,53) |
| Todas as janelas de momentum (6–24m) | positivas |
| Todas as frequências (mensal–semestral) | positivas |
| Custo 2,5× maior | sobrevive |
| Remoção de qualquer classe | sobrevive |
| Subperíodos | positivo em 4 de 5 |
| Mecanismo econômico | compreensível e documentado na literatura |

Não vamos vender p = 0,082 como se fosse p < 0,05.

---

## 7. Conclusão

**O que está validado:**
1. Rebalancear periodicamente entre classes **bate o CDI e o Ibovespa** com
   fração do risco.
2. O ranking por mérito **agrega** sobre o rebalanceamento puro (+1,7 p.p.).
3. O resultado **aguenta fora da amostra**, mudanças de parâmetro e custos.

**O que não está:**
1. Significância a 5% (ficou em 8%).
2. A camada de IA lendo atas do Copom — ainda não construída nem testada.
3. Independência do período: a bolsa global rendeu excepcionalmente bem, e o
   robô se beneficiou de ter essa classe disponível.

**Próximos passos:**
1. Construir e testar a leitura das atas do Copom por LLM (a camada criativa).
2. Ampliar o cardápio de classes (inflação/IMA-B, small caps, cripto).
3. Testar o robô com aporte mensal (mais realista para o investidor final).
