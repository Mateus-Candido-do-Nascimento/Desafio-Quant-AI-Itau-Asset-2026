# Metodologia — Robô Fundamento

> Como o robô funciona, do dado cru até a carteira. Cada regra vem com o **porquê**
> em linguagem natural. Se você não consegue defender uma linha na banca, ela não
> deveria estar no modelo.
> Implementação: `src/robo/`. Resultados: [[resultados_robo]].

---

## 1. A ideia em uma frase

> **Todo mês o robô decide quanto colocar em cada tipo de investimento — renda
> fixa, ações Brasil, bolsa global, ouro e dólar — dando mais peso para o que
> está indo bem e fugindo para a renda fixa quando nada está.**

Não é escolher ações. É **alocação entre classes de ativo**, que é o que uma
gestora de verdade faz. O rebalanceamento periódico não é um detalhe: é o
mecanismo central — todo mês a carteira é refeita.

---

## 2. O universo: 5 classes, 5 papéis diferentes

| Classe | Representa | Papel na carteira | Investível via |
|---|---|---|---|
| **CDI** | renda fixa pós-fixada | o caixa, o porto seguro | Tesouro Selic, CDB |
| **Ações** | Ibovespa | crescimento Brasil | BOVA11 |
| **Global** | S&P 500 em reais | crescimento internacional | IVVB11 |
| **Ouro** | ouro em reais | proteção contra crise | ETF/fundo de ouro |
| **Dólar** | USD/BRL | proteção contra risco Brasil | fundo cambial |

**Por que o CDI é especial:** ele é ao mesmo tempo uma classe e o **destino da
fuga**. Quando nenhuma classe de risco está valendo a pena, o robô se recolhe
100% nele. No Brasil isso é poderoso — o dinheiro parado rende ~10% ao ano.

**Por que "Global" é essencial:** durante o período testado o Ibovespa rendeu
5,7% ao ano e **perdeu para o CDI**. Sem a bolsa internacional, o robô ficaria
preso a um cardápio ruim. Um investidor brasileiro real tem essa opção.

---

## 3. O sinal: como o robô decide o que está "bom"

Para cada classe, todo mês, o robô calcula o **momentum de 12 meses**:

$$
\text{momentum}_{c,t} = \frac{P_{c,\,t-1}}{P_{c,\,t-13}} - 1
$$

| Símbolo | Significado |
|---|---|
| $P_{c,t}$ | nível (preço/índice) da classe $c$ no mês $t$ |
| $t-1$ | o mês **anterior** — o robô nunca usa o mês que está alocando |

**Por que momentum:** classes de ativo tendem a manter tendência por alguns
meses (fenômeno documentado — Faber, 2007; Antonacci, *Dual Momentum*). É o
sinal mais simples e mais robusto que existe para esse tipo de decisão.

**Por que 12 meses:** janela longa o suficiente para ignorar ruído mensal e
curta o suficiente para reagir a mudanças de regime.

---

## 4. A regra de alocação: ranking com duas travas

Todo mês, no rebalanceamento, o robô:

**Passo 1 — trava de segurança (momentum absoluto).**
Uma classe de risco só entra na carteira se estiver rendendo **mais que o CDI**.
Se o CDI está ganhando de todas, o robô fica **100% em renda fixa**.
> *Por que:* impede que o robô compre "a melhor entre as ruins". No Brasil, com
> juro alto, ficar parado é uma decisão legítima e frequentemente a melhor.

**Passo 2 — ranking (momentum relativo).**
Entre as classes aprovadas, ordena da melhor para a pior e distribui:

| Posição | Peso |
|---|---|
| 1ª | 40% |
| 2ª | 30% |
| 3ª | 20% |
| 4ª | 10% |
| o que sobrar | CDI |

> *Por que pesos decrescentes e não "tudo na melhor":* concentrar demais aumenta
> o risco sem melhorar o retorno ajustado — testamos (§ robustez em
> [[resultados_robo]]). Diversificar entre as aprovadas é mais estável.

