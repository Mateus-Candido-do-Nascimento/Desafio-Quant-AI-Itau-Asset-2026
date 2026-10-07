# Camada de IA — o robô lendo as atas do Copom

> Como um LLM lê o Banco Central e vira decisão de carteira. Metodologia do robô
> base: [[metodologia_robo]]. Resultados do robô base: [[resultados_robo]].
> O que já rejeitamos e por quê: [[busca_significancia]].
>
> Código: `src/robo/copom.py` · `src/robo/estrategia.py:pesos_ranking_ia` ·
> `src/robo/rodar_ia.py`

---

## 1. O problema que esta camada ataca

O robô perdeu dinheiro **uma única vez** no backtest: **2022–23, −7,1% abaixo do
CDI**. A causa está documentada: o momentum de 12 meses é retrovisor por
construção. Quando a Selic saiu de 2% para 13,75%, o sinal só percebeu a virada
depois que ela já tinha aparecido no preço — e o robô tomou chicotada
(*whipsaw*) entrando e saindo tarde.

A ata do Copom é o documento em que o Banco Central diz, **em português e antes
do preço reagir**, para onde a política monetária está indo. É pública, datada,
e em texto livre — exatamente o tipo de dado que um modelo quantitativo
tradicional não consegue usar e um LLM consegue.

> **A tese do robô aplicada aos juros:** se correr risco só faz sentido quando o
> risco está pagando, então quando o CDI está ficando mais caro de abrir mão
> (aperto), o robô deve correr menos risco — e o BC anuncia isso antes de o
> preço contar.

---

## 2. As fórmulas

### 2.1 Disponibilidade — a trava point-in-time

A ata é divulgada cerca de **6 dias úteis depois** da reunião. Usá-la na data da
reunião seria olhar o futuro. Definimos, de forma conservadora:

$$
d_{\text{disp}}(a) \;=\; d_{\text{reunião}}(a) \;+\; 8 \text{ dias corridos}
$$

8 dias corridos são **sempre** ≥ 6 dias úteis, então nunca antecipamos a
informação. O regime que vale para a decisão do mês $t$ é o da ata mais recente
já publicada no fim do mês anterior:

$$
R_t \;=\; \text{regime}\big(\arg\max_{a}\; \{ d_{\text{disp}}(a) \;\le\; \text{fim do mês } t-1 \}\big)
$$

Na prática (`copom.regime_mensal`): a série de regimes é indexada pela data de
**disponibilidade**, propagada para a frente (`ffill`), reamostrada para o fim de
cada mês, e por fim `shift(1)` — a mesma trava que `estrategia.py` usa em todos
os outros sinais. Nenhuma linha enxerga o próprio mês que está alocando.

### 2.2 Classificação — o que o LLM devolve

A tarefa é enunciada como **leitura**, não previsão: *"classifique o regime que
ESTE DOCUMENTO COMUNICA, com base apenas no que está escrito nele"*. Não
perguntamos o que vai acontecer com a bolsa.

A instrução central do prompt é **separar o que o Comitê FEZ do que ele
SINALIZA** — porque a decisão do dia já é pública num número (a meta Selic), e o
que só existe no texto é a parte prospectiva:

| Campo | Domínio | Papel |
|---|---|---|
| `regime` | aperto / neutro / afrouxamento | **Sinal primário.** A postura geral comunicada |
| `vies_prospectivo` | alta / manutenção / queda | **Hipótese H3.** O que sinalizam para as *próximas* reuniões |
| `restritividade` | 0 a 10 | O quanto descrevem a política como contracionista |
| `incerteza` | 0 a 10 | O quanto enfatizam risco e dispersão de cenários |
| `confianca` | 0 a 1 | O quanto o texto é explícito |
| `evidencia` | citação literal | **Auditabilidade** |

Um Comitê pode cortar juros hoje e sinalizar cautela adiante, ou manter hoje e
sinalizar alta. **É essa diferença que o número da Selic não consegue conter** —
e é exatamente onde a hipótese H3 (§4.6) procura o valor da leitura.

A `evidencia` é o que torna a camada auditável: dá para abrir o CSV e conferir,
ata por ata, o trecho que sustentou cada classificação.

> Os campos extras **não** são um menu para escolher o melhor depois. O sinal
> primário está fixado em `regime` e o secundário em `vies_prospectivo`, ambos
> declarados antes de rodar o modelo — ver [[pre_registro_ia]].

### 2.3 A inclinação — de regime para peso

