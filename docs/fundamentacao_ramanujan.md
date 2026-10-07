# Fundamentação — Somas de Ramanujan para detecção de ciclos

> Base teórica do projeto. A soma $c_q(n)$, a intuição da decomposição em
> períodos, o framework unificado (NPM) e as referências. Cada fórmula com o que
> ela significa — pra qualquer um da equipe defender na banca. Resultado empírico
> em commodities no fim.

---

## 0. O papel do Ramanujan no projeto (uma frase)

> O mercado tem ciclos sazonais reais (gasolina no verão, grãos na safra). As
> **somas de Ramanujan** são um jeito *principiado* de **descobrir qual é o
> período** de cada ativo — em vez de chutar "anual" — e de medir quão forte ele
> é. Não preveem preço; **detectam estrutura periódica** que a gente então
> explora.

A honestidade está aí: Ramanujan **não é uma bola de cristal**. É um detector de
periodicidade. A "previsão" vem da aposta de que o ciclo detectado *persiste* —
e isso é testável (e pode falhar).

---

## 1. A soma de Ramanujan $c_q(n)$

Para inteiros positivos $q$ (o período candidato) e $n$ (o índice de tempo):

$$
c_q(n) \;=\; \sum_{\substack{k=1 \\ \gcd(k,q)=1}}^{q} e^{\,2\pi i\,k n/q}
\;=\; \sum_{\substack{k=1 \\ \gcd(k,q)=1}}^{q} \cos\!\left(\frac{2\pi k n}{q}\right)
$$

| Símbolo | Significado |
|---|---|
| $q$ | período que estamos testando (ex.: 12 meses) |
| $n$ | posição no tempo |
| $k$ | percorre os inteiros de 1 a $q$ **coprimos** com $q$ (as raízes *primitivas*) |
| $\gcd(k,q)=1$ | só as frequências que "pertencem" exatamente a $q$, não a um divisor dele |

**Propriedades que importam:**
- **É sempre um inteiro** — apesar das raízes complexas, a soma cancela a parte imaginária. (Surpreendente e elegante.)
- **É periódica em $n$ com período $q$**: $c_q(n+q)=c_q(n)$.
- $c_q(0)=\varphi(q)$ (a função totiente de Euler — quantos coprimos $q$ tem).
- **Ortogonalidade**: somas de períodos diferentes são "independentes" — é o que permite decompor um sinal em períodos sem dupla contagem.

---

## 2. A "equação" fechada (fórmula de Hölder)

Você pediu *uma equação de Ramanujan*. A mais bonita é a forma fechada que
calcula $c_q(n)$ **sem somar nada**, só com funções aritméticas:

$$
c_q(n) \;=\; \mu\!\left(\frac{q}{d}\right)\,\frac{\varphi(q)}{\varphi\!\left(\frac{q}{d}\right)},
\qquad d=\gcd(n,q)
$$

| Símbolo | Significado |
|---|---|
| $d=\gcd(n,q)$ | máximo divisor comum entre o tempo $n$ e o período $q$ |
| $\mu(\cdot)$ | função de Möbius ($+1,-1,0$ conforme os fatores primos) |
| $\varphi(\cdot)$ | totiente de Euler |

**Por que isso é lindo:** o valor do "sinal periódico" de Ramanujan num ponto é
determinado pela **estrutura de fatores** entre $n$ e $q$ — teoria dos números
pura virando ferramenta de sinal. É o tipo de elegância nomeável que dá
identidade ao projeto (o "TDA/fractais" dos vencedores anteriores).

---

## 3. Da soma à detecção: a Transformada Periódica de Ramanujan (RPT)

Para medir **quanta** periodicidade de período $p$ existe num sinal $x$:

1. Monte o **subespaço de Ramanujan** $S_p$: gerado por $c_p(n)$ e seus
   $\varphi(p)$ deslocamentos circulares.
2. **Projete** $x$ ortogonalmente em $S_p$ e meça a energia da projeção.
3. Normalize por $\varphi(p)$ (graus de liberdade) — controla contra ruído.

$$
E_p \;=\; \frac{\big\|\,\text{proj}_{S_p}(x)\,\big\|^2}{\varphi(p)}
$$

Varrendo $p=2,3,\dots,P_{\max}$ você obtém o **espectro de Ramanujan**: um pico em
$p$ = há ciclo de período $p$. Foi exatamente isso que rodamos (§7).

**Por que melhor que Fourier (DFT) aqui:** a DFT espalha um período inteiro por
várias frequências vizinhas; o Ramanujan associa cada período a **um** subespaço
de dimensão $\varphi(p)$, então períodos inteiros (sazonalidade!) aparecem
**concentrados e limpos**, e com menos parâmetros — menos propenso a overfit.

---

## 4. O framework unificado: Nested Periodic Matrices (o "serve pra todas")

