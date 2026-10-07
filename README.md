# Robô Fundamento

Alocação sistemática entre classes de ativo com rebalanceamento mensal.
Projeto do **Desafio Quant AI 2026** (Itaú Asset).

> No Brasil o ativo livre de risco rende cerca de 10% ao ano. Isso muda a
> natureza do problema de alocação: correr risco só faz sentido quando o risco
> está sendo remunerado acima disso. O robô mede essa remuneração todo mês,
> realoca para as classes que estão entregando e, quando nenhuma está,
> simplesmente não corre risco.

A régua do projeto é o **CDI**, não a bolsa. Todo Sharpe aqui é calculado sobre
o retorno **excedente ao CDI**: no Brasil, ignorar o custo de oportunidade infla
qualquer métrica de risco-retorno.

---

## Resultados

Período jan/2015 a jul/2026 (139 meses), líquido de custos, point-in-time.

| Estratégia | Retorno a.a. | Vol. | Acima do CDI | Sharpe | Máx. queda |
|---|---|---|---|---|---|
| **Robô Fundamento** | **15,7%** | 10,8% | **+5,3%** | **0,53** | **−11%** |
| Rebalanceamento puro (peso igual) | 14,1% | 7,6% | +3,8% | 0,51 | −9% |
| Filtro de tendência apenas | 13,3% | 7,4% | +3,1% | 0,44 | −7% |
| Carteira balanceada 60/40 | 11,2% | 8,6% | +1,2% | 0,18 | −15% |
| Ibovespa | 11,6% | 21,5% | +1,5% | 0,18 | −37% |
| CDI (régua) | 9,9% | 1,1% | — | — | 0% |

- **Fora da amostra (2020+):** +5,0% sobre o CDI, Sharpe 0,58, acima do próprio
  desempenho no período completo. No mesmo intervalo, Ibovespa e 60/40
  **perderam** para o CDI.
- **Significância: t = 1,80, p = 0,074.** Marginal a 10%, **não** a 5%. Nunca
  apresentar como p < 0,05. O que sustenta a estratégia é o conjunto de testes
  de robustez, não o p-valor isolado.
- **Robustez:** positivo em todas as janelas de momentum testadas (6 a 24
  meses), em todas as frequências de rebalanceamento, sob custo 2,5× maior e
  removendo qualquer classe do cardápio. A janela adotada (12 meses) **não é a
  melhor** do conjunto, o que é evidência direta contra superotimização.
- **Onde falha:** perdeu para o CDI em 2022-2023 (−7,1% ao ano). Momentum é
  sinal defasado e tomou chicotadas na virada de regime com a Selic a 13,75%.

---

## A regra

Todo mês, para cada classe, calcula-se o momentum de 12 meses
`mom(c,t) = P(c, t-1) / P(c, t-13) - 1`. O uso de `t-1` é deliberado: a decisão
do mês *t* nunca enxerga o próprio mês que está alocando.

| Passo | O que faz | Por quê |
|---|---|---|
| 1. Trava absoluta | descarta a classe cujo momentum não supera o CDI | impede comprar a melhor entre as ruins; ficar parado é decisão legítima |
| 2. Ranking | ordena as aprovadas e distribui 40 / 30 / 20 / 10% | concentra no que entrega, sem apostar tudo numa classe |
| 3. Caixa | todo peso não alocado vai para o CDI | o excedente rende cerca de 10% ao ano sem risco |
| 4. Rebalanceia | volta aos pesos-alvo, pagando o giro | controla risco e realiza ganho de quem subiu demais |

**Universo:** CDI (caixa), Ações (Ibovespa), Global (S&P 500 *total return* em
BRL, via IVVB11), Ouro (em BRL) e Dólar.

O desenho é a adaptação ao Brasil do *Dual Momentum* (Antonacci, 2014) e da
alocação tática de Faber (2007): momentum absoluto é a trava do CDI, momentum
relativo é o ranking. A contribuição própria está na adaptação, porque nos
mercados desenvolvidos o caixa rende perto de zero e a trava quase nunca
aciona, enquanto no Brasil ela é o mecanismo central.

---

## Camada de IA generativa

Um modelo de linguagem lê as **atas do Copom**, classifica o regime de juros
(aperto / neutro / afrouxamento) e inclina a alocação: em aperto o robô reduz a
exposição a risco em um quarto, com a sobra indo para o CDI; em afrouxamento faz
o inverso. Sempre com teto de 100% em risco, de modo que a camada **nunca
introduz alavancagem**.

A motivação é precisa: momentum é retrovisor e só percebe uma virada depois que
ela apareceu no preço. A ata é o documento em que o Banco Central comunica a
direção da política monetária **antes** de o preço reagir.

