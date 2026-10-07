# Pré-registro da camada de IA

> **Escrito e commitado ANTES de rodar o LLM uma única vez.** Não havia chave de
> API na máquina quando este documento foi redigido — o que torna o registro
> verificável pelo histórico do Git, e não uma promessa retroativa.
>
> Camada: [[camada_ia_copom]] · Disciplina que herdamos: [[busca_significancia]]

---

## Por que pré-registrar

Este projeto já rejeitou três variantes que **cruzaram p < 0,05**
(vol-targeting, risk parity, cripto). Em todos os casos a rejeição veio depois
de ver o resultado — o que funciona, mas exige disciplina para não ceder ao
número bonito.

Com a camada de IA temos uma oportunidade que não tivemos antes: **declarar as
conclusões antes de conhecer os resultados.** Se o LLM for bem, o pré-registro
mostra que não garimpamos. Se for mal, o pré-registro nos obriga a reportar.

O risco real que ele neutraliza é específico e conhecido: um LLM tem muitos
graus de liberdade (prompt, temperatura implícita, quais campos extrair, qual
campo vira sinal). Sem regra escrita antes, é fácil rodar cinco variações e
apresentar a melhor como se fosse a única.

---

## O desenho, fixado

| Item | Valor fixado | Por quê |
|---|---|---|
| Modelo | `claude-opus-5` | Melhor disponível; custo (~US$ 2) é irrelevante aqui |
| Sinal primário | campo `regime` | Já tem braço de controle construído |
| Sinal secundário | campo `vies_prospectivo` | Testa a hipótese H3 (§4) |
| Inclinação $\tau$ | **0,25** | A priori, "um quarto da exposição a risco" |
| Faixa de robustez | 0,10 a 0,50 | Reportamos todos; **não escolhemos o melhor** |
| Período | jan/2015–jul/2026, e ago/2016+ | O segundo é onde a camada atua |
| Prompt | congelado em `copom.py:INSTRUCAO` | Uma versão. Sem iterar prompt vendo resultado |

**Regra de ouro declarada:** rodamos o LLM **uma vez**, com o prompt como está.
Se mudarmos o prompt depois de ver o backtest, isso vira uma variante nova e
entra na contagem de testes múltiplos — e será reportado como tal.

---

## As hipóteses e o que concluímos em cada caso

Referência: o robô base tem **Sharpe 0,53** e o braço de controle mecânico
(direção da Selic, zero IA) tem **Sharpe 0,59**.

### H1 — A leitura do LLM bate o robô sem IA?

| Resultado | Conclusão declarada |
|---|---|
| Sharpe(LLM) > 0,53 | A camada agrega. Prosseguir para H2. |
| Sharpe(LLM) ≤ 0,53 | **A IA não agregou.** Reportar no relatório; a camada não entra na estratégia principal. |

### H2 — A leitura bate o mesmo sinal SEM IA? *(a que importa)*

A régua do LLM **não é o robô base — é o braço mecânico.** O número da Selic é
público e gratuito; se a leitura do texto não superar isso, a IA é adorno.

| Resultado | Conclusão declarada |
|---|---|
| \|Sharpe(LLM) − 0,59\| < 0,05 | **O LLM apenas reproduz o número público.** Reportar exatamente assim. A camada vira extensão documentada, não estratégia — mesmo tratamento que demos à cripto. |
| Sharpe(LLM) > 0,64 | Vantagem aparente. **Não aceitar sem passar por H3.** |
| Sharpe(LLM) < 0,54 | A leitura atrapalha. Reportar e não usar. |

### H3 — A vantagem vem da parte que o número não tem?

Esta é a defesa contra contaminação (o LLM de 2026 conhecer o desfecho de 2016).

A decisão do Copom já está na Selic. O que **só** existe no texto é a
sinalização prospectiva. Então isolamos os meses em que o `vies_prospectivo`
lido **diverge** da direção mecânica — são os meses em que a leitura carrega
informação própria.

| Resultado | Conclusão declarada |
|---|---|
| A vantagem se **concentra** nos meses de divergência | Consistente com leitura genuína do texto prospectivo. Aceitar, reportando o teste. |
| A vantagem está **espalhada uniformemente**, inclusive onde o texto concorda com o número | **Suspeito.** Se o texto diz a mesma coisa que a Selic e ainda assim o LLM ganha, o ganho não veio da leitura. Reportar como possível contaminação e **não usar como resultado principal**. |

### H4 — É alavancagem disfarçada?

Já automatizado em `rodar_ia.py` §5, mesma régua que reprovou o vol-targeting.

| Resultado | Conclusão declarada |
|---|---|
| Exposição média a risco **não sobe** | Passa. |
| Exposição sobe > 1 p.p. ou escala > 1,02× | **REPROVAR**, pelo mesmo critério do vol-targeting. Sem exceção por ser IA. |

### H5 — Quanto o LLM concorda com o número?

Diagnóstico, não critério de aceitação — mas declarado para não ser
interpretado depois:

- **Concordância ~100%:** o LLM é redundante; dizer isso claramente.
- **Concordância 60–90%:** faixa esperada; a divergência é o material de H3.
- **Concordância < 50%:** suspeitar de leitura ruim ou prompt mal calibrado, não
  comemorar como "sinal diferenciado".

---

## O que NÃO faremos

1. **Não escolher o $\tau$ que der o melhor resultado.** $\tau = 0{,}25$ está
   fixado; a varredura 0,10–0,50 é diagnóstico de robustez, não menu.
2. **Não iterar o prompt olhando o backtest.** Uma rodagem, um prompt.
3. **Não trocar o sinal primário depois de ver os números.** Se `regime` for mal
   e `vies_prospectivo` for bem, isso é resultado de H3 e será reportado como
   análise secundária — nunca apresentado como se fosse o desenho original.
4. **Não vender p < 0,05.** A camada é mais uma variante somada às 8 de
   [[busca_significancia]]; sob Bonferroni nada sobrevive. O que sustenta o
   projeto é o conjunto de robustez, não um p-valor.
5. **Não usar a camada se ela falhar em H1 ou H4.** Neste caso o relatório
   descreve a construção, o teste e o resultado negativo — que é um resultado
   legítimo e, pelo edital, não elimina ninguém.

---

## O resultado que já temos, e que não muda

O braço de controle mecânico está rodado e independe do LLM:

- Sharpe 0,53 → **0,59**; p 0,074 → **0,048**
- **2022–23: −7,1% → −5,5%** — o único subperíodo perdedor, que era o alvo
- Exposição a risco **cai** de 68,7% para 65,3% (não é alavancagem)

Ou seja: **a tese de que o regime de juros deve inclinar a alocação já está
validada sem nenhuma IA.** O que o LLM está sendo testado para fazer é uma
pergunta mais estreita e mais honesta — *ler o texto agrega sobre ler o
número?* — e temos um resultado publicável para qualquer resposta.