A pergunta "existe uma coisa só que serve pra todos os períodos?" tem resposta:
as **Nested Periodic Matrices (NPM)** de Tenneti & Vaidyanathan (2015). É uma
classe de matrizes que **inclui DFT, Walsh-Hadamard e a Transformada de Ramanujan
como casos particulares**, e estima o período **diretamente** (não pelo espectro).

Ideia: montar um **dicionário** $A=[\,B_2\,B_3\,\cdots\,B_{P}\,]$ onde cada bloco
$B_p$ é a base periódica do período $p$, e resolver
$$
x \approx A\,s \quad\text{com penalidade que favorece POUCOS períodos (L1/L2)}.
$$
Os blocos com energia alta revelam os períodos ocultos. **Esse é o método geral**
— o mesmo procedimento acha o ciclo de qualquer série (gasolina=12, gás=6), sem
você assumir o período. É o que separa "detecção principiada" de "dummy de
calendário chutada".

---

## 5. Por que isso vence a crítica "é só uma dummy de calendário"

Um avaliador afiado dirá: *"sazonalidade você pega com média por mês."* A
resposta — e é empírica (§7): o **gás natural não tem ciclo anual (12), tem
semestral (6)** — dois picos de demanda por ano. Uma dummy "anual" erra; a RPT
**descobre o período certo**. Diferentes ativos, diferentes períodos, e o método
acha qual é. *Aí* o Ramanujan ganha o lugar dele.

---

## 6. O que a matemática faz — e o que NÃO faz (honestidade)

| Faz | Não faz |
|---|---|
| Detecta o período dominante de forma principiada | Prever preço diretamente |
| Decompõe o sinal em componentes exatamente periódicos | Garantir que o ciclo persista no futuro |
| Funciona pra período variável no tempo (filtros de Ramanujan) | Substituir teste out-of-sample |

A estratégia nasce de uma **aposta testável**: o componente periódico detectado
no passado continua valendo. Se não continuar, é nulo honesto (o edital aceita).

---

## 7. Resultado empírico (commodities, retorno mensal)

Espectro de Ramanujan (força do período em múltiplos do ruído) + estratégia
sazonal point-in-time vs buy-and-hold:

| Commodity | Período Ramanujan | Estratégia | B&H | |
|---|---|---|---|---|
| Gasolina (RB=F) | **12m = 8,3×** (anual) | Sharpe **0,86** | 0,31 | ✅ |
| Milho (ZC=F) | 12m = 3,9× | 0,47 | 0,27 | ✅ |
| Petróleo (CL=F) | 12m = 2,0× | 0,32 | 0,24 | ✅ (fraco) |
| Gás natural (NG=F) | **6m = 5,5×** (semestral!) | 0,19 | 0,20 | ✗ regra ingênua |
| Trigo (ZW=F) | 12m = 2,6× | 0,20 | 0,26 | ✗ |

3 de 5 batem o B&H. Gasolina é a estrela. O gás natural é a **prova de conceito
do método** (período não-óbvio que a dummy erraria). *Bruto de custo, in-sample;
falta walk-forward e custos — ver próximos passos.*

---

## 8. Referências (a escada, da raiz à aplicação)

**Raiz**
- S. Ramanujan (1918), *On certain trigonometrical sums and their applications in
  the theory of numbers*, Trans. Cambridge Phil. Soc. 22(13):259–276.

**Teoria dos números (aprofundar a matemática)**
- G. H. Hardy & E. M. Wright, *An Introduction to the Theory of Numbers*, Oxford —
  cap. sobre somas de Ramanujan.
- T. M. Apostol, *Introduction to Analytic Number Theory*, Springer (~cap. 8) —
  tratamento didático de $c_q(n)$, $\mu$, $\varphi$, ortogonalidade.
- Visão rápida: [Ramanujan's sum (Wikipedia)](https://en.wikipedia.org/wiki/Ramanujan's_sum)

**Framework moderno de sinal (Caltech — Vaidyanathan/Tenneti)**
- Tenneti & Vaidyanathan (2015), *Nested Periodic Matrices and Dictionaries: New
  Signal Representations for Period Estimation*, IEEE TSP 63(14):3736–3750 —
  [PDF](http://systems.caltech.edu/dsp/astemp/astemp1.pdf). **O paper central.**
- Vaidyanathan, *Ramanujan-sum expansions for FIR sequences* —
  [PDF](https://systems.caltech.edu/dsp/PPVSquare.pdf).
- *Srinivasa Ramanujan and signal-processing problems* (visão geral) —
  [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC6939226/).
- *Ramanujan Filter Banks* (ICASSP 2015) — periodicidade que varia no tempo.

---

## 9. Para o desafio (o ponto ótimo, sem rabbit-hole)

O edital é introdutório e premia **clareza, não complexidade**. Você não precisa
da teoria analítica dos números inteira. Precisa dominar: a definição de $c_q(n)$,
a fórmula de Hölder, a intuição da decomposição em períodos, e o NPM como ideia
unificadora — e mostrar a aplicação (commodities) funcionando. Matemática bonita,
bem entendida, bem explicada > matemática exibida.