Seja $w^{\text{base}}_{c,t}$ o peso da classe $c$ que o ranking do robô produziria
no mês $t$, e $\rho_t = \sum_{c \in \text{risco}} w^{\text{base}}_{c,t}$ a exposição
total a risco. O fator de inclinação é:

$$
f(R_t) =
\begin{cases}
1 - \tau & \text{se } R_t = \text{aperto} \\[2pt]
1 + \tau & \text{se } R_t = \text{afrouxamento} \\[2pt]
1 & \text{se } R_t = \text{neutro \; ou \; sem ata publicada}
\end{cases}
\qquad \tau = 0{,}25
$$

Os pesos de risco são reescalados, e **o que sobra ou falta vai para o CDI**:

$$
w_{c,t} = w^{\text{base}}_{c,t} \cdot \underbrace{\min\!\left(f(R_t),\; \tfrac{1}{\rho_t}\right)}_{\text{trava de 100\%}}
\qquad\text{e}\qquad
w_{\text{CDI},t} = 1 - \sum_{c \in \text{risco}} w_{c,t}
$$

**Três travas, todas herdadas das nossas próprias rejeições anteriores:**

1. O $\min(\cdot,\,1/\rho_t)$ limita a exposição a risco a 100%. **Não há
   alavancagem** — foi exatamente por alavancagem disfarçada que rejeitamos o
   vol-targeting.
2. A inclinação **nunca reabilita** uma classe reprovada no momentum absoluto.
   Ela só redimensiona o que o ranking já aprovou.
3. **A trava do CDI continua soberana:** se nenhuma classe de risco bate o CDI,
   o robô fica 100% em CDI, diga a ata o que disser.

> $\tau = 0{,}25$ é escolha **a priori** ("um quarto da exposição a risco"), não
> resultado de otimização. A §4.3 mostra que a conclusão não depende desse número.

---

## 3. O braço de controle — a parte mais importante deste documento

### A crítica que um avaliador experiente vai fazer

> *"Um LLM treinado em 2026 lendo uma ata de 2016 já sabe o que aconteceu
> depois. Isso é look-ahead embutido nos pesos do modelo, e você não consegue
> removê-lo."*

A crítica é **legítima e não tem solução completa**. Mascarar datas ajuda pouco:
o nível da Selic citado na ata já identifica a época. Fingir que resolvemos seria
pior do que o problema.

### O que fazemos em vez de fingir

Construímos o **mesmo sinal sem nenhuma IA**. A série SGS 432 (meta Selic
definida pelo Copom) é pública e point-in-time; a direção da última mudança dá:

$$
R^{\text{mec}}_t =
\begin{cases}
\text{aperto} & \text{se a última mudança da meta foi de alta} \\
\text{afrouxamento} & \text{se foi de baixa}
\end{cases}
$$

com **exatamente a mesma defasagem de 8 dias**, para que os dois braços tenham a
mesma informação disponível na mesma data. A única diferença entre eles é a
*leitura*: um lê o número, o outro lê o texto.

Isso transforma uma discussão insolúvel numa medição:

| Se acontecer | O que concluímos |
|---|---|
| LLM ≈ mecânico | O LLM não agregou nada além do que já estava num número público. **Reportamos isso** — e o resultado do robô não depende de IA. |
| LLM > mecânico | O texto tem informação que o número não tem (o *balanço de riscos*, a sinalização adiante). Aí é preciso investigar se é leitura genuína ou contaminação. |
| LLM < mecânico | A leitura atrapalhou. Reportamos e não usamos. |

**Em qualquer um dos três casos temos um resultado honesto para o relatório.**
É a diferença entre "usamos IA" e "medimos o que a IA fez".

---

## 4. Resultados — braço de controle (jan/2015 a jul/2026, 139 meses)

> ⚠️ **Estado:** o braço mecânico está rodado e validado. O braço do **LLM ainda
> não rodou** — falta chave de API (ver §6). Os números abaixo são todos do
> controle, e o relatório não deve afirmar nada sobre o LLM até ele rodar.

### 4.1 Período completo

| Braço | Retorno a.a. | Acima do CDI | Sharpe | Máx. queda | t | p |
|---|---|---|---|---|---|---|
| Robô sem IA (base) | 15,7% | +5,3% | 0,53 | −11% | 1,80 | 0,074 |
| **Robô + regime de juros** | **15,9%** | **+5,5%** | **0,59** | **−11%** | **2,00** | **0,048** |

### 4.2 Só onde a camada atua (ago/2016 em diante, 120 meses)

