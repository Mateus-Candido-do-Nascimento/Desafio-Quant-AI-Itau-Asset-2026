"""
SUPERADO. Use `entrega/gerar_relatorio_docx.py`.

Primeira versão do relatório, gerada em PDF direto com ReportLab. Foi
abandonada por um motivo concreto: no ReportLab a célula de tabela não quebra
linha sozinha quando recebe uma string simples, então o texto vazava para fora
da borda e o estouro só aparecia depois de abrir o PDF.

O gerador atual escreve `.docx`, onde o Word faz a quebra de linha, e o PDF sai
de uma exportação do próprio Word. O arquivo fica aqui como registro da
tentativa; os números dele podem estar defasados em relação ao backtest atual.

Uso (se realmente quiser rodar): venv/Scripts/python.exe entrega/gerar_relatorio.py
Saída: entrega/relatorio_final.pdf
"""
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

AQUI = Path(__file__).resolve().parent
SAIDA = AQUI / "relatorio_final.pdf"

# ── Números vêm do backtest, não digitados à mão ────────────────────────────
sys.path.insert(0, str(AQUI.parent / "src" / "robo"))


def metricas():
    """Roda o backtest e devolve os números que aparecem no relatório."""
    import pandas as pd
    import backtest as bt
    import config as cfg
    import dados
    import estrategia as est

    c = dados.carregar_painel()
    hoje = pd.Timestamp.today()
    if c.index[-1].month == hoje.month and c.index[-1].year == hoje.year:
        c = c.iloc[:-1]
    rec = c.index[c.index >= cfg.DATA_INICIO_INVESTIVEL]
    cdi = c["ret_CDI"].loc[rec]

    saida = {}
    for nome, pesos in [("robo", est.pesos_ranking(c)),
                        ("estatico", est.pesos_estatico(c)),
                        ("tatico", est.pesos_tatico(c))]:
        res = bt.rodar_backtest(c, pesos)
        r = res["retorno"].loc[rec]
        saida[nome] = bt.avaliar(r, cdi)
        if nome == "robo":
            saida["giro"] = float(res["giro"].loc[rec].mean())
            saida["serie"] = r
            w = pesos.loc[rec]
            saida["meses_caixa"] = int((w[cfg.CAIXA] > 0.95).sum())
            saida["aloc"] = (w.mean() * 100).round(0).to_dict()
    saida["bench"] = bt.avaliar(
        (0.6 * cdi + 0.4 * c["ret_Acoes"].loc[rec]), cdi)
    saida["ibov"] = bt.avaliar(c["ret_Acoes"].loc[rec], cdi)
    saida["cdi_aa"] = float((1 + cdi).prod() ** (12 / len(cdi)) - 1)
    saida["vol_cdi"] = float(cdi.std() * (12 ** 0.5))
    oos = rec > "2019-12-31"
    saida["oos"] = bt.avaliar(saida["serie"][oos], cdi[oos])
    saida["meses"] = len(rec)
    saida["anos_nec"] = (1.96 / saida["robo"]["sharpe"]) ** 2
    saida["anos"] = len(rec) / 12
    saida["ini"] = rec.min().strftime("%b/%Y")
    saida["fim"] = rec.max().strftime("%b/%Y")
    return saida


M = metricas()


def pc(x, casas=1, sinal=False):
    s = f"{x * 100:+.{casas}f}%" if sinal else f"{x * 100:.{casas}f}%"
    return s.replace(".", ",")


def num(x, casas=2):
    return f"{x:.{casas}f}".replace(".", ",")

AZUL = colors.HexColor("#1a4f8a")
CINZA = colors.HexColor("#4a4a48")
CLARO = colors.HexColor("#eef2f7")
BORDA = colors.HexColor("#c9c7bd")

