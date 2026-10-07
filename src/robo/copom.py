"""
Camada de IA generativa — o robô lendo as atas do Copom.

PARA QUE SERVE
--------------
O robô perdeu dinheiro uma única vez no backtest: 2022-23, quando o regime de
juros virou (Selic 2% -> 13,75%) e o momentum de 12 meses reagiu tarde. O
momentum é retrovisor por construção: ele só percebe a virada depois que ela
apareceu no preço.

A ata do Copom é o documento em que o Banco Central diz, em português, para
onde a política monetária está indo — antes de o preço reagir. É informação
pública, datada, e em texto livre: exatamente o tipo de dado que um modelo
quantitativo tradicional não consegue usar e um LLM consegue.

O QUE ESTA CAMADA FAZ
---------------------
  1. Baixa as atas do Copom (API pública do BC, ~8 por ano desde 2006).
  2. Um LLM lê cada ata e classifica o REGIME que o documento comunica:
        aperto  ·  neutro  ·  afrouxamento
  3. O regime inclina a alocação: em aperto o robô reduz risco (o CDI está
     ficando mais caro de abrir mão); em afrouxamento ele aceita mais risco.

DISCIPLINA POINT-IN-TIME (o ponto mais importante)
--------------------------------------------------
Uma ata é DIVULGADA cerca de 6 dias úteis DEPOIS da reunião. Usar a ata na data
da reunião seria olhar o futuro. Por isso:

    data_disponivel = data_da_reuniao + FOLGA_PUBLICACAO (8 dias corridos)

e a decisão do mês t só enxerga atas com `data_disponivel` até o fim do mês
t-1 — a mesma régua que o resto do robô usa com `shift(1)`.

O RISCO QUE UM AVALIADOR VAI LEVANTAR (e como tratamos)
-------------------------------------------------------
"Um LLM treinado em 2026 lendo uma ata de 2015 já sabe o que aconteceu depois."
É uma crítica legítima e não dá para eliminá-la por completo. O que fazemos:

  (a) A tarefa é de LEITURA, não de previsão. Perguntamos "o que este documento
      comunica?", e a resposta está no próprio texto. Não perguntamos "o que vai
      acontecer com a bolsa".
  (b) Removemos datas explícitas do texto enviado (medida parcial e assumida
      como tal — o nível da Selic aparece no texto e já identifica a época).
  (c) BRAÇO DE CONTROLE: `regime_mecanico()` produz o mesmo sinal sem nenhum
      LLM, olhando só a direção da última mudança da Selic (série pública,
      point-in-time). Se o robô com LLM empatar com o robô com o sinal
      mecânico, o LLM não agregou nada — e reportamos isso. É a única forma
      honesta de medir a contribuição da IA.

REPRODUTIBILIDADE
-----------------
As classificações do LLM ficam gravadas em `data/processed/copom_regimes.csv`,
com o trecho da ata que sustentou cada uma. Quem for reproduzir o backtest não
precisa de chave de API — e pode auditar o que o modelo respondeu, ata por ata.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as cfg

# ── Constantes desta camada ─────────────────────────────────────────────────
API_ATAS = "https://www.bcb.gov.br/api/servico/sitebcb/atascopom/ultimas"
BASE_BC = "https://www.bcb.gov.br"
SGS_SELIC_META = 432          # Meta Selic definida pelo Copom (% a.a., diária)

# Folga entre a reunião e a divulgação da ata. O BC publica em ~6 dias úteis;
# usamos 8 dias CORRIDOS, que é conservador (nunca antecipa a informação).
FOLGA_PUBLICACAO = pd.Timedelta(days=8)

REGIMES = ("aperto", "neutro", "afrouxamento")

AJUDA = """Camada de IA — o robo lendo as atas do Copom.

  python src/robo/copom.py                  situacao atual (nao gasta nada)
  python src/robo/copom.py --estimar        quanto vai custar (nao gasta nada)
  python src/robo/copom.py --testar-chave   1 ata, ~US$ 0,06, prova que a chave funciona
  python src/robo/copom.py --classificar    a rodagem completa (~US$ 4,46)

  Opcoes de --classificar:
    --sim      nao pergunta confirmacao (para script/CI)
    --forcar   refaz tudo do zero, ignorando o que ja esta no CSV

PARA USAR O BRACO DE IA voce precisa de uma chave da Anthropic. Crie um
arquivo `.env` na raiz do projeto (ja esta no .gitignore) com:

    ANTHROPIC_API_KEY=sk-ant-...

