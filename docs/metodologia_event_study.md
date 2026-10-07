# Metodologia — Event Study

> Documento base do relatório. Cada fórmula vem com legenda do que cada
> símbolo significa e **por que** ela está aqui. Se você não consegue
> defender uma linha na banca, ela não deveria estar no modelo.

---

## 0. A pergunta, antes da matemática

Nossa tese: **a natureza (gravidade) das irregularidades de um banco explica a
reação do preço da ação à divulgação do ranking do BC melhor que o volume cru
de reclamações.**

Antes de montar carteira (long-short), precisamos responder a pergunta
anterior: **o sinal move o preço?** O event study existe pra isso. Ele isola o
que aconteceu com a ação *por causa do evento*, separando do que aconteceria de
qualquer jeito por o mercado inteiro ter subido ou caído naquele dia.

A lógica em quatro passos:

```
retorno esperado  →  retorno anormal (AR)  →  retorno anormal acumulado (CAR)  →  teste de significância
   (o que era       (o que sobrou           (soma do efeito              (isso é sinal
    de se esperar)    de surpresa)            na janela do evento)         ou é acaso?)
```

As próximas seções destrincham cada seta.

---

## 1. Janelas: estimação vs. evento

Todo event study separa o tempo em duas janelas em torno do **dia 0** (a data
da divulgação do ranking).

```
   janela de estimação              janela do evento
 |───────────────────────|        |─────────●─────────|
 t = -130 ............ -11   ...   -5    0 (divulgação)   +5
        (≈120 pregões)         (gap)      ↑
                                       fechamento do dia da divulgação
```

| Símbolo | Significado |
|---|---|
| **dia 0** | data de divulgação do ranking. Regra do BC (lida do calendário real, validada em 2025): **4ª quinta-feira do mês seguinte ao fim do trimestre, às 15h**. Como é com mercado aberto (B3 fecha ~17h), o dia 0 "limpo" é o fechamento desse dia, que já incorpora ~2h de reação. |
| **janela de estimação** | ~120 pregões *antes* do evento (ex.: de −130 a −11). Serve só pra **aprender o comportamento normal** da ação. Não pode tocar o evento, senão contamina. |
| **gap** | os ~10 pregões entre o fim da estimação e o início da janela do evento. Evita que vazamento/antecipação do ranking suje a estimação. |
| **janela do evento** | poucos pregões em torno do dia 0 (ex.: −5 a +5, ou só 0 a +1). É onde medimos a reação. |

**Por que importa:** a janela de estimação define o que é "normal". A janela do
evento mede o "anormal". Se elas se sobrepuserem, o modelo aprende o próprio
evento como se fosse rotina — e o efeito desaparece artificialmente.

---

## 2. Retorno esperado: o modelo de mercado

Pra saber o que foi *anormal*, primeiro definimos o que seria *normal*. Usamos o
**modelo de mercado**: a ação tende a acompanhar o índice (Ibovespa), com uma
sensibilidade própria.

$$
R_{i,t} = \alpha_i + \beta_i \, R_{m,t} + \varepsilon_{i,t}
$$

| Símbolo | Significado |
|---|---|
| $R_{i,t}$ | retorno da ação $i$ no pregão $t$. |
| $R_{m,t}$ | retorno do mercado (Ibovespa) no mesmo pregão. |
| $\alpha_i$ | retorno médio da ação que **não** vem do mercado (parte própria). |
| $\beta_i$ | quanto a ação amplifica o mercado. $\beta=1.2$ → quando o Ibov sobe 1%, a ação tende a subir 1,2%. |
| $\varepsilon_{i,t}$ | erro: o pedaço do retorno que o mercado não explica. Em média zero. |

$\alpha_i$ e $\beta_i$ são estimados **só na janela de estimação**, por mínimos
quadrados (a mesma fórmula da regressão, ver `docs/` de fundamentos). Eles
capturam o comportamento normal da ação *antes* de o evento acontecer.

**Por que o modelo de mercado e não só o retorno bruto?** Se no dia do ranking o
Ibovespa caiu 3% por um motivo macro (Copom, EUA), a ação cairia junto sem ter
nada a ver com o ranking. O $\beta_i R_{m,t}$ desconta exatamente esse "arrasto
do mercado". O que sobrar é candidato a reação ao evento.

---

## 3. Retorno anormal (AR)

O retorno anormal é a **surpresa**: o que a ação fez de fato menos o que era de
se esperar pelo modelo de mercado.

$$
AR_{i,t} = R_{i,t} - \left( \hat\alpha_i + \hat\beta_i \, R_{m,t} \right)
$$

| Símbolo | Significado |
|---|---|
| $AR_{i,t}$ | retorno anormal da ação $i$ no pregão $t$ da janela do evento. |
| $\hat\alpha_i,\ \hat\beta_i$ | os coeficientes **estimados** na janela de estimação (o "chapéu" indica estimativa). |
| termo entre parênteses | o retorno **esperado** dado o mercado naquele dia. |

**Por que importa:** $AR_{i,t}$ é o coração do método. É o retorno "que não
deveria estar ali". Se o ranking não carrega informação nova, o $AR$ deveria ser
ruído em torno de zero. Se carrega, o $AR$ aparece concentrado em torno do dia 0.

---

## 4. Retorno anormal acumulado (CAR)

A reação a um evento raramente cabe num único pregão — vaza pro dia seguinte,
às vezes antecipa. Por isso **somamos** os $AR$ ao longo da janela do evento.

$$
CAR_i(t_1, t_2) = \sum_{t=t_1}^{t_2} AR_{i,t}
$$