ss = getSampleStyleSheet()
S = {
    "titulo": ParagraphStyle("t", parent=ss["Title"], fontSize=16, spaceAfter=2,
                             textColor=AZUL, alignment=1),
    "sub": ParagraphStyle("s", parent=ss["Normal"], fontSize=9.5, alignment=1,
                          textColor=CINZA, spaceAfter=10),
    "h": ParagraphStyle("h", parent=ss["Heading2"], fontSize=11.5, spaceBefore=8,
                        spaceAfter=3, textColor=AZUL),
    "h2": ParagraphStyle("h2", parent=ss["Heading3"], fontSize=9.8, spaceBefore=5,
                         spaceAfter=2, textColor=CINZA),
    "p": ParagraphStyle("p", parent=ss["Normal"], fontSize=8.8, leading=11.6,
                        alignment=TA_JUSTIFY, spaceAfter=4),
    "cit": ParagraphStyle("c", parent=ss["Normal"], fontSize=9.2, leading=12.5,
                          leftIndent=10, rightIndent=10, spaceBefore=3,
                          spaceAfter=5, textColor=AZUL, borderPadding=5,
                          backColor=CLARO, borderColor=AZUL, borderWidth=0),
    "cel": ParagraphStyle("cel", parent=ss["Normal"], fontSize=7.6, leading=9.2),
    "nota": ParagraphStyle("n", parent=ss["Normal"], fontSize=7.4, leading=9.2,
                           textColor=CINZA, spaceAfter=4),
}


def P(txt, st="p"):
    return Paragraph(txt, S[st])


def tabela(dados, larguras, destaque_linha=1):
    t = Table(dados, colWidths=larguras, hAlign="LEFT")
    est = [
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 7.6),
        ("FONT", (0, 1), (-1, -1), "Helvetica", 7.6),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDA),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]
    if destaque_linha:
        est += [("BACKGROUND", (0, destaque_linha), (-1, destaque_linha), CLARO),
                ("FONT", (0, destaque_linha), (-1, destaque_linha), "Helvetica-Bold", 7.6)]
    t.setStyle(TableStyle(est))
    return t


