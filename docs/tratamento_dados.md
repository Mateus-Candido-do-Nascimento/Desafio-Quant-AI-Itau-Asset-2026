# Tratamento dos dados — Reclamações do BC

> Como os CSVs crus do BC viram a tabela que alimenta o modelo. Cada decisão de
> limpeza está aqui com o **porquê**. Os números deste documento são gerados por
> `src/tratar_reclamacoes.py`; rode-o e confira contra `data/processed/`.

**Entrada:** `csv/{ano}/{q} trimestre/Bancos+...+Reclamacoes...csv`
**Saída:** `data/processed/reclamacoes_conglomerados.csv` (todos os bancos)
e `reclamacoes_universo.csv` (só os 13 tickers).
**Rastro:** `data/processed/tratamento_log.txt`.

---

## 1. Por que isto é o passo mais importante

O modelo só é tão honesto quanto o dado que entra nele. Antes de qualquer
fórmula de event study, precisamos de uma tabela em que cada linha seja
**um banco, num trimestre, com seu índice e suas reclamações** — sem duplicata,
sem subsidiária contada em dobro, sem número mal convertido. Esta etapa produz
exatamente isso, e deixa registrado tudo que foi descartado e por quê.

---

## 2. Os 4 obstáculos do dado cru

### 2.1 Encoding e número em formato BR
Os CSVs são `;`-separados, encoding **latin-1**. Números vêm no formato
brasileiro: `"1.665,06"` (ponto = milhar, vírgula = decimal). A função
`num_br` (em `src/config.py`) converte para float; string vazia ou espaço
vira `NaN` (ausência de dado, não zero).

### 2.2 A "linha-mãe" do conglomerado
Cada conglomerado aparece com uma linha consolidada (a que tem o índice do
grupo) seguida das subsidiárias. **Só queremos a linha-mãe.** As subsidiárias
vêm com índice 0 e contaminariam tudo se entrassem.

Como identificar a linha-mãe depende do layout (ver §3):
- **Layouts antigos:** coluna `Tipo == "Conglomerado"`; o nome está em
  *Instituição financeira* com o sufixo `(conglomerado)`, que removemos.
- **Layout novo:** coluna `Conglomerado` preenchida **e** *Instituição
  financeira* vazia.

### 2.3 Mapa banco → ticker, feito à mão
O nome no BC ("ITAU", "BTG PACTUAL/BANCO PAN") não casa automaticamente com o
ticker da B3. Casar por substring gera falso positivo (o clássico: "ITA" casa
dentro de "CNH INDUSTRIAL"). Por isso o `MAPA_TICKER` em `config.py` é
explícito, 13 entradas. Bancos fora do mapa são mantidos no arquivo completo
(`no_universo = False`) para auditoria, mas não entram na análise.

### 2.4 BDRs não são ações domésticas
`ROXO34` (Nubank) e `INBR` (Inter) são **BDRs** — recibos de ações negociadas
na NYSE/Nasdaq. O preço reage ao mercado americano e ao câmbio, não a um evento
doméstico como o ranking do BC. Marcamos `eh_bdr = True` e os deixamos **fora
da análise principal** (entram só como teste de robustez). Ver
[[metodologia_event_study]] §0.

---

## 3. A armadilha escondida: o BC mudou o layout 6 vezes

Varrendo 2017Q1→2026Q1 (36 trimestres), encontramos **6 estruturas de coluna
diferentes**. O BC reformou a planilha ao longo dos anos. Tratar isso com nomes
de coluna fixos quebra — por isso usamos um **resolvedor por palavra-chave**
(`_resolver` em `tratar_reclamacoes.py`): cada campo lógico tem uma lista de
candidatos `(termos_que_incluem, termos_que_excluem)`, em ordem de prioridade.

| Layout | Trimestres | Marca distintiva |
|---|---|---|
| 1 | 2017Q1–2019Q3 (9) | tem `clientes – FGC` + `Unnamed:15` |
| 2 | 2017Q2/Q4 (2) | igual ao 1, sem `Unnamed` |
| 3 | 2019Q4–2020Q1 (2) | sem coluna FGC |
| 4 | 2020Q2–2024Q1 (15) | base "antiga" estável |
| 5 | 2024Q2 (1) | troca p/ "respondidas" e só "procedentes extrapoladas" |
| 6 | 2024Q3–2026Q1 (7) | ganha coluna `Conglomerado`; perde nº de clientes |

### 3.1 Descontinuidade nas contagens (afeta a F3)
As colunas de contagem **não têm a mesma definição** entre layouts:

| Campo lógico | Layouts 1–4 | Layout 5 | Layout 6 |
|---|---|---|---|
| total de reclamações | "total de reclamações" | "...respondidas" | "...analisadas" |
| procedentes | "reguladas procedentes" | só "procedentes **extrapoladas**" | "procedentes" |
| nº de clientes | presente | presente | **ausente** |

**Consequência:** a feature **F3 (razão procedente/total)** tem uma quebra de
definição em 2024. No relatório isso entra como ressalva, e na modelagem
podemos (a) restringir F3 ao período homogêneo, ou (b) tratar o regime como
variável de controle. **A F1 (índice) não sofre disso** — é a mesma métrica em
todos os layouts, e por isso é nossa âncora.

---

## 4. Resultado do tratamento (números atuais)

Da execução de `tratar_reclamacoes.py`:

