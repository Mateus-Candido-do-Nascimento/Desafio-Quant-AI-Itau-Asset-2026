# Resultado da PoC — Event Study sobre o Itaú (ITUB4)

> Documento de resultado: cada fórmula da metodologia **aplicada ao Itaú com
> números reais**, o resultado, e as limitações honestas. Gerado por
> `src/event_study.py` sobre os 15 eventos de 2022+. Para a teoria abstrata, ver
> [[metodologia_event_study]].

---

## TL;DR — a pergunta e a resposta

**Pergunta da PoC:** a divulgação do ranking de reclamações do BC move o preço do
Itaú?

**Resposta: sim, há reação negativa, concentrada no dia da divulgação + o dia
seguinte (janela [0,+1]).** O retorno anormal acumulado médio é **−0,57%**,
marginal no teste paramétrico (t = −2,09, p = 0,056) mas **robusto no teste não-
paramétrico: 12 dos 15 eventos tiveram CAR negativo (sign test p = 0,035)**.

Isso valida o pré-requisito da tese: o sinal move o preço. Ainda **não** testa a
parte central (severidade do LLM vs. volume) — isso exige o universo completo.

---

## 1. O que entrou

| Insumo | Valor |
|---|---|
| Ativo | ITUB4 (fechamento ajustado, yfinance) |
| Mercado ($R_m$) | Ibovespa (`^BVSP`) |
| Eventos | 15 divulgações, 2022 Q1 → 2025 Q4 (datas oficiais do BC) |
| Janela de estimação | 120 pregões, de −130 a −11 |
| Janela do evento | de −5 a +5 pregões |

---

## 2. Cada fórmula, aplicada (exemplo: evento 2024 Q3, dia 0 = 24/out/2024)

### 2.1 Retorno simples
$$R_t = \frac{P_t}{P_{t-1}} - 1$$
Onde $P_t$ é o fechamento ajustado. Calculamos para o Itaú ($R_{i,t}$) e para o
Ibovespa ($R_{m,t}$), alinhados nos pregões comuns.

### 2.2 Modelo de mercado (estimar o "normal")
$$R_{i,t} = \alpha_i + \beta_i R_{m,t} + \varepsilon_{i,t}$$
Estimado por OLS **só na janela de estimação** (120 pregões antes do evento).
Para este evento:
$$\hat\alpha = 0{,}00074 \qquad \hat\beta = 0{,}8520$$
Leitura: fora do evento, o Itaú andava com $\beta \approx 0{,}85$ do Ibovespa
(quando o índice sobe 1%, o Itaú tende a subir 0,85%) mais um drift diário de
0,074%.

### 2.3 Retorno anormal (AR) — a "surpresa"
$$AR_{i,t} = R_{i,t} - (\hat\alpha_i + \hat\beta_i R_{m,t})$$

| Dia | $R_{Itaú}$ | $R_{Ibov}$ | Esperado $=\hat\alpha+\hat\beta R_m$ | **AR** |
|---|---|---|---|---|
| 0 (24/out) | +0,9045% | +0,6453% | +0,6243% | **+0,2802%** |
| +1 (25/out) | −1,1205% | −0,1338% | −0,0395% | **−1,0809%** |

No dia 0 o Itaú subiu, mas **menos do que o esperado** dado o mercado — AR quase
neutro. No dia +1 o Itaú caiu 1,12% enquanto o mercado mal se moveu: o esperado
era ~0, então quase toda a queda é **anormal** (−1,08%). A reação veio no dia
seguinte.

### 2.4 Retorno anormal acumulado (CAR)
$$CAR_i(t_1,t_2) = \sum_{t=t_1}^{t_2} AR_{i,t}$$
Para a janela [0,+1] deste evento:
$$CAR(0,1) = (+0{,}2802\%) + (-1{,}0809\%) = \mathbf{-0{,}8008\%}$$
Esse é o "tamanho do efeito" do evento sobre o Itaú: −0,80% de retorno que o
mercado não explica, na divulgação + dia seguinte.

### 2.5 Agregação entre eventos (CAAR)
Para falar do efeito *típico*, mediamos o AR de cada dia relativo entre os 15
eventos e acumulamos:
$$\overline{AR}_d = \frac{1}{15}\sum_{e=1}^{15} AR_{e,d}
\qquad CAAR = \sum_d \overline{AR}_d$$