### Estado

| Braço | Situação |
|---|---|
| Controle (direção da Selic, zero IA) | **validado** |
| LLM lendo as atas | implementado e testado, **não executado** (falta chave de API) |

Resultado do braço de controle:

| Versão | Acima do CDI | Sharpe | p | 2022-2023 | Exposição a risco |
|---|---|---|---|---|---|
| Robô base | +5,3% | 0,53 | 0,074 | −7,1% | 69% |
| **Com regime de juros** | **+5,5%** | **0,59** | **0,048** | **−5,5%** | **65%** |

A melhora acontece no subperíodo que era o alvo, e a exposição média a risco
**cai**. A camada melhora o Sharpe reduzindo risco, o oposto exato do
vol-targeting que foi rejeitado (ver abaixo).

### Três cuidados metodológicos

1. **Point-in-time.** A ata sai cerca de 6 dias úteis após a reunião, e só entra
   na decisão **8 dias corridos** depois. `src/robo/teste_copom.py` prova sobre
   os dados que nenhum mês usa ata publicada após o seu início.
2. **Contaminação do LLM.** Um modelo treinado hoje conhece o desfecho de uma
   ata antiga, e isso não dá para eliminar. Então **medimos**: o braço de
   controle constrói o mesmo sinal sem nenhuma IA, pela direção da última
   mudança da Selic, com defasagem idêntica. Se a leitura do texto não superar o
   número público, a conclusão declarada é que a IA não agregou.
3. **Pré-registro.** As hipóteses, a intensidade da inclinação e a conclusão de
   cada desfecho possível foram escritas **antes** de existir chave de API na
   máquina, em `docs/pre_registro_ia.md`, verificável pelo histórico do Git.

---

## O que foi testado e rejeitado

Três variantes **cruzaram p < 0,05** e foram rejeitadas de propósito. Isso é
parte central do trabalho, não uma nota de rodapé.

| Variante | p | Motivo da rejeição |
|---|---|---|
| Vol-targeting | 0,029 | **alavancagem disfarçada**: exposição a risco de 62% para 70%, escala média 1,16×, melhora em só 3 de 6 subperíodos |
| Risk parity | 0,036 | melhora apenas no recorte 2010+ e **piora** no recorte principal |
| Incluir criptomoeda | 0,004 | ETF de bitcoin na B3 só existe desde 2021; no subperíodo investível o ganho cai para +2,3% com **p = 0,50**. É viés de sobrevivência no nível de **classe** |

Com oito variantes testadas, a correção de Bonferroni leva o melhor p (0,029) a
0,232: nenhuma sobrevive ao ajuste por múltiplos testes.

**A matemática do limite:** a estatística t de um excedente aproxima-se de
`Sharpe × raiz(anos)`. Para demonstrar um Sharpe de 0,53 com 95% de confiança
seriam necessários `(1,96 / 0,53)² ≈ 13,8 anos`; há 11,6. **Faltam cerca de dois
anos de dados, não uma estratégia melhor.**

A criptomoeda continua rodável com `INCLUIR_CRIPTO = True` em
`src/robo/config.py`, como extensão documentada.

---

## Como rodar

Requer Python 3.13+ e um ambiente virtual em `venv/`.

```bash
venv/Scripts/python.exe -m pip install -r requirements.txt
```

| Comando | O que faz |
|---|---|
| `venv/Scripts/python.exe src/robo/rodar.py` | backtest principal e testes de robustez |
| `venv/Scripts/python.exe src/robo/reforco.py` | os testes que um avaliador crítico faria |
| `venv/Scripts/python.exe src/robo/busca_significancia.py` | a busca disciplinada por p < 0,05 |
| `venv/Scripts/python.exe src/robo/rodar_ia.py` | ablation da camada de IA (não precisa de chave) |
| `venv/Scripts/python.exe src/robo/teste_copom.py` | 30 checagens do pipeline de IA, custo zero |
| `venv/Scripts/python.exe entrega/gerar_grafico.py` | gera o gráfico do relatório |
| `venv/Scripts/python.exe entrega/gerar_relatorio_docx.py` | gera o relatório final em `.docx` |

### Rodar o braço do LLM

Precisa de uma chave da Anthropic num `.env` na raiz (já está no `.gitignore`):

```
ANTHROPIC_API_KEY=sk-ant-...
```

Depois, **nesta ordem**, porque o teste de chave custa centavos e evita
comprometer a rodagem cheia com uma credencial errada:

```bash
venv/Scripts/python.exe src/robo/copom.py --estimar
venv/Scripts/python.exe src/robo/copom.py --testar-chave
venv/Scripts/python.exe src/robo/copom.py --classificar
venv/Scripts/python.exe src/robo/rodar_ia.py
```