```
Linhas-mãe extraídas (todos os bancos):      2960
Linhas no nosso universo (têm ticker):        427
   dos quais BDR (ROXO34/INBR):                51
```

Universo sem BDR: **376 linhas** banco×trimestre. Essa é a base do event study,
antes do filtro point-in-time (que o `teste_viabilidade.py` aplica).

---

## 5. Achado crítico: o índice (F1) é esparso para bancos pequenos

O BC só calcula o índice quando o banco está numa **faixa ranqueada** (rótulos
que mudaram de nome: "Top 15", "Top 10", "Mais de quatro milhões de clientes").
Abaixo de um limiar de reclamações, o banco aparece na lista **sem índice**.

Disponibilidade da F1 no nosso universo (trimestres com índice / aparições):

| Ticker | Com índice | Aparições | Situação |
|---|---|---|---|
| ITUB4, BBDC4, BBAS3, SANB11 | 36 | 36 | sólido |
| BMEB4, BMGB4 | 36 | 36 | sólido |
| BRSR6 | 35 | 36 | sólido |
| BPAC11 | 19 | 19 | sólido (desde IPO 2018) |
| **SFSA4** | **17** | 36 | **F1 esparsa (~metade)** |
| **BEES3** | **14** | 36 | **F1 esparsa (~40%)** |
| **ABCB4** | **0** | 33 | **F1 nunca calculada** |
| ROXO34, INBR | — | — | BDR, fora da análise |

**Por que importa muito.** A tese compara o poder explicativo da **F1 (índice
cru)** contra a **severidade do LLM**. Esse ablation só é possível em bancos que
têm F1. Na prática:
- **8 bancos com F1 sólida** sustentam o teste central → suficiente.
- **ABCB4** entra só pela via do LLM (que lê o perfil de irregularidades, não
  depende do índice) e pelas contagens — mas fica de fora do ablation F1-vs-LLM.
- ABCB4 é banco de atacado (poucos clientes de varejo → poucas reclamações →
  nunca cruza o limiar). É um caso legítimo de exclusão, não um bug.

### 5.1 Decisão fixada: o ablation roda sobre os 8 bancos com F1 sólida

Definimos em `config.BANCOS_F1_SOLIDA` os 8 bancos que entram no ablation
central (coluna `f1_solida` no CSV de saída):

> ITUB4, BBDC4, BBAS3, SANB11, BMEB4, BMGB4, BRSR6, BPAC11

**Por que NÃO reconstruímos um índice caseiro para os demais** (decisão tomada
após comparar as alternativas):

1. **Não seria consistente.** O índice caseiro exigiria a coluna `clientes`, que
   **desaparece no layout 6 (2024Q3+)**. A série existiria em 2020 mas não em
   2025 — pior que o buraco original.
2. **Contaminaria o teste.** A tese compara a severidade do LLM contra o
   **índice oficial do BC**. Misturar oficial + proxy no braço "índice cru"
   torna a linha de base inconsistente e indefensável na banca.
3. **A ausência é informação.** O BC não calcula o índice abaixo de um limiar
   material de reclamações (ABCB4 teve 7 reclamações num trimestre). Esses
   bancos têm sinal de reclamação fino **e** são small caps ilíquidas → retorno
   anormal ruidoso. São os mesmos bancos fracos nos dois lados; excluí-los do
   ablation **melhora** a qualidade.

**O que NÃO muda:** ABCB4/BEES3/SFSA4 continuam no projeto pela via do LLM
(F4/F5 leem o perfil de irregularidades, não o índice). Só ficam fora do
*head-to-head* F1-vs-LLM.

**Frase para o relatório:** *"O índice do BC só é definido acima de um limiar
material de reclamações; abaixo dele o sinal é fino demais e a ação ilíquida
demais para um event study limpo. Restringimos o ablation aos bancos com índice
oficial, preservando a consistência da linha de base."*

---

## 6. Esquema do arquivo de saída

`data/processed/reclamacoes_universo.csv` (`;`-separado, UTF-8):

| Coluna | Significado |
|---|---|
| `ano`, `trimestre` | período de referência da reclamação |
| `banco_bc` | nome do conglomerado como vem no BC |
| `ticker` | ticker B3 mapeado à mão |
| `no_universo` | está no nosso MAPA_TICKER? |
| `eh_bdr` | é BDR (fora da análise principal)? |
| `categoria` | faixa do BC (muda de rótulo entre anos) |
| `indice` | **F1** — índice de reclamações do BC (`NaN` se não calculado) |
| `recl_total` | total de reclamações (def. varia por layout, ver §3.1) |
| `recl_procedentes` | reclamações procedentes (idem) |
| `razao_procedente` | **F3 candidata** = procedentes / total |
| `clientes` | nº de clientes (ausente no layout 6) |

---

## 7. O que falta (próximos passos do tratamento)

1. **Aceleração trimestral (F2):** derivar do `indice` em t vs. t-1, por ticker.
   Exige a série temporal já ordenada (o universo.csv já permite).
2. **Resgatar BAZA3/BNBR3:** Banco da Amazônia e do Nordeste aparecem como
   instituição individual, não conglomerado — hoje ficam fora. Avaliar inclusão.
3. **Features do LLM (F4, F5):** virão do arquivo de *irregularidades*, ainda
   não tratado aqui. Pipeline separado.
4. **Preços (yfinance):** baixar `Adj Close` dos tickers + `^BVSP`, base do
   cálculo de retorno. Ver [[metodologia_event_study]] §2.