Antes de ago/2016 os dois braços são idênticos por construção (§5), então incluir
esse trecho dilui o efeito nos dois sentidos.

| Braço | Acima do CDI | Sharpe | p |
|---|---|---|---|
| Robô sem IA (base) | +5,5% | 0,62 | 0,054 |
| Robô + regime de juros | +5,8% | 0,65 | 0,041 |

### 4.3 A conclusão depende do tamanho da inclinação?

| $\tau$ | Acima do CDI | Sharpe |
|---|---|---|
| 10% | +5,5% | 0,56 |
| **25% (a priori)** | **+5,5%** | **0,59** |
| 40% | +5,4% | 0,60 |
| 50% | +5,3% | 0,61 |

**Não.** O Sharpe melhora em relação ao base (0,53) em toda a faixa testada. O
valor que escolhemos a priori não é o melhor do conjunto — mesma evidência
contra *data snooping* que já usamos na janela de momentum.

### 4.4 Por subperíodo

| Subperíodo | Sem IA | Com regime | |
|---|---|---|---|
| 2016-08 a 2019 | +6,3% | +6,9% | melhora |
| 2020–21 (covid) | +16,8% | +18,5% | melhora |
| **2022–23 (a virada)** | **−7,1%** | **−5,5%** | **melhora — era o alvo** |
| 2024 em diante | +6,5% | +4,4% | **piora** |

Melhora em 3 de 4 subperíodos, **incluindo o único em que o robô perdia** — que
era exatamente o problema que a camada foi desenhada para atacar. Piora em
2024+; está reportado, não escondido.

### 4.5 O teste que reprovou o vol-targeting

Rejeitamos o vol-targeting (p = 0,029) por ser **alavancagem disfarçada**:
subia a exposição a risco de 62% para 70%, escala média 1,16×. A mesma régua,
aplicada aqui:

| Braço | Exposição média a risco | Escala média | Meses 100% CDI |
|---|---|---|---|
| Robô sem IA (base) | 68,7% | 1,000 | 17 |
| Robô + regime de juros | **65,3%** | **0,953** | 17 |

**Passa — e no sentido oposto.** A inclinação melhora o Sharpe **reduzindo** a
exposição a risco (escala 0,95×, não 1,16×), e não mexe nos 17 meses em que o
robô foge 100% para o CDI. Não é alavancagem.

`rodar_ia.py` §5 aplica esse teste automaticamente e **imprime REPROVAR** se
qualquer variante futura aumentar a exposição a risco.

---

## 5. Limitações — o que não conseguimos fazer

1. **Cobertura das atas.** A API do BC só serve as atas em PDF a partir da **200ª
   reunião (jul/2016)**. Antes disso o site entrega uma página HTML renderizada
   por JavaScript, sem texto acessível. Portanto a camada só atua de **ago/2016**
   em diante: são 120 dos 139 meses. Nos 19 meses anteriores o robô com IA é
   **idêntico** ao robô sem IA. É limitação de disponibilidade de dado, não
   escolha metodológica.

2. **Contaminação residual do LLM.** Mitigada pelo braço de controle (§3), não
   eliminada. A máscara de datas (`_mascarar_datas`) é medida parcial e está
   assumida como tal no código.

3. **O sinal mecânico não tem "neutro".** A direção da última mudança da Selic
   persiste até a próxima mudança, então o controle está sempre em aperto ou
   afrouxamento (70 e 69 meses). O LLM consegue devolver "neutro" — uma diferença
   qualitativa real entre os dois braços, e uma das coisas que o teste §6 do
   `rodar_ia.py` vai medir.

4. **Testes múltiplos.** Esta é mais uma variante somada às 8 de
   [[busca_significancia]]. O p = 0,048 do controle **não sobrevive a Bonferroni**
   sobre o programa inteiro de testes. O que sustenta a camada é o conjunto —
   robustez ao $\tau$, melhora no subperíodo-alvo, redução de risco — e não o
   p-valor isolado. **Não vender como p < 0,05.**

---

### 4.6 H3 — a vantagem vem do que o número não tem?

Teste **pré-registrado** ([[pre_registro_ia]]), automatizado em `rodar_ia.py` §7.

A decisão do Copom já está na Selic. O que só existe no texto é a sinalização
prospectiva. Então separamos os meses em que o `vies_prospectivo` lido
**diverge** da direção mecânica, e comparamos a vantagem do LLM nos dois grupos:

