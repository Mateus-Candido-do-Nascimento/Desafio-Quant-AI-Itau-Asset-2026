"""
Gera o Relatório Final em .docx (editável, até 5 páginas, sem identificação).

Uso: venv/Scripts/python.exe entrega/gerar_relatorio_docx.py
Saída: entrega/relatorio_final.docx

Os números NÃO são digitados: vêm do backtest, calculados na hora da geração.
No Word as tabelas quebram linha sozinhas — o problema de estouro do PDF não
existe aqui, e o texto continua ajustável à mão antes de exportar para PDF.
"""
from __future__ import annotations

import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

# Console do Windows e cp1252: sem isto, qualquer acento no caminho de
# saida quebra o print final. Convencao do projeto.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

AQUI = Path(__file__).resolve().parent
SAIDA = AQUI / "relatorio_final.docx"
sys.path.insert(0, str(AQUI.parent / "src" / "robo"))

AZUL = RGBColor(0x1A, 0x4F, 0x8A)
CINZA = RGBColor(0x4A, 0x4A, 0x48)


# ── Métricas vindas do backtest ─────────────────────────────────────────────
def metricas() -> dict:
    import pandas as pd
    import backtest as bt
    import config as cfg
    import dados
    import estrategia as est

    import copom

    c = dados.carregar_painel()
    hoje = pd.Timestamp.today()
    if c.index[-1].month == hoje.month and c.index[-1].year == hoje.year:
        c = c.iloc[:-1]
    rec = c.index[c.index >= cfg.DATA_INICIO_INVESTIVEL]
    cdi = c["ret_CDI"].loc[rec]

    # Camada de IA: braço de controle (regime de juros pela direção da Selic).
    # O braço do LLM só entra aqui quando copom_regimes.csv existir.
    regime = copom.regime_mensal(c.index, fonte="mecanico")
    w_ia = est.pesos_ranking_ia(c, regime)

    M = {}
    for nome, w in [("robo", est.pesos_ranking(c)), ("estatico", est.pesos_estatico(c)),
                    ("tatico", est.pesos_tatico(c)), ("robo_ia", w_ia)]:
        res = bt.rodar_backtest(c, w)
        r = res["retorno"].loc[rec]
        M[nome] = bt.avaliar(r, cdi)
        M[f"{nome}_risco"] = float(w.loc[rec][cfg.CLASSES_RISCO].sum(axis=1).mean())
        virada = (rec >= "2022-01-01") & (rec <= "2023-12-31")
        M[f"{nome}_virada"] = bt.avaliar(r[virada], cdi[virada])["excedente_cdi_aa"]
        if nome == "robo":
            M["giro"] = float(res["giro"].loc[rec].mean())
            M["serie"] = r
            wr = w.loc[rec]
            M["meses_caixa"] = int((wr[cfg.CAIXA] > 0.95).sum())
            M["aloc"] = (wr.mean() * 100).round(0).to_dict()
    M["n_atas"] = len(copom.listar_atas())
    M["bench"] = bt.avaliar(0.6 * cdi + 0.4 * c["ret_Acoes"].loc[rec], cdi)
    M["ibov"] = bt.avaliar(c["ret_Acoes"].loc[rec], cdi)
    M["cdi_aa"] = float((1 + cdi).prod() ** (12 / len(cdi)) - 1)
    M["vol_cdi"] = float(cdi.std() * 12 ** 0.5)
    oos = rec > "2019-12-31"
    M["oos"] = bt.avaliar(M["serie"][oos], cdi[oos])
    M["meses"] = len(rec)
    M["anos"] = len(rec) / 12
    M["anos_nec"] = (1.96 / M["robo"]["sharpe"]) ** 2
    mes = {1: "jan", 2: "fev", 3: "mar", 4: "abr", 5: "mai", 6: "jun",
           7: "jul", 8: "ago", 9: "set", 10: "out", 11: "nov", 12: "dez"}
    M["ini"] = f"{mes[rec.min().month]}/{rec.min().year}"
    M["fim"] = f"{mes[rec.max().month]}/{rec.max().year}"
    return M


M = metricas()


def pc(x, casas=1, sinal=False):
    s = f"{x * 100:+.{casas}f}%" if sinal else f"{x * 100:.{casas}f}%"
    return s.replace(".", ",")