A rodagem é **retomável**: grava o CSV a cada ata, aborta na primeira se a chave
for inválida e nunca sobrescreve um CSV bom com um vazio. Depois de rodar uma
vez, o resultado fica em `data/processed/copom_regimes.csv` e o backtest passa a
ser reproduzível por qualquer pessoa **sem chave**.

> O relatório final é gerado em `.docx` e o PDF sai de uma exportação do próprio
> Word. O gerador antigo em ReportLab (`entrega/gerar_relatorio.py`) está
> **superado**: as células de tabela não quebravam linha e o texto vazava para
> fora da borda.

---

## Estrutura

```
src/robo/     config.py       parâmetros, fonte única de verdade
              dados.py        API SGS do Banco Central e yfinance
              estrategia.py   as regras de alocação
              backtest.py     o motor de simulação (implementado aqui)
              rodar.py        backtest principal e robustez
              reforco.py      testes de avaliador crítico
              busca_significancia.py
              copom.py        camada de IA: atas, LLM e controle mecânico
              rodar_ia.py     ablation da camada de IA
              teste_copom.py  testes do pipeline de IA, sem custo de API

docs/         metodologia_robo.md      como o robô funciona
              resultados_robo.md       números e análise
              fundamentacao_robo.md    a literatura por trás
              busca_significancia.md   o que foi rejeitado e por quê
              camada_ia_copom.md       fórmulas da camada de IA
              pre_registro_ia.md       hipóteses fixadas antes de rodar o LLM

entrega/      gerar_grafico.py         figura do relatório
              gerar_relatorio_docx.py  relatório final (.docx)
              gerar_relatorio.py       versão legada em ReportLab

notebooks/    robo_fundamento.ipynb    Colab auto-contido
data/         raw/ (atas do Copom) e processed/ (saídas do backtest)
pdf-itau/     edital e documentos oficiais da competição
```

---

## Dados

Tudo público e gratuito.

| Fonte | O que vem dela |
|---|---|
| API SGS do Banco Central | CDI (série 12), IPCA (433), meta Selic (432) |
| API de atas do Copom | as 81 atas em PDF publicadas desde jul/2016 |
| Yahoo Finance | Ibovespa, S&P 500 *total return*, ouro e dólar |

A API do SGS exige `User-Agent` de navegador e aceita blocos de até cerca de 10
anos por requisição. Ela também falha de duas formas transitórias (HTTP 200 com
página HTML de erro quando há rajada de requisições, e 502/503 por
instabilidade), ambas tratadas com espera exponencial em `dados.py`.

---

## Rigor do backtest

O motor foi **implementado neste repositório**, sem plataforma pronta, como
exige o edital. Ele percorre mês a mês, lê os pesos-alvo decididos com dados até
`t-1`, paga o custo do giro no rebalanceamento, apura o retorno e deixa a
carteira **derivar** até o mês seguinte, como uma carteira real em que quem sobe
passa a pesar mais.

| Viés | Tratamento |
|---|---|
| Look-ahead | todo sinal com defasagem de um mês |
| Custos | 10 bps por unidade de giro, descontados (giro médio de 27% ao mês) |
| Sobrevivência | índices de classe, não ações individuais |
| Superotimização | validação fora da amostra e sensibilidade em todos os parâmetros |

---

## Direções abandonadas

Três linhas foram testadas e descartadas **com dados**, e o código fica no
repositório como registro:

1. **Ranking de reclamações do Banco Central contra preço de ação de banco**
   (event study). Universo estreito demais (11 bancos) e achado quase
   tautológico. Ver `docs/metodologia_event_study.md`.
2. **Somas de Ramanujan** para detecção de ciclos. Detecta ciclo real (por
   exemplo, semanal na volatilidade do bitcoin, 26× o ruído), mas **não é
   negociável**: o vol-timing não melhorou o Sharpe e uma dummy de calendário
   empata ou ganha. Ver `docs/fundamentacao_ramanujan.md`.
3. **Momentum em ações individuais brasileiras.** Funciona, mas foi preterido
   porque o objetivo é alocação entre classes, não seleção de ações.

A lição transversal, que vale além deste projeto: **detectável não é
negociável**, e o simples costuma ganhar do sofisticado.

---

## Convenções

- Sempre usar o Python do `venv/` do projeto, não o do sistema.
- Scripts que imprimem no console começam com
  `sys.stdout.reconfigure(encoding="utf-8")`, porque o console do Windows é
  cp1252.
- Commits em Conventional Commits, mensagens sem acento.
- Números no relatório **não são digitados à mão**: vêm do backtest, calculados
  no momento da geração.