- **Vantagem concentrada na divergência** → é leitura genuína do texto. Aceitar.
- **Vantagem espalhada por igual**, inclusive onde texto e número concordam →
  o ganho não veio da leitura. **Suspeita de contaminação**, não usar como
  resultado principal.

É a única forma que encontramos de distinguir "o LLM leu bem" de "o LLM sabe o
que aconteceu depois" — e a regra de decisão foi escrita antes de rodar.

---

## 5b. Como sabemos que o pipeline está correto

`src/robo/teste_copom.py` roda **30 verificações sem gastar nada**, trocando a
chamada da API por um cliente falso. Cobre o caminho inteiro: índice das atas,
extração de PDF (nas mais antigas e nas mais novas), máscara de datas, esquema
da resposta, ida e volta pelo CSV, e a inclinação da carteira.

Duas verificações merecem destaque:

1. **Vazamento point-in-time.** Para cada mês com sinal, o teste confere
   diretamente que a ata usada foi publicada **antes do início daquele mês**.
   Não é inspeção de código — é prova sobre os dados.
2. **As travas da inclinação.** Que aperto reduz risco, que afrouxamento não
   reduz, que neutro não altera nada, que a exposição nunca passa de 100%, e que
   **nenhuma ata reabilita classe reprovada no momentum absoluto**.

As 81 atas já foram baixadas e extraídas: **1.319.830 caracteres, zero falhas**,
inclusive nos PDFs de 2016, que são os mais problemáticos.

```bash
venv/Scripts/python.exe src/robo/teste_copom.py
```

---

## 6. Como rodar

### Sem chave de API (roda tudo que não usa LLM)

```bash
venv/Scripts/python.exe src/robo/rodar_ia.py       # braço de controle
venv/Scripts/python.exe src/robo/teste_copom.py    # 30 testes do pipeline
venv/Scripts/python.exe src/robo/copom.py          # situação atual + ajuda
venv/Scripts/python.exe src/robo/copom.py --estimar
```

### Com chave de API — o braço do LLM

Crie um `.env` na raiz do projeto (já está no `.gitignore`):

```
ANTHROPIC_API_KEY=sk-ant-...
```

Depois, **na ordem** — o teste de chave custa centavos e evita comprometer os
US$ 4,46 da rodagem cheia com uma chave errada:

```bash
venv/Scripts/python.exe src/robo/copom.py --testar-chave   # 1 ata, ~US$ 0,06
venv/Scripts/python.exe src/robo/copom.py --classificar    # as 81, ~US$ 4,46
venv/Scripts/python.exe src/robo/rodar_ia.py               # o ablation completo
```

**Proteções para quem for rodar:**

| Situação | O que acontece |
|---|---|
| Sem chave | Mensagem dizendo onde criar o `.env`. Nada é gasto. |
| Chave inválida | Aborta na **1ª de 81** com mensagem clara — não queima as outras 80. |
| Sem acesso ao modelo | Aborta na 1ª, dizendo que é permissão e não chave. |
| Queda de rede numa ata | Pula e segue; para depois de 10 falhas seguidas. |
| `Ctrl+C` no meio | Salva o que já foi feito. |
| Rodar de novo | **Retoma de onde parou** — só paga o que falta. |
| Rodagem que falha | **Não sobrescreve** o CSV bom com um vazio. |

O CSV é gravado **a cada ata concluída**, então nenhum trabalho já pago se
perde. `--sim` pula a confirmação de custo (para script); `--forcar` refaz do
zero.

**Escolha do modelo e custo.** `claude-opus-5`, saída estruturada por JSON
schema (`output_config.format`), pensamento adaptativo com `effort: medium`.
Números medidos, não estimados no olho (`copom.py --estimar`):

| | |
|---|---|
| Atas | 81 |
| Caracteres | 1.319.830 |
| Tokens de entrada | ~406.600 |
| Tokens de saída | ~97.200 (inclui raciocínio) |
| **Custo total** | **~US$ 4,46**, uma única vez |
| Com a Batch API | ~US$ 2,23 (50% off, resultado em até 1h) |

Usamos o modelo mais capaz porque **a qualidade da leitura é o produto** e o
custo é irrelevante na escala deste projeto. Ficamos na chamada sequencial (e
não na Batch API) porque ela dá progresso ao vivo e o cache em CSV é
incremental: se cair no meio, a rodagem seguinte só refaz o que falta.

```bash
venv/Scripts/python.exe src/robo/copom.py --estimar   # confere o custo antes
```