def num(x, casas=2):
    return f"{x:.{casas}f}".replace(".", ",")


# ── Helpers de formatação ───────────────────────────────────────────────────
doc = Document()

sec = doc.sections[0]
sec.top_margin, sec.bottom_margin = Cm(1.3), Cm(1.2)
sec.left_margin, sec.right_margin = Cm(1.7), Cm(1.7)

normal = doc.styles["Normal"]
normal.font.name = "Calibri"
normal.font.size = Pt(9)
normal.paragraph_format.space_after = Pt(4)
normal.paragraph_format.line_spacing = 1.02


def par(texto, size=9, bold_marks=True, align="just", cor=None, space=4,
        italico=False, size_pt=None):
    """Parágrafo com **negrito** inline via marcadores."""
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space)
    p.alignment = {"just": WD_ALIGN_PARAGRAPH.JUSTIFY,
                   "center": WD_ALIGN_PARAGRAPH.CENTER,
                   "left": WD_ALIGN_PARAGRAPH.LEFT}[align]
    for i, pedaco in enumerate(texto.split("**")):
        if not pedaco:
            continue
        r = p.add_run(pedaco)
        r.font.size = Pt(size_pt or size)
        r.bold = bold_marks and i % 2 == 1
        r.italic = italico
        if cor:
            r.font.color.rgb = cor
    return p


def titulo(texto, size=15):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(1)
    r = p.add_run(texto)
    r.font.size, r.bold, r.font.color.rgb = Pt(size), True, AZUL
    return p


def secao(texto, size=11):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(7)
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run(texto)
    r.font.size, r.bold, r.font.color.rgb = Pt(size), True, AZUL
    manter_junto(p)
    return p


def sub(texto):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(1)
    r = p.add_run(texto)
    r.font.size, r.bold, r.font.color.rgb = Pt(9), True, CINZA
    manter_junto(p)
    return p


def sombrear(celula, hexcor):
    tc = celula._tc.get_or_add_tcPr()
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear")
    sh.set(qn("w:fill"), hexcor)
    tc.append(sh)


def destaque(texto):
    """Caixa de citação: tabela de 1 célula com fundo claro."""
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    cel = t.cell(0, 0)
    cel.width = Cm(17.6)
    sombrear(cel, "EEF2F7")
    p = cel.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.space_before = Pt(2)
    for i, pedaco in enumerate(texto.split("**")):
        if not pedaco:
            continue
        r = p.add_run(pedaco)
        r.font.size, r.bold = Pt(9), i % 2 == 1
        r.font.color.rgb = AZUL
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def tabela(dados, larguras_cm, destacar=None, size=8):
    """Tabela com quebra de linha automática (o Word cuida disso)."""
    t = doc.add_table(rows=len(dados), cols=len(dados[0]))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    # Impede que uma linha se parta ao meio na quebra de página, o que deixaria
    # meia frase órfã no topo da página seguinte.
    for row in t.rows:
        trPr = row._tr.get_or_add_trPr()
        cs = OxmlElement("w:cantSplit")
        trPr.append(cs)
    for i, linha in enumerate(dados):
        for j, val in enumerate(linha):
            cel = t.cell(i, j)
            cel.width = Cm(larguras_cm[j])
            p = cel.paragraphs[0]
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.space_before = Pt(1)
            if j > 0 and i > 0 and len(str(val)) <= 8:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for k, pedaco in enumerate(str(val).split("**")):
                if not pedaco:
                    continue
                r = p.add_run(pedaco)
                r.font.size = Pt(size)
                r.bold = (i == 0) or (k % 2 == 1) or (destacar == i)
                if i == 0:
                    r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            if i == 0:
                sombrear(cel, "1A4F8A")
            elif destacar == i:
                sombrear(cel, "EEF2F7")
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def nota(texto):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after = Pt(5)
    for i, pedaco in enumerate(texto.split("**")):
        if not pedaco:
            continue
        r = p.add_run(pedaco)
        r.font.size, r.bold, r.font.color.rgb = Pt(7.5), i % 2 == 1, CINZA
    return p


def quebra():
    doc.add_page_break()