A rodagem e RETOMAVEL: grava o CSV a cada ata, entao pode interromper e
continuar depois sem perder o que ja foi pago. Rode uma vez e o resultado
fica em data/processed/copom_regimes.csv — a partir dai o backtest e
reproduzivel por qualquer pessoa SEM chave.

SEM CHAVE voce ainda roda tudo que nao usa LLM:
    python src/robo/rodar_ia.py       o braco de controle (Selic, zero IA)
    python src/robo/teste_copom.py    30 testes do pipeline, custo zero"""

CACHE_PDF = cfg.DATA_RAW / "copom"
CACHE_TXT = cfg.DATA_RAW / "copom_txt"
ARQ_REGIMES = cfg.DATA_PROC / "copom_regimes.csv"

MODELO_LLM = "claude-opus-5"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


# ── 1. Índice das atas ──────────────────────────────────────────────────────
def listar_atas(desde: str = "2013-01-01") -> pd.DataFrame:
    """Índice das atas publicadas: data da reunião, título e link do PDF.

    Começamos em 2013 (e não em 2015) de propósito: o momentum de 12 meses
    precisa de histórico, então o painel do robô já carrega dados anteriores.
    """
    r = requests.get(API_ATAS, params={"quantidade": 250, "filtro": ""},
                     headers=HEADERS, timeout=60)
    r.raise_for_status()
    itens = r.json()["conteudo"]

    df = pd.DataFrame(itens)
    df["data_reuniao"] = pd.to_datetime(df["DataReferencia"]).dt.tz_localize(None).dt.normalize()
    df = df[df["Url"].notna() & (df["data_reuniao"] >= pd.Timestamp(desde))]
    df["url_pdf"] = BASE_BC + df["Url"]
    # A ata só existe para o mundo alguns dias DEPOIS da reunião.
    df["data_disponivel"] = df["data_reuniao"] + FOLGA_PUBLICACAO
    df = df.rename(columns={"Titulo": "titulo"})

    return (df[["data_reuniao", "data_disponivel", "titulo", "url_pdf"]]
            .sort_values("data_reuniao").reset_index(drop=True))


# ── 2. Texto da ata ─────────────────────────────────────────────────────────
def _mascarar_datas(txt: str) -> str:
    """Remove datas explícitas do texto (mitigação PARCIAL de contaminação).

    Assumimos que é parcial: o nível da Selic citado na ata já identifica
    aproximadamente a época. A defesa real é o braço de controle mecânico, não
    esta função. Ela existe para não facilitar o reconhecimento da data.
    """
    txt = re.sub(r"\b(19|20)\d{2}\b", "[ANO]", txt)
    meses = ("janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|"
             r"outubro|novembro|dezembro")
    txt = re.sub(rf"\b\d{{1,2}}\s*(?:a|e|-)?\s*\d{{0,2}}\s*de\s*(?:{meses})\b",
                 "[DATA]", txt, flags=re.IGNORECASE)
    return re.sub(rf"\b(?:{meses})\b", "[MES]", txt, flags=re.IGNORECASE)


def texto_da_ata(url_pdf: str, data_reuniao: pd.Timestamp) -> str:
    """Baixa o PDF da ata e extrai o texto, com cache em disco."""
    from pypdf import PdfReader

    CACHE_PDF.mkdir(parents=True, exist_ok=True)
    CACHE_TXT.mkdir(parents=True, exist_ok=True)
    chave = data_reuniao.strftime("%Y%m%d")
    f_txt, f_pdf = CACHE_TXT / f"{chave}.txt", CACHE_PDF / f"{chave}.pdf"

    if f_txt.exists():
        return f_txt.read_text(encoding="utf-8")

    if not f_pdf.exists():
        r = requests.get(url_pdf, headers=HEADERS, timeout=120)
        r.raise_for_status()
        f_pdf.write_bytes(r.content)

    bruto = " ".join((pg.extract_text() or "") for pg in PdfReader(f_pdf).pages)
    limpo = re.sub(r"\s+", " ", bruto).strip()
    f_txt.write_text(limpo, encoding="utf-8")
    return limpo


# ── 3a. Classificação pelo LLM ──────────────────────────────────────────────
INSTRUCAO = """Você é um analista de renda fixa lendo a ata de uma reunião do \
Comitê de Política Monetária (Copom) do Banco Central do Brasil.