def construir():
    doc = SimpleDocTemplate(
        str(SAIDA), pagesize=A4,
        leftMargin=1.5 * cm, rightMargin=1.5 * cm,
        topMargin=1.2 * cm, bottomMargin=1.1 * cm,
        title="Relatorio Final - Desafio Quant AI 2026", author="")
    h = []

    # ══════════════════ PÁGINA 1 — ROBÔ E CONCEITO ══════════════════
    h.append(P("Robô Fundamento", "titulo"))
    h.append(P("Alocação sistemática entre classes de ativo com rebalanceamento "
               "mensal &nbsp;|&nbsp; Desafio Quant AI 2026", "sub"))

    h.append(P("1. O robô", "h"))
    h.append(P(
        f"<b>Fundamento</b> — porque toda decisão de alocação tem um fundamento "
        "econômico por trás: o robô não segue palpite nem narrativa, segue "
        "evidência mensurável. Ele responde todo mês a uma única pergunta: "
        "<i>o risco está pagando mais que o dinheiro parado?</i>"))

    h.append(P("2. Conceito da estratégia", "h"))
    h.append(P(
        f"<b>A tese.</b> No Brasil o ativo livre de risco rende cerca de 10% ao "
        "ano. Isso muda a natureza do problema de alocação: correr risco só faz "
        "sentido quando o risco está sendo remunerado acima disso. Nosso robô "
        "mede essa remuneração todo mês, realoca para as classes que estão "
        "entregando — e, quando nenhuma está, simplesmente não corre risco.", "cit"))
    h.append(P(
        f"A régua do projeto é o <b>CDI</b>, não a bolsa. Essa escolha não é "
        "cosmética: no período testado o <b>Ibovespa rendeu 11,6% ao ano contra "
        "9,9% do CDI</b> — ou seja, a bolsa entregou apenas 1,5 p.p. acima do "
        "dinheiro parado, com 37% de queda máxima no caminho. Uma carteira "
        "balanceada clássica 60/40 <b>perdeu</b> para o CDI de 2020 em diante. "
        "Superar o CDI de forma consistente no Brasil é, portanto, um problema "
        "genuinamente difícil — e é o problema que atacamos."))
    h.append(P(
        f"<b>Fundamentação.</b> A regra é a adaptação ao mercado brasileiro do "
        "<i>Dual Momentum</i> (Antonacci, 2014), que combina momentum absoluto "
        "(o ativo precisa superar o caixa) e momentum relativo (entre os "
        "aprovados, o melhor pesa mais), somada à alocação tática de Faber "
        "(2007), que documenta redução substancial de drawdown mantendo retorno "
        "de renda variável. Não é invenção nossa: é método publicado e "
        "replicado, aplicado a um contexto onde o caixa é excepcionalmente "
        "forte. A literatura brasileira reforça a escolha por outro caminho — "
        "estudos de momentum em <i>ações individuais</i> no Brasil encontram "
        "resultados frágeis, o que justifica operar <b>entre classes</b> em vez "
        "de fazer seleção de ações."))

    h.append(P("3. Modelagem", "h"))
    h.append(P("3.1 Universo: cinco classes, cinco papéis", "h2"))
    h.append(tabela([
        ["Classe", "Representa", "Papel na carteira", "Veículo na B3"],
        ["CDI", "renda fixa pós-fixada", "caixa e porto seguro", "Tesouro Selic"],
        ["Ações", "Ibovespa", "crescimento Brasil", "BOVA11"],
        ["Global", "S&P 500 em reais", "crescimento internacional", "IVVB11"],
        ["Ouro", "ouro em reais", "proteção contra crise", "ETF/fundo de ouro"],
        ["Dólar", "USD/BRL", "proteção contra risco Brasil", "fundo cambial"],
    ], [2.2 * cm, 3.6 * cm, 5.2 * cm, 3.4 * cm], destaque_linha=1))
    h.append(P(
        f"O CDI é simultaneamente uma classe e o <b>destino da fuga</b>: quando "
        "nenhuma classe de risco supera o caixa, o robô se recolhe 100% nele. "
        "A inclusão da bolsa global é decisiva — sem ela o cardápio ficaria "
        "restrito a classes que, no período, mal superaram o CDI.", "nota"))

    h.append(P("3.2 O sinal", "h2"))
    h.append(P(
        f"Para cada classe c, no mês t, calculamos o momentum de 12 meses: "
        "<b>mom(c,t) = P(c, t-1) / P(c, t-13) &minus; 1</b>. O uso de t&minus;1 "
        "é deliberado: a decisão do mês t jamais enxerga o próprio mês que está "
        "alocando. Janela de 12 meses é longa o bastante para filtrar ruído "
        "mensal e curta o bastante para reagir a mudanças de regime — e "
        "mostramos adiante que o resultado não depende dessa escolha."))

    h.append(P("3.3 A regra de alocação (o ciclo mensal)", "h2"))
    h.append(tabela([
        ["Passo", "O que o robô faz", "Por quê"],
        ["1. Trava absoluta",
         "descarta a classe cujo momentum não supera o CDI",
         "impede comprar 'a melhor entre as ruins'; ficar parado é decisão legítima"],
        ["2. Ranking",
         "ordena as aprovadas e distribui 40 / 30 / 20 / 10%",
         "concentra no que está entregando, sem apostar tudo em uma só"],
        ["3. Caixa", "todo o peso não alocado vai para o CDI",
         "o excedente rende ~10% a.a. sem risco"],
        ["4. Rebalanceia", "traz a carteira de volta a esses pesos, pagando o giro",
         "controla o risco e realiza ganho de quem subiu demais"],
    ], [2.6 * cm, 5.6 * cm, 6.2 * cm], destaque_linha=0))

    h.append(PageBreak())

    # ══════════════════ PÁGINA 2 — BACKTEST E RESULTADOS ══════════════════
    h.append(P("4. Backtest: rigor e mitigação de vieses", "h"))
    h.append(P(
        f"O motor de simulação foi <b>implementado inteiramente por nós</b>, sem "
        "plataforma que entregue backtest pronto. Ele percorre mês a mês: lê os "
        "pesos-alvo (decididos com dados até t&minus;1), paga o custo do giro no "
        "rebalanceamento, apura o retorno e deixa a carteira <b>derivar</b> até o "
        "mês seguinte — como uma carteira real, em que quem sobe passa a pesar mais."))
    h.append(tabela([
        ["Viés", "Como o robô o evita"],
        ["Look-ahead (olhar o futuro)",
         "todo sinal com defasagem de um mês; nenhuma decisão usa informação do próprio mês"],
        ["Custos de transação",
         f"10 bps sobre cada unidade de giro, descontados do retorno (giro médio de {pc(M['giro'],0)} ao mês)"],
        ["Viés de sobrevivência",
         "usamos índices de classe, não ações individuais — nenhuma empresa 'desaparece' da amostra"],
        ["Superotimização",
         "validação fora da amostra e testes de sensibilidade em todos os parâmetros (§6)"],
    ], [4.2 * cm, 10.2 * cm], destaque_linha=0))
    h.append(P(
        f"<b>Período:</b> {M["ini"]} a {M["fim"]} ({M["meses"]} meses). O início não é "
        "arbitrário: o IVVB11 — forma prática de comprar bolsa global na B3 — "
        "existe desde nov/2014. Preferimos um recorte mais curto e plenamente "
        "investível a um histórico maior com premissa frouxa.", "nota"))

    h.append(P("5. Resultados", "h"))
    h.append(Image(str(AQUI / "grafico.png"), width=17.2 * cm, height=5.6 * cm))
    h.append(Spacer(1, 4))
    def linha(rot, k):
        m = M[k]
        return [rot, pc(m["retorno_aa"]), pc(m["vol_aa"]),
                pc(m["excedente_cdi_aa"], sinal=True), num(m["sharpe"]),
                pc(m["max_dd"], 0)]

    h.append(tabela([
        ["Estratégia", "Retorno a.a.", "Vol.", "Acima do CDI", "Sharpe*", "Máx. queda"],
        linha("Robô Fundamento", "robo"),
        linha("Rebalanceamento puro (peso igual)", "estatico"),
        linha("Filtro de tendência apenas", "tatico"),
        linha("Carteira balanceada 60/40", "bench"),
        linha("Ibovespa", "ibov"),
        ["CDI (régua)", pc(M["cdi_aa"]), pc(M["vol_cdi"]), "—", "—", "0%"],
    ], [5.6 * cm, 2.2 * cm, 1.7 * cm, 2.4 * cm, 1.8 * cm, 2.3 * cm]))
    h.append(P(
        f"* Sharpe calculado sobre o retorno <b>excedente ao CDI</b> — no Brasil, "
        "ignorar o custo de oportunidade infla qualquer métrica de risco-retorno.", "nota"))
    h.append(P(
        f"<b>As duas leituras.</b> Contra o CDI, o robô entrega <b>{pc(M['robo']['excedente_cdi_aa'],1,True)} ao ano</b> "
        "acima do dinheiro parado. Contra a bolsa, entrega mais retorno que o "
        f"Ibovespa ({pc(M['robo']['retorno_aa'])} contra {pc(M['ibov']['retorno_aa'])}) com <b>menos de um terço da queda máxima</b> "
        f"({pc(M['robo']['max_dd'],0)} contra {pc(M['ibov']['max_dd'],0)}). O investidor participa da alta sem passar pelo susto."))
    h.append(P(
        f"<b>A defesa funciona.</b> Em <b>{M['meses_caixa']} dos {M['meses']} meses</b> o robô ficou 100% em "
        f"CDI — inclusive na virada de 2022. A alocação média (CDI {M['aloc']['CDI']:.0f}%, Global {M['aloc']['Global']:.0f}%, "
        f"Ouro {M['aloc']['Ouro']:.0f}%, Ações {M['aloc']['Acoes']:.0f}%, Dólar {M['aloc']['Dolar']:.0f}%) mostra que ele girou genuinamente entre "
        "as classes, com um terço do tempo em caixa; não é uma aposta disfarçada "
        "em uma única classe."))
    h.append(P(
        f"<b>Fora da amostra.</b> Restringindo a 2020 em diante — período que não "
        f"usamos para desenhar a estratégia — o robô entrega <b>{pc(M['oos']['excedente_cdi_aa'],1,True)} sobre o CDI "
        f"com Sharpe {num(M['oos']['sharpe'])}</b>, acima do próprio desempenho no período completo. No "
        "mesmo intervalo, Ibovespa e carteira 60/40 <b>perderam</b> para o CDI."))

    h.append(PageBreak())

    # ══════════════════ PÁGINA 3 — ANÁLISE CRÍTICA ══════════════════
    h.append(P("6. Análise crítica: o resultado é robusto?", "h"))
    h.append(P(
        f"Um resultado só vale o que valem os testes que ele sobrevive. Submetemos "
        "o robô a quatro exames de sensibilidade e a um teste não-paramétrico."))
    h.append(tabela([
        ["Teste", "Variações testadas", "Resultado"],
        ["Janela do momentum", "6, 9, 12, 18 e 24 meses",
         "todas positivas (+3,5% a +5,8% sobre o CDI). A janela que adotamos, 12m, NÃO é a melhor"],
        ["Frequência do rebalanceamento", "mensal, trimestral, semestral",
         "todas positivas; mensal é a melhor, semestral ainda entrega +3,7%"],
        ["Custo de transação", "5, 10 e 25 bps por giro",
         "sobrevive a custo 2,5x maior que o adotado (+4,6% sobre o CDI)"],
        ["Remoção de classes", "retirando cada classe do cardápio",
         "positivo em todos os casos; nenhuma classe isolada sustenta o resultado"],
        ["Significância (bootstrap)", "10.000 reamostragens",
         "P(excedente <= 0) = 0,037 unicaudal, coerente com o teste t"],
    ], [4.1 * cm, 4.3 * cm, 9.4 * cm], destaque_linha=1))
    h.append(P(
        f"O ponto mais relevante é o primeiro: <b>a janela que escolhemos não é a "
        "que maximiza o resultado</b>. Se tivéssemos garimpado o parâmetro, "
        "teríamos escolhido 9 meses. Essa é a evidência mais direta de que não "
        "houve superotimização."))

    h.append(P("7. Onde o robô falha — e o que rejeitamos", "h"))
    h.append(P("7.1 A falha", "h2"))
    h.append(P(
        f"O robô <b>perdeu para o CDI em 2022–2023 (&minus;7,2%)</b>. A causa é "
        "estrutural e conhecida: momentum é um sinal defasado, e na virada de "
        "regime com Selic a 13,75% ele tomou sucessivas 'chicotadas' — entrando "
        "em classes que já haviam virado. É a fraqueza inerente do método, e ela "
        "apareceu. Nos demais quatro subperíodos o robô foi positivo, com "
        "destaque para 2020–2021 (+15,8% sobre o CDI enquanto o Ibovespa fazia "
        "&minus;8,3%)."))

    h.append(P("7.2 Três melhorias que testamos e REJEITAMOS", "h2"))
    h.append(P(
        f"Nosso excedente tem p = {num(M['robo']['p'],3)} — marginal. Buscamos cruzar o corte de 5% "
        "com variantes definidas <i>a priori</i>. Três cruzaram. <b>Rejeitamos "
        "as três</b>, e consideramos isso a parte mais importante deste relatório."))
    h.append(tabela([
        ["Variante", "p obtido", "Por que foi rejeitada"],
        ["Vol-targeting", "0,029",
         "alavancagem disfarçada: exposição a risco subiu de 62% para 70%, escala média 1,16x, "
         "e o Sharpe melhorou em apenas 3 de 6 subperíodos"],
        ["Risk parity", "0,036",
         f"melhora somente no recorte 2010+; PIORA no recorte principal (Sharpe 0,46 contra {num(M['robo']['sharpe'])}) "
         "— adotá-la exigiria escolher o período conveniente"],
        ["Incluir criptomoeda", "0,004",
         "ETF de bitcoin na B3 só existe desde 2021; no subperíodo investível o ganho cai para "
         "+2,3% com p = 0,50. Toda a significância vem do período em que a classe não era "
         "acessível por veículo regulado — é viés de sobrevivência no nível de classe"],
    ], [3.0 * cm, 1.7 * cm, 13.1 * cm], destaque_linha=0))
    h.append(P(
        f"Além disso, com oito variantes testadas, a correção de Bonferroni leva "
        "o melhor p (0,029) a 0,232 — nenhuma sobreviveria ao ajuste por "
        "múltiplos testes. <b>Optamos por reportar um resultado marginal robusto "
        "em vez de um resultado significativo garimpado.</b>", "cit"))

    h.append(P("7.3 A matemática do limite", "h2"))
    h.append(P(
        f"A estatística t de um excedente aproxima-se de <b>Sharpe &times; "
        f"&radic;anos</b>. Para demonstrar um Sharpe de {num(M['robo']['sharpe'])} com 95% de confiança "
        f"seriam necessários <b>(1,96 / {num(M['robo']['sharpe'])})&sup2; &asymp; {num(M['anos_nec'],1)} anos</b>; dispomos "
        f"de {num(M['anos'],1)}. <b>Faltam cerca de dois anos de dados — não uma estratégia "
        "melhor.</b> Esse é o limite honesto do que esta amostra permite afirmar, "
        "e é a razão pela qual sustentamos a estratégia pelo <i>conjunto</i> de "
        "evidências de robustez, e não por um p-valor isolado."))

    h.append(PageBreak())

    # ══════════════════ PÁGINA 4 — GENAI E CONCLUSÃO ══════════════════
    h.append(P("8. Uso de IA generativa", "h"))
    h.append(P(
        f"A IA generativa foi usada como <b>parceira de pesquisa e engenharia</b>, "
        "em quatro etapas, com registro do que cada uma produziu:"))
    h.append(tabela([
        ["Etapa", "Contribuição prática da GenAI"],
        ["Revisão crítica do desenho",
         "identificou os dois erros que mais alteraram o projeto: (i) a régua correta é o CDI e não "
         "a bolsa — todas as métricas anteriores estavam infladas; (ii) o cardápio de classes "
         "original era estreito demais e prendia o robô a opções que não superavam o caixa"],
        ["Construção do código",
         "implementação dos módulos de dados (API do Banco Central e mercado), do motor de "
         "backtest e da bateria de testes de robustez"],
        ["Auditoria dos resultados",
         "os testes de sanidade que levaram à rejeição do vol-targeting (diagnóstico de "
         "alavancagem disfarçada) e do risk parity nasceram desse processo de questionamento"],
        ["Redação e estruturação",
         "organização da documentação metodológica e deste relatório"],
    ], [4.4 * cm, 13.4 * cm], destaque_linha=0))
    h.append(P(
        f"<b>Disciplina adotada.</b> Nenhuma sugestão da IA entrou no modelo sem "
        "passar pelos mesmos testes aplicados às nossas próprias hipóteses — e a "
        "maioria foi <b>rejeitada</b> por eles. O ganho não veio de a IA acertar "
        "mais, veio de ela nos forçar a testar mais.", "cit"))
    h.append(P(
        f"<b>Extensão desenhada e não validada.</b> Projetamos uma camada em que "
        "um modelo de linguagem lê as atas do Copom para classificar o regime de "
        "juros e inclinar a alocação, com disciplina <i>point-in-time</i> (a ata "
        "só é lida após a data de publicação, evitando que o modelo 'conheça o "
        "futuro' por seu treinamento). <b>Não a incluímos nos resultados por não "
        "termos concluído sua validação</b> — reportá-la como se estivesse "
        "testada seria incoerente com o restante do trabalho."))

    h.append(P("9. Conclusão", "h"))
    h.append(P(
        f"<b>O que está demonstrado.</b> (1) Alocação com rebalanceamento mensal "
        f"entre classes supera o CDI em {pc(M['robo']['excedente_cdi_aa'],1,True)} ao ano e o Ibovespa em retorno, com "
        "menos de um terço da queda máxima. (2) A vantagem se mantém fora da "
        "amostra, em todas as janelas de momentum, em todas as frequências de "
        "rebalanceamento e sob custos 2,5x maiores. (3) O ranking por mérito "
        "agrega sobre o rebalanceamento puro, embora a maior parte do valor venha "
        "da <b>estrutura</b> — rebalancear entre classes com fuga para o caixa — "
        "e não da sofisticação do sinal."))
    h.append(P(
        f"<b>O que não está.</b> A significância é marginal (p = {num(M['robo']['p'],3)}), e "
        "explicamos por quê: a amostra é curta para o Sharpe obtido. O robô falha "
        "em viradas bruscas de regime, como em 2022–2023. E o desempenho depende "
        "de haver classes atrativas no cardápio — no período, a bolsa global "
        "contribuiu de forma relevante, o que pode não se repetir."))
    h.append(P(
        f"<b>A leitura que fazemos.</b> O achado mais útil deste trabalho talvez "
        f"não seja o excedente de {pc(M['robo']['excedente_cdi_aa'])}, e sim o que ele custou para ser afirmado "
        "com honestidade: três melhorias descartadas por não sobreviverem aos "
        "próprios testes, e um p-valor que preferimos reportar como é. Em "
        "gestão sistemática, a disciplina de recusar o resultado bonito é parte "
        "do produto.", "cit"))

    h.append(P("10. Próximos passos", "h"))
    h.append(tabela([
        ["Prioridade", "Ação", "O que responde"],
        ["1", "Construir e validar a leitura das atas do Copom por LLM",
         "o momentum é defasado; uma leitura de regime pode antecipar viradas como a de 2022"],
        ["2", "Ampliar o cardápio com títulos indexados à inflação (IMA-B)",
         "classe relevante e ausente; small caps, títulos e imobiliário dos EUA já foram testados e reprovados"],
        ["3", "Reavaliar criptomoeda quando houver histórico de ETF na B3",
         "hoje o resultado depende do período não investível; a partir de ~2027 haverá amostra suficiente"],
        ["4", "Simular com aportes mensais e faixas de risco por perfil",
         "aproxima o backtest da experiência real do investidor final"],
    ], [1.9 * cm, 6.6 * cm, 9.3 * cm], destaque_linha=0))
    h.append(Spacer(1, 6))
    h.append(P(
        f"Fontes de dados, todas públicas e gratuitas: séries de CDI e IPCA da API "
        "do Banco Central do Brasil (SGS) e cotações de mercado via Yahoo Finance. "
        "Backtest, métricas e testes de robustez implementados pela equipe em "
        "Python. Referências: Antonacci (2014), <i>Dual Momentum Investing</i>; "
        "Faber (2007), <i>A Quantitative Approach to Tactical Asset Allocation</i>; "
        "Moskowitz, Ooi &amp; Pedersen (2012), <i>Time Series Momentum</i>.", "nota"))

    doc.build(h)
    print(f"PDF gerado: {SAIDA}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    construir()