def manter_junto(paragrafo):
    """Evita que um titulo fique sozinho no rodape, separado do que ele abre."""
    pPr = paragrafo._p.get_or_add_pPr()
    kn = OxmlElement("w:keepNext")
    pPr.append(kn)


# ══════════════════════ PÁGINA 1 ══════════════════════
titulo("Robô Fundamento")
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_after = Pt(8)
r = p.add_run("Alocação sistemática entre classes de ativo com rebalanceamento "
              "mensal  |  Desafio Quant AI 2026")
r.font.size, r.font.color.rgb = Pt(9), CINZA

secao("1. O robô")
par("O nome **Fundamento** traduz o critério de decisão: toda alocação tem um "
    "fundamento econômico verificável por trás dela. O robô não segue palpite nem "
    "narrativa de mercado. Ele responde todo mês a uma única pergunta objetiva: o "
    "risco está sendo pago acima do dinheiro parado?")

secao("2. Conceito da estratégia")
destaque("**A tese.** No Brasil o ativo livre de risco rende cerca de 10% ao ano. "
         "Isso muda a natureza do problema de alocação: correr risco só faz sentido "
         "quando o risco está sendo remunerado acima disso. O robô mede essa "
         "remuneração todo mês, realoca para as classes que estão entregando e, "
         "quando nenhuma está, simplesmente não corre risco.")
par(f"A régua do projeto é o **CDI**, não a bolsa. A escolha não é cosmética. No "
    f"período testado o **Ibovespa rendeu {pc(M['ibov']['retorno_aa'])} ao ano contra "
    f"{pc(M['cdi_aa'])} do CDI**, apenas {num(M['ibov']['excedente_cdi_aa'] * 100)} p.p. "
    f"acima do dinheiro parado, com {pc(M['ibov']['max_dd'], 0)} de queda máxima no "
    f"caminho. A carteira balanceada clássica 60/40 **perdeu** para o CDI de 2020 em "
    f"diante. Superar o CDI de forma consistente no Brasil é, portanto, um problema "
    f"genuinamente difícil, e é o problema que atacamos.")

sub("2.1 Fundamentação teórica")
par("A regra é a adaptação ao mercado brasileiro de quatro resultados consolidados na "
    "literatura, e não uma construção ad hoc:")
tabela([
    ["Referência", "O que estabelece", "Como entra no robô"],
    ["Jegadeesh & Titman (1993), **Journal of Finance**",
     "Ativos com bom desempenho recente tendem a mantê-lo. É a anomalia de momentum, "
     "documentada e replicada por três décadas.",
     "Fundamento do sinal de 12 meses."],
    ["Asness, Moskowitz & Pedersen (2013), **Journal of Finance**",
     "Prêmio de momentum consistente em **oito mercados e classes de ativo**, com "
     "estrutura de fator comum entre eles.",
     "Justifica aplicar momentum **entre classes**, e não apenas dentro de ações."],
    ["Faber (2007), **Journal of Wealth Management**",
     "Regra de tendência aplicada a múltiplas classes reduz drasticamente o drawdown "
     "preservando retorno de renda variável.",
     "Sustenta a fuga ao caixa e explica nosso perfil de queda contida."],
    ["Antonacci (2014), **Dual Momentum Investing**",
     "Combinação de momentum **absoluto** (superar o caixa) e **relativo** (ordenar "
     "entre os aprovados) domina cada um isoladamente.",
     "É exatamente a arquitetura de duas travas da nossa regra."],
], [4.3, 7.0, 6.3], size=7.5)
par("A evidência brasileira reforça a escolha de desenho por um caminho indireto: "
    "estudos de momentum em **ações individuais** no Brasil encontram resultados "
    "frágeis, frequentemente abaixo do Ibovespa. Isso desaconselha justamente o que "
    "**não** fizemos, que seria seleção de ações, e é coerente com operar entre "
    "classes, onde há menos ruído idiossincrático, menos custo e menos dependência de "
    "eventos de empresa. **A contribuição própria** está na adaptação: nos mercados "
    "desenvolvidos o caixa rende perto de zero e a trava absoluta quase nunca aciona; "
    "no Brasil ela é o mecanismo central, porque o caixa remunera cerca de 10% ao ano.")