Sua tarefa é de LEITURA, não de previsão. Descreva o que ESTE DOCUMENTO \
COMUNICA, com base apenas no que está escrito nele.

REGRA CENTRAL: separe o que o Comitê FEZ do que o Comitê SINALIZA.
A decisão daquele dia já é pública num número (a meta Selic). O que só existe \
no texto é a sinalização para adiante: o balanço de riscos, o grau de \
restritividade que o Comitê julga necessário, e o que ele indica para as \
próximas reuniões. É essa parte prospectiva que interessa.

Regras:
- Baseie-se EXCLUSIVAMENTE no texto fornecido. Não use conhecimento externo \
sobre o que aconteceu com a economia, os juros ou os mercados depois desta \
reunião. Se o texto for ambíguo, use a categoria neutra e registre confiança \
baixa.
- Cite literalmente. A evidência precisa ser um trecho que existe na ata.

Campos:

1. "regime" — a POSTURA GERAL que o documento comunica:
   - "aperto": política contracionista, juros subindo, ou manutenção com \
vigilância inflacionária elevada.
   - "neutro": estabilidade, cautela sem direção definida, riscos equilibrados.
   - "afrouxamento": política em flexibilização, juros caindo, ou manutenção \
com viés de queda.

2. "vies_prospectivo" — o que o Comitê sinaliza para as PRÓXIMAS reuniões, \
independentemente do que decidiu hoje. Um Comitê pode cortar juros hoje e \
sinalizar cautela adiante, ou manter hoje e sinalizar alta. É a diferença \
entre os dois que carrega informação que o número da Selic não tem.
   - "alta": indica elevação ou possibilidade de elevação adiante.
   - "manutencao": indica estabilidade, ou não sinaliza direção.
   - "queda": indica reduções ou possibilidade de redução adiante.

3. "restritividade" — 0 a 10: o quanto o Comitê descreve a política monetária \
como restritiva/contracionista neste momento (0 = claramente estimulativa, \
5 = neutra, 10 = fortemente contracionista).

4. "incerteza" — 0 a 10: o quanto o Comitê enfatiza incerteza, riscos elevados \
ou dispersão de cenários.

5. "confianca" — 0 a 1: o quanto o texto é explícito. Baixa se você precisou \
inferir muito.