```
 dia   AR médio    CAAR
 -5    +0,159%   +0,159%
 -2    +0,141%   +0,602%   ← leve drift de alta ANTES do evento
 -1    -0,022%   +0,580%
  0    -0,143%   +0,438%   ← dia da divulgação
 +1    -0,427%   +0,011%   ← maior queda anormal
 +2    -0,263%   -0,252%   ← fundo
 +5    +0,037%   +0,151%
```
O desenho é nítido: o Itaú vinha em leve alta, e a partir do dia 0 sofre quedas
anormais nos dias 0, +1 e +2, zerando o ganho acumulado. A reação é **negativa e
concentrada logo após a divulgação**.

### 2.6 Testes de significância (H0: o efeito é zero)

**Paramétrico** — t de uma amostra sobre os 15 CARs:
$$t = \frac{\overline{CAR}}{s_{CAR}/\sqrt{n}}, \quad n=15,\ \text{gl}=14$$

**Não-paramétrico** — sign test: quantos dos 15 eventos têm CAR negativo? Sob
H0, ~50%. Não assume normalidade — importante com $n$ pequeno.

---

## 3. Resultado consolidado (15 eventos)

| Janela | CAR médio | t | p(t) | neg/n | p(sinal) |
|---|---|---|---|---|---|
| CAR(0,0) | −0,142% | −0,91 | 0,376 | 9/15 | 0,607 |
| **CAR(0,1)** | **−0,569%** | **−2,09** | **0,056** | **12/15** | **0,035** |
| CAR(−1,1) | −0,592% | −1,96 | 0,071 | 10/15 | 0,302 |
| CAR(−5,5) | +0,151% | +0,21 | 0,836 | 7/15 | 1,000 |

$\hat\beta$ médio = 0,98 · $\hat\alpha$ médio = 0,00057.

**Leitura:**
- A janela **[0,+1]** é a que reage. Faz sentido: o BC divulga às ~14h30–15h
  (mercado aberto, fecha ~17h), então parte da reação cabe no dia 0 e o resto
  transborda pro dia +1.
- O t (p = 0,056) é **marginal** — esperado com $n=15$. Mas o **sign test (p =
  0,035) é mais forte**: 12 de 15 eventos negativos é difícil de explicar por
  acaso. Os dois testes apontando na mesma direção dão confiança.
- A janela larga [−5,+5] **não** é significativa: o efeito é de curto prazo e se
  dilui se a janela for grande demais.

---

## 4. Limitações honestas (entram no relatório)

1. **$n = 15$ eventos.** Amostra pequena (consequência de restringir a 2022+ por
   datas exatas). O paramétrico fica frágil; por isso reportamos o não-
   paramétrico junto. Não vendemos o t = −2,09 como "5%".
2. **Quatro janelas testadas.** Testar várias janelas infla o risco de falso
   positivo. A [0,+1] é a janela *a priori* natural (hora da divulgação), não
   garimpada — mas registramos a ressalva.
3. **Itaú é peça grande do Ibovespa.** $\beta \approx 0{,}98$, e o Itaú compõe o
   próprio índice — o modelo de mercado tem correlação parcialmente mecânica. O
   AR (resíduo) ainda é válido, mas idealmente usaríamos um índice ex-Itaú.
4. **Um banco só.** Isto é o Itaú. Não generaliza para o setor nem testa a tese
   central. É a prova de que o *método funciona* e de que *há reação*.
5. **Direção, não causa.** Medimos reação à divulgação. Ainda não ligamos o
   tamanho/sinal do CAR à **gravidade** das irregularidades (a tese). Próximo passo.

---

## 5. Próximos passos

1. **Rodar o universo todo** (8 bancos com F1 sólida) — `event_study.py` já é
   genérico (`python src/event_study.py BBDC4`).
2. **Ablation (a tese):** ordenar os bancos de cada evento por (a) índice cru e
   (b) severidade do LLM, e ver qual ordena melhor o CAR. Exige as features F4/F5
   do LLM, ainda não construídas.
3. **Controle de earnings (risco nº1):** medir a distância de cada evento ao
   balanço do banco; eventos sobrepostos vão para robustez.
4. **Snap de feriado:** o dia 0 já cai no 1º pregão ≥ data oficial; validar que
   nenhum evento caiu em feriado deslocando a janela.