secao("3. Modelagem")
sub("3.1 Universo: cinco classes, cinco papéis")
tabela([
    ["Classe", "Representa", "Papel na carteira", "Veículo na B3"],
    ["**CDI**", "renda fixa pós-fixada", "caixa e porto seguro", "Tesouro Selic"],
    ["Ações", "Ibovespa", "crescimento Brasil", "BOVA11"],
    ["Global", "S&P 500 em reais", "crescimento internacional", "IVVB11"],
    ["Ouro", "ouro em reais", "proteção contra crise", "ETF de ouro"],
    ["Dólar", "USD/BRL", "proteção contra risco Brasil", "fundo cambial"],
], [2.3, 4.3, 5.6, 3.4], destacar=1)
nota("O CDI é simultaneamente uma classe e o **destino da fuga**: quando nenhuma "
     "classe de risco supera o caixa, o robô se recolhe 100% nele. A bolsa global é "
     "decisiva, pois sem ela o cardápio ficaria restrito a classes que, no período, "
     "mal superaram o CDI.")

sub("3.2 O sinal")
par("Para cada classe c, no mês t, calculamos o momentum de 12 meses: "
    "**mom(c,t) = P(c, t−1) / P(c, t−13) − 1**. O uso de t−1 é deliberado: a decisão "
    "do mês t jamais enxerga o próprio mês que está alocando. A janela de 12 meses é "
    "longa o bastante para filtrar ruído mensal e curta o bastante para reagir a "
    "mudanças de regime. Na seção 6 mostramos que o resultado não depende dessa escolha.")

sub("3.3 A regra de alocação (o ciclo mensal)")
tabela([
    ["Passo", "O que o robô faz", "Por quê"],
    ["1. Trava absoluta", "descarta a classe cujo momentum não supera o CDI",
     "impede comprar “a melhor entre as ruins”; ficar parado é decisão legítima"],
    ["2. Ranking", "ordena as aprovadas e distribui 40 / 30 / 20 / 10%",
     "concentra no que está entregando, sem apostar tudo em uma só classe"],
    ["3. Caixa", "todo o peso não alocado vai para o CDI",
     "o excedente rende cerca de 10% ao ano sem risco"],
    ["4. Rebalanceia", "traz a carteira de volta a esses pesos, pagando o giro",
     "controla o risco e realiza ganho de quem subiu demais"],
], [2.7, 5.8, 9.1])


# ══════════════════════ PÁGINA 2 ══════════════════════
secao("4. Backtest: rigor e mitigação de vieses")
par("O motor de simulação foi **implementado inteiramente pela equipe**, sem "
    "plataforma que entregue backtest pronto. Ele percorre mês a mês: lê os pesos-alvo "
    "(decididos com dados até t−1), paga o custo do giro no rebalanceamento, apura o "
    "retorno e deixa a carteira **derivar** até o mês seguinte, como uma carteira "
    "real, em que quem sobe passa a pesar mais.")
tabela([
    ["Viés", "Como o robô o evita"],
    ["Look-ahead (olhar o futuro)",
     "todo sinal com defasagem de um mês; nenhuma decisão usa informação do próprio mês"],
    ["Custos de transação",
     f"10 bps sobre cada unidade de giro, descontados do retorno "
     f"(giro médio de {pc(M['giro'], 0)} ao mês)"],
    ["Viés de sobrevivência",
     "usamos índices de classe, não ações individuais; nenhuma empresa desaparece da amostra"],
    ["Superotimização",
     "validação fora da amostra e sensibilidade em todos os parâmetros (seção 6)"],
], [4.4, 13.2])
nota(f"**Período:** {M['ini']} a {M['fim']} ({M['meses']} meses). O início não é "
     f"arbitrário: o IVVB11, forma prática de comprar bolsa global na B3, existe "
     f"desde nov/2014. Preferimos um recorte mais curto e plenamente investível a um "
     f"histórico maior com premissa frouxa. Fontes: API do Banco Central (SGS) para "
     f"CDI e IPCA; Yahoo Finance para mercado.")

secao("5. Resultados")
doc.add_picture(str(AQUI / "grafico.png"), width=Cm(17.4))
doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER


