# Pré-relatório — Robô Fundamento

> Respostas para o formulário do pré-relatório (entrega 31/07/2026) + o
> detalhamento por trás de cada uma. Metodologia: [[metodologia_robo]].
> Resultados: [[resultados_robo]].

---

## Formulário — respostas para colar

**9. Nome do Robô**
> Fundamento

**10. Explicação do Nome**
> O robô ajusta a alocação entre classes de ativo com base nos fundamentos do
> cenário — quais classes estão de fato entregando retorno acima do custo de
> oportunidade (o CDI). O nome reflete que cada decisão de alocação tem um
> fundamento por trás: o robô não segue palpite, segue evidência.

**11. Lógica da Estratégia**
> Estratégia sistemática de alocação entre classes de ativo (renda fixa, ações
> Brasil, bolsa global, ouro e dólar), com rebalanceamento mensal. A cada mês o
> robô ordena as classes pelo retorno dos últimos 12 meses e aplica duas travas:
> (i) uma classe de risco só entra se estiver rendendo mais que o CDI — se
> nenhuma estiver, a carteira vai 100% para renda fixa; (ii) entre as aprovadas,
> a melhor recebe maior peso (40/30/20/10%). O rebalanceamento periódico traz a
> carteira de volta a esses pesos, controlando o risco. Todo o processo é
> point-in-time e considera custos de transação.

**12. Classe de Ativos**
> Multiclasse: renda fixa pós-fixada (CDI), renda variável Brasil (Ibovespa),
> renda variável internacional (S&P 500 em reais), ouro e câmbio (dólar).

**13. Universo de Investimento**
> Índices representativos de cada classe, todos investíveis por ETF na B3 no
> período testado: CDI/Tesouro Selic (renda fixa), BOVA11 (Ibovespa), IVVB11
> (S&P 500 em reais), ouro e dólar. O backtest começa em 2015 porque o IVVB11 —
> a forma prática de comprar bolsa global na B3 — existe desde nov/2014.

**14. Frequência da Estratégia**
> Mensal (revisão da alocação e rebalanceamento mensais).

**15. Benchmark**
> CDI como benchmark principal (retorno absoluto no Brasil) e Ibovespa como
> comparação com a bolsa.

---

## Detalhamento (para o relatório final)

### Conceito — a tese

> **No Brasil, dinheiro parado rende ~10% ao ano sem risco. Isso muda tudo:
> correr risco só faz sentido quando o risco está pagando. O robô mede isso
> todo mês e realoca — e quando nada está pagando, ele simplesmente não corre
> risco.**

Por que não é óbvio: no período testado o **Ibovespa rendeu 11,6% a.a. contra
9,9% do CDI** — ou seja, a bolsa mal superou o dinheiro parado, com −37% de
tombo no caminho. A carteira balanceada clássica 60/40 **perdeu** para o CDI a
partir de 2020. Bater o CDI de forma consistente é um problema real, não trivial.

### Modelagem — o ciclo mensal

1. Calcula o momentum de 12 meses de cada classe (só com dados até o mês anterior).
2. **Trava de segurança:** descarta as classes que rendem menos que o CDI.
3. **Ranking:** entre as aprovadas, distribui 40/30/20/10%; o resto vai para o CDI.
4. **Rebalanceia** a carteira para esses pesos, pagando o custo do giro.
5. Deixa a carteira derivar e repete no mês seguinte.

### Backtest — rigor

| Armadilha (masterclass) | Como tratamos |
|---|---|
| Olhar o futuro | todo sinal com `shift(1)`: decisão de $t$ usa dados até $t-1$ |
| Custos | 10 bps por unidade de giro, descontados |
| Viés de sobrevivência | usamos **índices**, não ações — nenhuma empresa "some" da amostra |

Motor de backtest **implementado por nós** (`src/robo/backtest.py`), sem
plataforma pronta. Validação fora da amostra (2020+) e testes de robustez
(frequência, concentração, custo).

### Resultados (jan/2015 – jul/2026, 139 meses, líquido de custo)

| Estratégia | Retorno a.a. | Acima do CDI | Sharpe | Máx. queda |
|---|---|---|---|---|
| **Robô Fundamento** | **15,7%** | **+5,3%** | **0,53** | **−11%** |
| Rebalanceamento puro | 14,1% | +3,8% | 0,51 | −9% |
| Ibovespa | 11,6% | +1,5% | 0,18 | −37% |
| CDI (régua) | 9,9% | — | — | 0% |