**Passo 3 — rebalanceamento.**
A carteira volta para esses pesos. Entre um rebalanceamento e outro ela
**deriva** (quem sobe passa a pesar mais); no mês seguinte o robô corrige.

---

## 5. O motor de backtest (implementado por nós)

O edital proíbe usar plataforma que entrega o backtest pronto. O nosso motor
(`src/robo/backtest.py`) simula mês a mês:

```
para cada mês t:
    1. lê os pesos-alvo (decididos com dados até t-1)
    2. se é mês de rebalanceamento:
           calcula o giro = |peso_novo - peso_atual|
           paga o custo do giro
           adota os pesos novos
    3. retorno do mês = soma(peso × retorno da classe) - custo
    4. deixa os pesos derivarem com o retorno
```

### As três regras de ouro (as armadilhas da masterclass)

| Armadilha | Como o robô evita |
|---|---|
| **Olhar o futuro** | todo sinal usa `shift(1)`: a decisão do mês $t$ só enxerga até $t-1$ |
| **Esquecer custos** | 10 bps sobre cada unidade de giro, descontados do retorno |
| **Viés de sobrevivência** | usamos **índices**, não ações individuais — não há empresa que "sumiu" da amostra |

---

## 6. Como medimos sucesso: a régua é o CDI

$$
\text{Sharpe} = \frac{\text{média}(r_{\text{robô}} - r_{\text{CDI}})}{\text{desvio}(r_{\text{robô}} - r_{\text{CDI}})}\times\sqrt{12}
$$

**Este é o ponto mais importante do projeto inteiro.** No Brasil, dinheiro parado
rende ~10% ao ano **sem risco nenhum**. Uma estratégia que rende 12% não é boa —
é 2% acima do que se ganharia sem fazer nada. Qualquer métrica que ignore o CDI
está inflada.

Também reportamos:
- **Máximo drawdown** — o pior tombo do pico ao vale (o susto do investidor).
- **Teste t** sobre o retorno excedente — o ganho sobre o CDI é real ou sorte?

**Benchmarks:** CDI (régua principal), Ibovespa (a bolsa) e uma carteira
balanceada 60/40 (o que um investidor tradicional faria).

---

## 7. Onde entra a IA generativa

O edital exige GenAI em **pelo menos uma etapa** — não precisa ser o modelo.
Nosso uso, em ordem de peso:

1. **Construção do código e do backtest** — implementação dos módulos, do motor
   de simulação e dos testes de robustez.
2. **Análise e visualização dos resultados** — leitura crítica das métricas,
   gráficos, identificação de fragilidades (foi a GenAI que apontou que a régua
   correta era o CDI, e que o universo original estava limitado demais).
3. **Estruturação da documentação e do relatório.**
4. **Extensão planejada (leitura macro):** um LLM lendo as **atas do Copom** para
   classificar o regime de juros e inclinar a alocação. Está desenhada com
   disciplina point-in-time (o modelo só lê a ata **depois** da data de
   publicação), mas **ainda não foi validada** — ver próximos passos.

---

## 8. Limitações honestas

1. **Significância marginal:** o ganho sobre o CDI tem p ≈ 0,08 — forte, mas não
   cruza o corte de 5%. Com 139 meses, é o que a amostra permite dizer.
2. **O período favoreceu a bolsa global:** o S&P 500 em reais rendeu 20% ao ano
   (bull market americano + real desvalorizado). Isso pode não se repetir, e o
   robô depende de ter boas classes no cardápio.
3. **Investibilidade:** o backtest começa em 2015 porque o IVVB11 (a forma
   prática de comprar bolsa global na B3) só existe desde nov/2014. Antes disso
   a classe existia, mas era menos acessível.
4. **Custos simplificados:** 10 bps por giro; não modelamos spread de ETF pouco
   líquido nem imposto.
5. **A camada de IA lendo Copom ainda não foi testada** — pode não agregar, e
   reportaremos assim se for o caso.