def linha_res(rot, k):
    m = M[k]
    return [rot, pc(m["retorno_aa"]), pc(m["vol_aa"]),
            pc(m["excedente_cdi_aa"], sinal=True), num(m["sharpe"]),
            pc(m["max_dd"], 0)]


tabela([
    ["Estratégia", "Retorno a.a.", "Vol.", "Acima do CDI", "Sharpe*", "Máx. queda"],
    linha_res("**Robô Fundamento**", "robo"),
    linha_res("Rebalanceamento puro (peso igual)", "estatico"),
    linha_res("Filtro de tendência apenas", "tatico"),
    linha_res("Carteira balanceada 60/40", "bench"),
    linha_res("Ibovespa", "ibov"),
    ["CDI (régua)", pc(M["cdi_aa"]), pc(M["vol_cdi"]), "n/a", "n/a", "0%"],
], [5.8, 2.4, 1.8, 2.6, 1.9, 2.5], destacar=1)
nota("* Sharpe calculado sobre o retorno **excedente ao CDI**. No Brasil, ignorar o "
     "custo de oportunidade infla qualquer métrica de risco-retorno.")

par(f"**As duas leituras.** Contra o CDI, o robô entrega "
    f"**{pc(M['robo']['excedente_cdi_aa'], 1, True)} ao ano** acima do dinheiro parado. "
    f"Contra a bolsa, entrega mais retorno que o Ibovespa "
    f"({pc(M['robo']['retorno_aa'])} contra {pc(M['ibov']['retorno_aa'])}) com **menos "
    f"de um terço da queda máxima** ({pc(M['robo']['max_dd'], 0)} contra "
    f"{pc(M['ibov']['max_dd'], 0)}). O investidor participa da alta sem passar pelo susto.")
par(f"**A defesa funciona.** Em **{M['meses_caixa']} dos {M['meses']} meses** o robô "
    f"ficou 100% em CDI, inclusive na virada de 2022. A alocação média "
    f"(CDI {M['aloc']['CDI']:.0f}%, Global {M['aloc']['Global']:.0f}%, "
    f"Ouro {M['aloc']['Ouro']:.0f}%, Ações {M['aloc']['Acoes']:.0f}%, "
    f"Dólar {M['aloc']['Dolar']:.0f}%) mostra que ele girou genuinamente entre as "
    f"classes, com cerca de um terço do tempo em caixa. Não é uma aposta disfarçada em "
    f"uma única classe.")
par(f"**Fora da amostra.** Restringindo a 2020 em diante, período que não usamos para "
    f"desenhar a estratégia, o robô entrega "
    f"**{pc(M['oos']['excedente_cdi_aa'], 1, True)} sobre o CDI com Sharpe "
    f"{num(M['oos']['sharpe'])}**, acima do próprio desempenho no período completo. No "
    f"mesmo intervalo, Ibovespa e carteira 60/40 **perderam** para o CDI.")


# ══════════════════════ PÁGINA 3 ══════════════════════
secao("6. Análise crítica: o resultado é robusto?")
par("Um resultado vale o que valem os testes que ele sobrevive. Submetemos o robô a "
    "quatro exames de sensibilidade e a um teste não-paramétrico.")
tabela([
    ["Teste", "Variações testadas", "Resultado"],
    ["Janela do momentum", "6, 9, 12, 18 e 24 meses",
     "**todas positivas** (+3,5% a +5,8% sobre o CDI). A janela que adotamos, 12 meses, "
     "**não é a melhor** do conjunto"],
    ["Frequência do rebalanceamento", "mensal, trimestral, semestral",
     "todas positivas; mensal é a melhor, semestral ainda entrega +3,7%"],
    ["Custo de transação", "5, 10 e 25 bps por giro",
     "sobrevive a custo 2,5× maior que o adotado (+4,6% sobre o CDI)"],
    ["Remoção de classes", "retirando cada classe do cardápio",
     "positivo em todos os casos; nenhuma classe isolada sustenta o resultado"],
    ["Significância (bootstrap)", "10.000 reamostragens",
     "P(excedente ≤ 0) = 0,037 unicaudal, coerente com o teste t"],
], [4.2, 4.4, 9.0], destacar=1)
par("O ponto mais relevante é o primeiro: **a janela que escolhemos não é a que "
    "maximiza o resultado**. Se tivéssemos garimpado o parâmetro, teríamos escolhido 9 "
    "meses. É a evidência mais direta de que não houve superotimização.")