6. "evidencia" — citação CURTA e LITERAL da ata (até 200 caracteres) que \
sustenta a classificação de "vies_prospectivo"."""

VIESES = ("alta", "manutencao", "queda")

ESQUEMA = {
    "type": "object",
    "properties": {
        "regime": {"type": "string", "enum": list(REGIMES)},
        "vies_prospectivo": {"type": "string", "enum": list(VIESES)},
        "restritividade": {"type": "number"},
        "incerteza": {"type": "number"},
        "confianca": {"type": "number"},
        "evidencia": {"type": "string"},
    },
    "required": ["regime", "vies_prospectivo", "restritividade", "incerteza",
                 "confianca", "evidencia"],
    "additionalProperties": False,
}


def _carregar_env() -> None:
    """Lê a chave de API de um `.env` na raiz, se existir.

    Sem dependência nova: o SDK da Anthropic lê `ANTHROPIC_API_KEY` do ambiente,
    e esta função só faz a ponte entre o arquivo e o ambiente. O `.env` NÃO vai
    para o Git (está no .gitignore) — chave de API não se comita.
    """
    env = cfg.ROOT / ".env"
    if not env.exists():
        return
    for linha in env.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        os.environ.setdefault(chave.strip(), valor.strip().strip("'\""))


def classificar_llm(texto: str, client=None) -> dict:
    """Uma ata -> {regime, confianca, evidencia}. Uma chamada, saída estruturada."""
    import anthropic

    _carregar_env()
    client = client or anthropic.Anthropic()
    resp = client.messages.create(
        model=MODELO_LLM,
        max_tokens=2000,
        system=INSTRUCAO,
        thinking={"type": "adaptive"},
        output_config={
            "effort": "medium",
            "format": {"type": "json_schema", "schema": ESQUEMA},
        },
        messages=[{"role": "user", "content": f"<ata>\n{texto}\n</ata>"}],
    )
    bruto = next(b.text for b in resp.content if b.type == "text")
    return json.loads(bruto)


def _checar_chave() -> str | None:
    """Confere a chave ANTES de começar. Devolve a mensagem de erro, ou None.

    Existe para não deixar alguém iniciar uma rodagem paga e descobrir na 40ª
    ata que a chave estava errada — ou ver 81 mensagens de falha em sequência
    sem entender o motivo.
    """
    _carregar_env()
    if not (os.environ.get("ANTHROPIC_API_KEY") or
            os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        return (
            "Nao encontrei a chave da API.\n\n"
            "  Crie um arquivo .env na raiz do projeto com a linha:\n"
            "      ANTHROPIC_API_KEY=sk-ant-...\n\n"
            f"  (esperado em: {cfg.ROOT / '.env'})\n"
            "  O .env esta no .gitignore — a chave nao vai para o repositorio.\n\n"
            "  Sem chave voce ainda pode rodar tudo que nao usa LLM:\n"
            "      python src/robo/rodar_ia.py      (braco de controle)\n"
            "      python src/robo/teste_copom.py   (testes do pipeline)"
        )
    return None


def _gravar(linhas: list[dict]) -> pd.DataFrame:
    """Grava o CSV. Chamada a cada ata, para nunca perder trabalho já pago.

    Se não há nada para gravar (por exemplo: a chave era inválida e a primeira
    ata já falhou), NÃO escreve — para não sobrescrever um CSV bom com um vazio.
    """
    if not linhas:
        return pd.DataFrame()
    df = pd.DataFrame(linhas).sort_values("data_reuniao").reset_index(drop=True)
    ARQ_REGIMES.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(ARQ_REGIMES, index=False, encoding="utf-8")
    return df


def construir_regimes(limite: int | None = None, forcar: bool = False,
                      confirmar: bool = True) -> pd.DataFrame | None:
    """Roda o LLM sobre as atas e grava o resultado em CSV.

    Idempotente e retomável: só chama o LLM para atas que ainda não estão no
    CSV, e grava o CSV a cada ata concluída. Se cair no meio (rede, rate limit,
    Ctrl+C), a rodagem seguinte continua de onde parou — nada do que já foi pago
    é perdido.

    Depois de rodar uma vez, o backtest é reproduzível por qualquer pessoa
    SEM chave de API.
    """
    import anthropic

    erro = _checar_chave()
    if erro:
        print(erro)
        return None

    atas = listar_atas()
    if limite:
        atas = atas.tail(limite)

    linhas, feitas = [], set()
    if ARQ_REGIMES.exists() and not forcar:
        ja = pd.read_csv(ARQ_REGIMES, parse_dates=["data_reuniao", "data_disponivel"])
        linhas = ja.to_dict("records")
        feitas = set(ja["data_reuniao"])

    pendentes = atas[~atas["data_reuniao"].isin(feitas)]
    if pendentes.empty:
        print(f"Nada a fazer: as {len(feitas)} atas ja estao em {ARQ_REGIMES.name}.")
        print("Para refazer do zero, use --forcar.")
        return pd.DataFrame(linhas)

    if feitas:
        print(f"Retomando: {len(feitas)} atas ja classificadas, "
              f"{len(pendentes)} pendentes.")

    # Confirmação de custo — ninguém deve gastar sem saber quanto.
    custo = len(pendentes) * 0.055          # ~US$ 4,46 / 81 atas, medido
    if confirmar:
        print(f"\nVai classificar {len(pendentes)} atas com {MODELO_LLM}.")
        print(f"Custo estimado: ~US$ {custo:.2f}  (detalhe: --estimar)")
        try:
            if input("Continuar? [s/N] ").strip().lower() not in ("s", "sim", "y"):
                print("Cancelado. Nada foi gasto.")
                return None
        except EOFError:                     # rodando sem terminal interativo
            print("Sem terminal interativo — use --sim para confirmar de antemao.")
            return None

    client = anthropic.Anthropic()
    novas, falhas = 0, 0
    print()
    try:
        for n, (_, a) in enumerate(pendentes.iterrows(), 1):
            marca = f"[{n}/{len(pendentes)}] {a['data_reuniao']:%Y-%m-%d}"
            try:
                texto = _mascarar_datas(texto_da_ata(a["url_pdf"], a["data_reuniao"]))
                out = classificar_llm(texto, client=client)
            except anthropic.AuthenticationError:
                print(f"{marca}  CHAVE INVALIDA — abortando antes de gastar mais.")
                print("Confira o valor de ANTHROPIC_API_KEY no .env.")
                break
            except anthropic.PermissionDeniedError as e:
                print(f"{marca}  SEM PERMISSAO para {MODELO_LLM}: {e}")
                print("A chave existe mas nao tem acesso a esse modelo. Abortando.")
                break
            except Exception as e:            # ata ilegível, rede, rate limit
                falhas += 1
                print(f"{marca}  falhou ({type(e).__name__}) — segue para a proxima")
                if falhas >= 10:
                    print("10 falhas seguidas. Abortando; rode de novo para retomar.")
                    break
                continue

            falhas = 0
            novas += 1
            linhas.append({
                "data_reuniao": a["data_reuniao"],
                "data_disponivel": a["data_disponivel"],
                "titulo": a["titulo"], "regime": out["regime"],
                "vies_prospectivo": out["vies_prospectivo"],
                "restritividade": out["restritividade"],
                "incerteza": out["incerteza"], "confianca": out["confianca"],
                "evidencia": out["evidencia"],
            })
            _gravar(linhas)                   # grava JÁ — não perde o que foi pago
            print(f"{marca}  {out['regime']:<13} "
                  f"vies={out['vies_prospectivo']:<11} "
                  f"restr={out['restritividade']:>4.1f} "
                  f"conf={out['confianca']:.2f}", flush=True)
            time.sleep(0.5)                   # gentileza com o rate limit
    except KeyboardInterrupt:
        print("\nInterrompido. O que ja foi classificado esta salvo.")

    df = _gravar(linhas)
    if df.empty:
        print("\nNenhuma ata foi classificada — nada gravado, nada gasto.")
        return None

    print(f"\n{novas} atas novas | {len(df)} no total -> {ARQ_REGIMES}")
    if len(df) < len(atas):
        print(f"Faltam {len(atas) - len(df)}. Rode o mesmo comando para retomar.")
    else:
        print("Completo. Agora rode: python src/robo/rodar_ia.py")
    return df


def estimar_custo() -> None:
    """Quanto vai custar rodar o LLM sobre todas as atas — antes de gastar.

    Estima localmente, sem chamar a API (o endpoint de contagem de tokens já
    exigiria chave). Para português, ~3,7 caracteres por token é uma
    aproximação razoável; a conta é para dimensionar, não para faturar.
    """
    CHARS_POR_TOKEN = 3.7
    PRECO_ENTRADA, PRECO_SAIDA = 5.0, 25.0        # US$ por milhão (claude-opus-5)
    SAIDA_POR_ATA = 1200                          # resposta + thinking adaptativo

    atas = listar_atas()
    chars = sum(len(texto_da_ata(a["url_pdf"], a["data_reuniao"]))
                for _, a in atas.iterrows())
    tok_prompt = len(INSTRUCAO) / CHARS_POR_TOKEN
    entrada = chars / CHARS_POR_TOKEN + tok_prompt * len(atas)
    saida = SAIDA_POR_ATA * len(atas)
    custo = entrada / 1e6 * PRECO_ENTRADA + saida / 1e6 * PRECO_SAIDA

    print(f"Atas                : {len(atas)}")
    print(f"Caracteres totais   : {chars:,}")
    print(f"Tokens de entrada   : ~{entrada:,.0f}")
    print(f"Tokens de saída     : ~{saida:,.0f} (estimado)")
    print(f"Modelo              : {MODELO_LLM} (US$ {PRECO_ENTRADA:.0f}/{PRECO_SAIDA:.0f} por milhao)")
    print(f"CUSTO ESTIMADO      : ~US$ {custo:.2f}  (uma vez; depois fica em cache)")
    print(f"Com a Batch API     : ~US$ {custo/2:.2f}  (50% off, resultado em ate 1h)")


# ── 3b. Braço de controle: o mesmo sinal SEM nenhum LLM ─────────────────────
def regime_mecanico(desde: str = "2013-01-01") -> pd.Series:
    """Regime pela direção da última mudança da Selic — zero IA.

    É o CONTROLE do experimento. Usa a série SGS 432 (meta Selic definida pelo
    Copom), pública e point-in-time: a meta muda no dia seguinte à reunião, e a
    direção da mudança é observável na hora.

        subiu  -> aperto        caiu -> afrouxamento        parada -> neutro

    Se o robô com LLM não ganhar deste sinal, o LLM não agregou nada. Aplicamos
    a MESMA folga de publicação, para que os dois braços tenham exatamente a
    mesma informação disponível na mesma data — a diferença é só a leitura.
    """
    import dados

    meta = dados._sgs(SGS_SELIC_META)   # mesmo buscador do resto do projeto

    # Só os dias em que a meta MUDOU — cada um corresponde a uma decisão.
    mudou = meta.diff()
    eventos = mudou[mudou != 0].dropna()
    regime = pd.Series(
        ["aperto" if d > 0 else "afrouxamento" for d in eventos],
        index=eventos.index + FOLGA_PUBLICACAO, name="regime",
    )
    return regime[regime.index >= pd.Timestamp(desde)]


# ── 4. Série mensal point-in-time ───────────────────────────────────────────
def regime_mensal(indice: pd.DatetimeIndex, fonte: str = "llm") -> pd.Series:
    """Regime vigente para a decisão de cada mês — já com a defasagem correta.

    Recebe o índice mensal do painel do robô e devolve, para cada mês t, o
    regime da ata mais recente que JÁ ESTAVA PUBLICADA quando a decisão de t foi
    tomada (isto é, até o fim do mês t-1).

    O `.shift(1)` no fim é a mesma trava usada em `estrategia.py`: nenhuma linha
    enxerga o próprio mês que está alocando.
    """
    # O viés prospectivo usa o mesmo vocabulário de regime para poder entrar na
    # MESMA função de inclinação — o que muda é só a leitura, não a regra.
    VIES_P_REGIME = {"alta": "aperto", "queda": "afrouxamento",
                     "manutencao": "neutro"}

    if fonte in ("llm", "llm_vies"):
        if not ARQ_REGIMES.exists():
            raise FileNotFoundError(
                f"{ARQ_REGIMES} nao existe. Rode: python src/robo/copom.py --classificar"
            )
        df = pd.read_csv(ARQ_REGIMES, parse_dates=["data_disponivel"])
        col = "regime" if fonte == "llm" else "vies_prospectivo"
        s = df.set_index("data_disponivel")[col].sort_index()
        eventos = s.map(VIES_P_REGIME) if fonte == "llm_vies" else s
    elif fonte == "mecanico":
        eventos = regime_mecanico()
    else:
        raise ValueError(
            f"fonte deve ser 'llm', 'llm_vies' ou 'mecanico', recebi {fonte!r}")

    # Último regime conhecido no fim de cada mês do painel, depois defasado.
    diario = eventos[~eventos.index.duplicated(keep="last")]
    mensal = diario.reindex(
        diario.index.union(indice)).ffill().reindex(indice)
    return mensal.shift(1).rename("regime")


# ── CLI ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")

    args = set(sys.argv[1:])

    if "--ajuda" in args or "-h" in args or "--help" in args:
        print(AJUDA)
    elif "--estimar" in args:
        estimar_custo()
    elif "--testar-chave" in args:
        # Gasta ~US$ 0,06: classifica UMA ata só para provar que a chave e o
        # modelo funcionam, antes de comprometer os ~US$ 4,46 da rodagem cheia.
        erro = _checar_chave()
        if erro:
            print(erro)
            sys.exit(1)
        a = listar_atas().iloc[-1]
        print(f"Classificando 1 ata ({a['data_reuniao']:%Y-%m-%d}) para testar "
              "a chave (~US$ 0,06)...\n")
        try:
            out = classificar_llm(
                _mascarar_datas(texto_da_ata(a["url_pdf"], a["data_reuniao"])))
        except Exception as e:
            print(f"FALHOU: {type(e).__name__}: {e}")
            sys.exit(1)
        for k, v in out.items():
            print(f"  {k:18s}: {v}")
        print("\nChave OK. Agora rode: python src/robo/copom.py --classificar")
    elif "--classificar" in args:
        construir_regimes(forcar="--forcar" in args, confirmar="--sim" not in args)
    else:
        atas = listar_atas()
        print(f"Atas disponiveis: {len(atas)} "
              f"({atas['data_reuniao'].min():%Y-%m} a "
              f"{atas['data_reuniao'].max():%Y-%m})")
        if ARQ_REGIMES.exists():
            n = len(pd.read_csv(ARQ_REGIMES))
            print(f"Ja classificadas pelo LLM: {n} -> {ARQ_REGIMES.name}")
        else:
            print("Ja classificadas pelo LLM: 0 (o braco de IA ainda nao rodou)")
        mec = regime_mecanico()
        print(f"Braco de controle (Selic, sem IA): {len(mec)} decisoes")
        print(f"\n{AJUDA}")