| Símbolo | Significado |
|---|---|
| $CAR_i(t_1,t_2)$ | retorno anormal acumulado da ação $i$ entre os pregões $t_1$ e $t_2$. |
| $t_1, t_2$ | limites da janela do evento (ex.: $-1$ a $+1$, ou $0$ a $+5$). |

**Por que importa:** o $CAR$ é a **medida-resumo do efeito do evento** sobre uma
ação. É ele que vamos correlacionar com o sinal — é o número que a tese precisa
explicar.

> **O teste central da tese (ablation).** Ordenamos os bancos de cada evento de
> duas formas: (a) pelo **índice cru** do BC e (b) pela **severidade do LLM**.
> A pergunta é: qual das duas ordenações se alinha melhor com o $CAR$ observado?
> Se a severidade ordena melhor, a tese ganha sustentação. Se o índice cru
> ordena igual ou melhor, a tese cai — e reportamos isso (Q22 do edital permite).

---

## 5. Agregação entre bancos (CAAR)

Um único banco é anedota. Pra falar do *efeito do ranking em geral*, calculamos a
média dos $AR$ entre todos os bancos de um evento — e acumulamos.

$$
\overline{AR}_t = \frac{1}{N}\sum_{i=1}^{N} AR_{i,t}
\qquad
CAAR(t_1,t_2) = \sum_{t=t_1}^{t_2} \overline{AR}_t
$$

| Símbolo | Significado |
|---|---|
| $\overline{AR}_t$ | retorno anormal **médio** entre os $N$ bancos, no pregão $t$. |
| $N$ | número de bancos válidos no evento (point-in-time; ver `teste_viabilidade.py`). |
| $CAAR$ | *Cumulative Average Abnormal Return* — o efeito médio do evento sobre o setor. |

**Por que importa:** ao mediar entre bancos, o ruído idiossincrático de cada ação
tende a se cancelar, e o efeito comum do evento (se existir) sobrevive. É o
gráfico clássico de event study: o $CAAR$ no eixo y, os dias relativos no x.

---

## 6. Teste de significância: é sinal ou é acaso?

Achar $CAAR \neq 0$ não basta — pode ser sorte da amostra. Testamos a hipótese
nula de que **o evento não teve efeito** ($H_0: CAAR = 0$).

$$
t = \frac{CAAR(t_1,t_2)}{\widehat{\sigma}\big(CAAR(t_1,t_2)\big)}
$$

| Símbolo | Significado |
|---|---|
| $t$ | estatística de teste. Quanto maior em módulo, mais difícil o resultado ser acaso. |
| numerador | o efeito acumulado médio que medimos. |
| $\widehat\sigma(\cdot)$ | desvio-padrão do $CAAR$, estimado a partir da variância dos $AR$ na janela de estimação. |

Regra prática: $|t| > 1{,}96$ → significativo a 5% (o efeito provavelmente é
real). $|t| < 1{,}96$ → não rejeitamos a hipótese de que o ranking não move o
preço.

**Por que importa:** é a diferença entre "achamos um padrão" e "achamos um padrão
que provavelmente não é coincidência". Sem o teste, qualquer linha torta vira
narrativa. Com ele, o resultado é honesto — inclusive quando dá nulo.

> **Cuidado com $N$ pequeno.** Temos ~11 bancos por evento e **15 eventos**
> (escopo restrito a 2022+, onde as datas de divulgação são oficiais). Com
> amostra pequena, o teste-$t$ simples perde poder e fica sensível a outliers.
> Por isso vamos cruzar com testes não-paramétricos (ex.: teste de sinais) e
> reportar os dois. Ver [[riscos-n-pequeno]].

---

## 7. O confundidor que pode matar tudo: earnings

**Risco nº1 do projeto.** A divulgação do ranking pode cair perto do balanço
trimestral do banco. Se cair, o $CAR$ que atribuímos ao ranking pode ser, na
verdade, reação ao lucro divulgado dias antes/depois.

```
   balanço do banco        ranking do BC
        ●--------------------------●
        ←--- dias de distância ---→
                  ↑
        se for pequeno, os efeitos se misturam e o AR fica contaminado
```

Não dá pra ignorar. O **Teste 2** (`teste_viabilidade.py`) mede, pra cada par
banco×evento, a distância em dias até o balanço mais próximo. Eventos com
sobreposição entram numa análise de robustez separada (ou saem). A decisão de
corte vem *depois* de ver a distribuição das distâncias — não chutamos antes.

---

## 8. Resumo do pipeline

| Passo | Entrada | Saída | Seção |
|---|---|---|---|
| 1. Janelas | data do evento | índices de estimação e evento | §1 |
| 2. Estimar normal | retornos na estimação | $\hat\alpha_i, \hat\beta_i$ | §2 |
| 3. Anormal | retornos no evento | $AR_{i,t}$ | §3 |
| 4. Acumular | $AR_{i,t}$ | $CAR_i$ | §4 |
| 5. Agregar | $CAR_i$ de todos | $CAAR$ | §5 |
| 6. Testar | $CAAR$ + variância | estatística $t$, p-valor | §6 |
| 7. Ablation | $CAR_i$ + ranks | índice cru vs. severidade LLM | §4 |

Tudo implementado por nós (proibido delegar a plataforma pronta — regra do
edital). O backtest é o motor que roda esse pipeline em cada um dos 15 eventos
(2022+); ver resultado da PoC em [[resultado_poc_itau]].

---

## Referências de aula (curso IMPA, citadas no doc da equipe)

- Regressão linear / mínimos quadrados → estimação de $\alpha,\beta$ (Aula 2, Cap. 3).
- Seleção de variáveis / Lasso → quais das 5 features entram (Aula 7, Cap. 6).
- Reamostragem / validação → robustez do teste (Aula 5, Cap. 5).