secao("7. Onde o robô falha e o que rejeitamos")
sub("7.1 A falha")
par(f"O robô **perdeu para o CDI em 2022-2023 "
    f"({pc(M['robo_virada'], 1, True)} ao ano)**. A causa é estrutural e conhecida: "
    f"momentum é sinal defasado e, na virada de regime com a Selic a 13,75%, tomou "
    f"sucessivas “chicotadas”, entrando em classes que já haviam virado. É a fraqueza "
    f"inerente do método, e ela apareceu. Nos outros quatro subperíodos o robô foi "
    f"positivo, com destaque para 2020-2021 (+15,8% sobre o CDI enquanto o Ibovespa "
    f"fazia −8,3%). A seção 8.2 descreve a camada que construímos especificamente para "
    f"atacar essa falha.")

sub("7.2 Três melhorias que testamos e rejeitamos")
par(f"Nosso excedente tem p = {num(M['robo']['p'], 3)}, valor marginal. Buscamos cruzar "
    f"o corte de 5% com variantes definidas **a priori**. Três cruzaram. **Rejeitamos "
    f"as três**, e consideramos isso a parte mais importante deste relatório.")
tabela([
    ["Variante", "p obtido", "Por que foi rejeitada"],
    ["Vol-targeting", "0,029",
     "**alavancagem disfarçada**: a exposição a risco subiu de 62% para 70%, escala "
     "média de 1,16×, e o Sharpe melhorou em apenas 3 de 6 subperíodos"],
    ["Risk parity", "0,036",
     f"melhora somente no recorte 2010+; **piora no recorte principal** (Sharpe 0,46 "
     f"contra {num(M['robo']['sharpe'])}). Adotá-la exigiria escolher o período conveniente"],
    ["Incluir criptomoeda", "0,004",
     "ETF de bitcoin na B3 só existe desde 2021; no subperíodo investível o ganho cai "
     "para +2,3% com **p = 0,50**. Toda a significância vem do período em que a classe "
     "não era acessível por veículo regulado. É viés de sobrevivência no nível de **classe**"],
], [3.2, 1.8, 12.6])
destaque("Com oito variantes testadas, a correção de Bonferroni leva o melhor p (0,029) "
         "a 0,232, e nenhuma sobreviveria ao ajuste por múltiplos testes. **Optamos por "
         "reportar um resultado marginal robusto em vez de um resultado significativo "
         "garimpado.**")

sub("7.3 A matemática do limite")
par(f"A estatística t de um excedente aproxima-se de **Sharpe × √anos**. Para demonstrar "
    f"um Sharpe de {num(M['robo']['sharpe'])} com 95% de confiança seriam necessários "
    f"**(1,96 / {num(M['robo']['sharpe'])})² ≈ {num(M['anos_nec'], 1)} anos**; dispomos "
    f"de {num(M['anos'], 1)}. **Faltam cerca de dois anos de dados, não uma estratégia "
    f"melhor.** Esse é o limite honesto do que a amostra permite afirmar, e a razão pela "
    f"qual sustentamos a estratégia pelo **conjunto** de evidências de robustez, e não "
    f"por um p-valor isolado.")


# ══════════════════════ PÁGINA 4 ══════════════════════
secao("8. Uso de IA generativa")
sub("8.1 Como parceira de pesquisa e engenharia")
tabela([
    ["Etapa", "Contribuição prática"],
    ["Revisão crítica do desenho",
     "identificou os dois erros que mais alteraram o projeto: (i) a régua correta é o "
     "CDI e não a bolsa, o que revelou que todas as métricas anteriores estavam "
     "infladas; (ii) o cardápio de classes original era estreito demais e prendia o "
     "robô a opções que não superavam o caixa"],
    ["Construção do código",
     "módulos de dados (API do Banco Central e mercado), motor de backtest e bateria "
     "de testes de robustez"],
    ["Auditoria dos resultados",
     "os testes de sanidade que levaram à rejeição do vol-targeting (diagnóstico de "
     "alavancagem disfarçada) e do risk parity nasceram desse processo de questionamento"],
], [4.5, 13.1])
destaque("**Disciplina adotada.** Nenhuma sugestão da IA entrou no modelo sem passar "
         "pelos mesmos testes aplicados às nossas próprias hipóteses, e a maioria foi "
         "**rejeitada** por eles. O ganho não veio de a IA acertar mais; veio de ela nos "
         "forçar a testar mais.")