- **Fora da amostra (2020+):** +5,1% sobre o CDI, Sharpe 0,59 — a vantagem se
  manteve (acima do in-sample), enquanto Ibovespa e 60/40 perderam para o CDI.
- **Robustez:** positivo em **todas** as janelas de momentum testadas (6 a 24
  meses), em qualquer frequência (mensal +5,1% … semestral +3,7%), com custos
  2,5× maiores, e mesmo removendo qualquer classe do cardápio. A janela que
  usamos (12m) **não é a melhor** do conjunto — evidência contra data snooping.
- **Significância:** t = 1,80 (p = 0,077 bicaudal); bootstrap de 10.000
  reamostragens dá P(excedente ≤ 0) = 0,037. Ou seja: **significativo a 5%
  unicaudal, marginal a 10% bicaudal.** Não apresentamos como p < 0,05.
- **Subperíodos:** positivo em 4 de 5; brilha na crise (2020–21, enquanto
  a bolsa perdia), mas **perdeu em 2022–23** — o momentum tomou
  chicotada na virada de regime com Selic a 13,75%. Reportado como limitação.
- **O robô fugiu 100% para o CDI em 17 dos 139 meses** — foi assim que limitou o
  tombo a −11% enquanto a bolsa levava −37%.
- **Fundamentação:** a regra é a adaptação ao Brasil do *Dual Momentum*
  (Antonacci) e da alocação tática de Faber (2007) — método publicado e
  replicado, não invenção nossa. Detalhes em [[fundamentacao_robo]].

### O p-valor marginal — e por que não o "melhoramos"

Tentamos cruzar o corte de 5% com **8 variantes definidas a priori**. Duas
cruzaram — e **rejeitamos as duas**:

| Variante | p | Por que rejeitamos |
|---|---|---|
| Vol-targeting | 0,029 | **Alavancagem disfarçada**: exposição a risco 62%→70%, escala média 1,16×, e melhorou em só 3 de 6 subperíodos |
| Risk parity | 0,036 | Só ganha no recorte 2010+; **piora** no recorte principal (Sharpe 0,46 vs 0,52) |
| **Incluir cripto** (teto 10%) | **0,004** | ETF de bitcoin na B3 só desde **2021**; no subperíodo investível o ganho cai para +2,3% com **p = 0,50**. Toda a significância vem do período em que a classe não era acessível — é viés de sobrevivência no nível de **classe**. Fica como **extensão documentada**, não como estratégia. |

Além disso, com 8 testes a correção de Bonferroni leva o melhor p (0,029) a
**0,232** — nenhuma variante sobrevive.

**A matemática explica o limite:** para provar um Sharpe de 0,52 com 95% de
confiança seriam necessários $(1{,}96/0{,}52)^2 \approx 14{,}5$ anos. Temos 11,6.
**Faltam ~3 anos de dados, não uma estratégia melhor.**

> *"Preferimos reportar um resultado marginal robusto a um resultado
> significativo garimpado."* — detalhamento em [[busca_significancia]].

### Uso de IA generativa

1. **Construção** do código, do motor de backtest e dos testes de robustez.
2. **Análise crítica** dos resultados — foi no diálogo com a GenAI que
   identificamos os dois erros que mais mudaram o projeto: a régua correta é o
   CDI (não a bolsa), e o cardápio de classes original estava limitado demais.
3. **Documentação e relatório.**
4. **Extensão planejada:** LLM lendo as **atas do Copom** para classificar o
   regime de juros e inclinar a alocação — desenhada com disciplina
   point-in-time, ainda **não validada**.

### Conclusão e próximos passos

**Validado:** alocação com rebalanceamento periódico entre classes bate o CDI e
o Ibovespa com fração do risco; o ranking por mérito agrega +1,7 p.p. sobre o
rebalanceamento puro; o resultado aguenta fora da amostra e mudanças de parâmetro.

**Não validado:** significância a 5% (ficou em 8%); a camada de IA lendo Copom;
independência do período (a bolsa global rendeu excepcionalmente bem).

**Próximos passos:** construir e testar a leitura das atas do Copom por LLM;
ampliar o cardápio de classes (IMA-B, small caps); simular com aporte mensal.