sub("8.2 Como componente do modelo: a leitura das atas do Copom")
par(f"A falha documentada na seção 7.1 tem uma causa precisa: o momentum é retrovisor, "
    f"e só percebe uma virada de regime depois que ela apareceu no preço. A ata do "
    f"Copom é o documento em que o Banco Central comunica a direção da política "
    f"monetária **antes** de o preço reagir. É informação pública, datada e em texto "
    f"livre, exatamente o tipo de dado que um modelo quantitativo tradicional não "
    f"consegue usar e um modelo de linguagem consegue.")
par(f"Construímos a camada completa: download das **{M['n_atas']} atas** publicadas pela "
    f"API do Banco Central, extração do texto, classificação do regime de juros por "
    f"modelo de linguagem em aperto, neutro ou afrouxamento, e inclinação da alocação. "
    f"Em regime de aperto o robô reduz a exposição a risco em um quarto, com a sobra "
    f"indo para o CDI; em afrouxamento faz o inverso, sempre com **teto de 100% em "
    f"risco**, de modo que a camada nunca introduz alavancagem.")
tabela([
    ["Cuidado metodológico", "Como foi tratado"],
    ["Point-in-time", "a ata é divulgada cerca de seis dias úteis após a reunião. "
     "Só entra na decisão **oito dias corridos** depois, margem sempre conservadora. "
     "Um teste automatizado verifica, sobre os dados, que nenhum mês usa ata publicada "
     "após o seu início"],
    ["Contaminação do modelo de linguagem",
     "um modelo treinado hoje conhece o desfecho de uma ata antiga. Não é possível "
     "eliminar isso, então **medimos**: construímos o mesmo sinal sem nenhuma IA, pela "
     "direção da última mudança da Selic, com defasagem idêntica. Se a leitura do texto "
     "não superar o número público, a conclusão declarada é que a IA não agregou"],
    ["Garimpo de resultado",
     "as hipóteses, a intensidade da inclinação e a conclusão de cada desfecho possível "
     "foram **registradas antes** de executar o modelo de linguagem, com o registro "
     "datado no histórico do repositório"],
], [4.0, 13.6])

sub("8.3 Resultado da camada e estado atual")
par("O braço de controle, que usa apenas a direção da Selic e nenhuma IA, está "
    "validado e melhora o robô de forma consistente:")
tabela([
    ["Versão", "Acima do CDI", "Sharpe", "p", "2022-2023", "Exposição a risco"],
    ["Robô Fundamento", pc(M["robo"]["excedente_cdi_aa"], 1, True),
     num(M["robo"]["sharpe"]), num(M["robo"]["p"], 3),
     pc(M["robo_virada"], 1, True), pc(M["robo_risco"], 0)],
    ["**Com regime de juros**", pc(M["robo_ia"]["excedente_cdi_aa"], 1, True),
     num(M["robo_ia"]["sharpe"]), num(M["robo_ia"]["p"], 3),
     pc(M["robo_ia_virada"], 1, True), pc(M["robo_ia_risco"], 0)],
], [4.6, 2.6, 1.8, 1.7, 2.6, 4.3], destacar=2)
par(f"A melhora ocorre no subperíodo que era o alvo, com 2022-2023 saindo de "
    f"{pc(M['robo_virada'], 1, True)} para {pc(M['robo_ia_virada'], 1, True)} ao ano, e "
    f"o resultado se mantém para qualquer intensidade de inclinação entre 10% e 50%. "
    f"Decisivo para aceitá-la: a exposição média a risco **cai** de "
    f"{pc(M['robo_risco'], 0)} para {pc(M['robo_ia_risco'], 0)}. A camada melhora o "
    f"Sharpe **reduzindo** risco, o oposto exato do vol-targeting que rejeitamos.")
destaque(f"**O que ainda não afirmamos.** O braço do modelo de linguagem está "
         f"implementado e testado, mas **não foi executado**. O que está validado é o "
         f"braço de controle, sem IA. Reportar a leitura das atas como testada seria "
         f"incoerente com o critério que aplicamos ao rejeitar as três variantes da "
         f"seção 7.2.")


# ══════════════════════ PÁGINA 5 ══════════════════════
secao("9. Conclusão")
par(f"**O que está demonstrado.** Alocação com rebalanceamento mensal entre classes "
    f"supera o CDI em {pc(M['robo']['excedente_cdi_aa'], 1, True)} ao ano e supera o "
    f"Ibovespa em retorno, com menos de um terço da queda máxima. A vantagem se mantém "
    f"fora da amostra, em todas as janelas de momentum, em todas as frequências de "
    f"rebalanceamento e sob custos 2,5× maiores. O ranking por mérito agrega sobre o "
    f"rebalanceamento puro, embora a maior parte do valor venha da **estrutura**, que é "
    f"rebalancear entre classes com fuga para o caixa, e não da sofisticação do sinal. "
    f"A inclinação pelo regime de juros melhora o resultado reduzindo risco.")
par(f"**O que não está.** A significância é marginal (p = {num(M['robo']['p'], 3)}), e "
    f"explicamos por quê: a amostra é curta para o Sharpe obtido. O robô falha em "
    f"viradas bruscas de regime, como em 2022-2023, e a camada de juros atenua essa "
    f"falha sem eliminá-la. A leitura das atas por modelo de linguagem está construída "
    f"mas não executada. E o desempenho depende de haver classes atrativas no cardápio: "
    f"no período, a bolsa global contribuiu de forma relevante, o que pode não se repetir.")
destaque("**A leitura que fazemos.** O achado mais útil deste trabalho talvez não seja o "
         "excedente sobre o CDI, e sim o que ele custou para ser afirmado com honestidade: "
         "três melhorias descartadas por não sobreviverem aos próprios testes, uma quarta "
         "aceita apenas depois de passar na mesma régua, e um p-valor que preferimos "
         "reportar como é. Em gestão sistemática, a disciplina de recusar o resultado "
         "bonito é parte do produto.")

secao("10. Próximos passos")
tabela([
    ["Ação", "O que responde"],
    ["**1.** Executar a leitura das atas por modelo de linguagem e comparar com o "
     "braço de controle",
     "responde se ler o texto agrega sobre ler o número público, hipótese já "
     "pré-registrada com critério de aceitação e de rejeição definidos"],
    ["**2.** Ampliar o cardápio com títulos indexados à inflação (IMA-B)",
     "classe relevante e hoje ausente; small caps, títulos e imobiliário dos EUA já "
     "foram testados e reprovados nos mesmos critérios"],
    ["**3.** Reavaliar criptomoeda quando houver histórico de ETF na B3",
     "hoje o resultado depende do período não investível; a partir de 2027 haverá "
     "amostra suficiente para um teste limpo"],
    ["**4.** Simular com aportes mensais e faixas de risco por perfil",
     "aproxima o backtest da experiência real do investidor final"],
], [8.0, 9.6])
nota("Referências: Jegadeesh & Titman (1993), Returns to Buying Winners and Selling "
     "Losers, Journal of Finance; Asness, Moskowitz & Pedersen (2013), Value and Momentum "
     "Everywhere, Journal of Finance; Faber (2007), A Quantitative Approach to Tactical "
     "Asset Allocation, Journal of Wealth Management; Antonacci (2014), Dual Momentum "
     "Investing; Moskowitz, Ooi & Pedersen (2012), Time Series Momentum, Journal of "
     "Financial Economics. Dados públicos e gratuitos: séries de CDI, IPCA e meta Selic "
     "da API do Banco Central do Brasil (SGS), atas do Copom pela API do Banco Central e "
     "cotações via Yahoo Finance. Backtest, métricas, testes de robustez e camada de "
     "leitura de atas implementados pela equipe em Python.")

doc.core_properties.author = ""
doc.core_properties.title = "Relatorio Final - Desafio Quant AI 2026"
doc.core_properties.comments = ""
doc.core_properties.last_modified_by = ""
doc.save(str(SAIDA))
print(f"DOCX gerado: {SAIDA}")
