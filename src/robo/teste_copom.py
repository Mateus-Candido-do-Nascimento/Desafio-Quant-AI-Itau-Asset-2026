"""
Testa a camada de IA SEM gastar um centavo.

Uso:  python src/robo/teste_copom.py

Por que existe: a rodagem do LLM custa dinheiro e demora. Descobrir na ata 60
de 81 que o parser quebra, que o esquema não bate ou que a data ficou errada é
caro e chato. Este arquivo troca a chamada da API por um cliente falso e
exercita TODO o resto do caminho — download, extração de PDF, esquema,
gravação em CSV, leitura de volta, defasagem point-in-time e inclinação da
carteira.

Se tudo passar aqui, a única coisa que pode falhar na rodagem paga é a própria
resposta do modelo.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as cfg
import copom
import estrategia as est

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ok_total, falhas = 0, []


def checa(nome: str, condicao: bool, detalhe: str = "") -> None:
    global ok_total
    if condicao:
        ok_total += 1
        print(f"  OK   {nome}")
    else:
        falhas.append(nome)
        print(f"  FALHA {nome} {detalhe}")


class ClienteFalso:
    """Imita `anthropic.Anthropic` devolvendo uma resposta válida pelo esquema.

    Alterna as respostas de propósito, para que o sinal resultante tenha
    variação e os testes de defasagem e de inclinação tenham o que exercitar.
    """

    def __init__(self):
        self.chamadas = 0
        self.messages = self

    def create(self, **kwargs):
        self.chamadas += 1
        i = self.chamadas
        payload = {
            "regime": copom.REGIMES[i % 3],
            "vies_prospectivo": copom.VIESES[i % 3],
            "restritividade": float(i % 11),
            "incerteza": float((i * 3) % 11),
            "confianca": 0.8,
            "evidencia": f"trecho simulado {i}",
        }
        bloco = type("B", (), {"type": "text", "text": json.dumps(payload)})()
        return type("R", (), {"content": [bloco]})()


def main() -> None:
    print("=" * 72)
    print("TESTE DA CAMADA DE IA — sem chave, sem custo")
    print("=" * 72)

    # ── 1. Índice das atas ──────────────────────────────────────────────────
    print("\n1. Índice das atas")
    atas = copom.listar_atas()
    checa("baixou o índice", len(atas) > 50, f"({len(atas)} atas)")
    checa("colunas esperadas",
          {"data_reuniao", "data_disponivel", "url_pdf"} <= set(atas.columns))
    checa("ordem cronológica", atas["data_reuniao"].is_monotonic_increasing)

    # A trava point-in-time: a ata NUNCA pode estar disponível na própria reunião
    folga = (atas["data_disponivel"] - atas["data_reuniao"]).dt.days
    checa("defasagem de publicação aplicada", (folga >= 6).all(),
          f"(mínimo {folga.min()} dias)")

    # ── 2. Extração de PDF ──────────────────────────────────────────────────
    print("\n2. Extração de texto do PDF")
    amostra = pd.concat([atas.head(2), atas.tail(2)])   # as mais velhas e as mais novas
    textos = {}
    for _, a in amostra.iterrows():
        t = copom.texto_da_ata(a["url_pdf"], a["data_reuniao"])
        textos[a["data_reuniao"]] = t
        checa(f"extraiu {a['data_reuniao']:%Y-%m}", len(t) > 3000, f"({len(t)} chars)")
    checa("texto menciona o Copom",
          all("Copom" in t or "COPOM" in t for t in textos.values()))

    # ── 3. Máscara de datas ─────────────────────────────────────────────────
    print("\n3. Máscara de datas (mitigação parcial de contaminação)")
    bruto = list(textos.values())[0]
    masc = copom._mascarar_datas(bruto)
    import re
    checa("removeu anos de 4 dígitos", not re.search(r"\b(19|20)\d{2}\b", masc))
    checa("removeu nomes de mês", "janeiro" not in masc.lower())
    checa("não destruiu o texto", len(masc) > len(bruto) * 0.8)

    # ── 4. Esquema e parsing da resposta ────────────────────────────────────
    print("\n4. Chamada ao LLM (cliente falso) e esquema")
    falso = ClienteFalso()
    out = copom.classificar_llm("ata de mentira", client=falso)
    checa("devolveu dict", isinstance(out, dict))
    checa("tem todos os campos obrigatórios",
          set(copom.ESQUEMA["required"]) <= set(out))
    checa("regime no domínio", out["regime"] in copom.REGIMES)
    checa("viés no domínio", out["vies_prospectivo"] in copom.VIESES)

    # ── 5. Ida e volta pelo CSV ─────────────────────────────────────────────
    print("\n5. Gravação e leitura do CSV")
    linhas = []
    for i, (_, a) in enumerate(atas.iterrows(), 1):
        falso.chamadas = i
        o = copom.classificar_llm("x", client=falso)
        linhas.append({
            "data_reuniao": a["data_reuniao"], "data_disponivel": a["data_disponivel"],
            "titulo": a["titulo"], **o,
        })
    df = pd.DataFrame(linhas)
    tmp = cfg.DATA_PROC / "_teste_copom_regimes.csv"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(tmp, index=False, encoding="utf-8")
    volta = pd.read_csv(tmp, parse_dates=["data_reuniao", "data_disponivel"])
    checa("CSV preserva as linhas", len(volta) == len(df))
    checa("CSV preserva as datas",
          (volta["data_disponivel"] == df["data_disponivel"]).all())

    # ── 6. Defasagem point-in-time (o teste que mais importa) ───────────────
    print("\n6. Point-in-time: nenhum mês enxerga o próprio mês")
    original = copom.ARQ_REGIMES
    try:
        copom.ARQ_REGIMES = tmp
        idx = pd.date_range("2015-01-31", "2026-07-31", freq="ME")
        for fonte in ("llm", "llm_vies"):
            reg = copom.regime_mensal(idx, fonte=fonte)
            checa(f"série mensal '{fonte}' alinhada", len(reg) == len(idx))
            checa(f"'{fonte}' no vocabulário de regime",
                  set(reg.dropna().unique()) <= set(copom.REGIMES))

        # Prova direta da trava: para cada mês com sinal, a ata usada tem de ter
        # sido publicada ANTES do início daquele mês.
        reg = copom.regime_mensal(idx, fonte="llm")
        pub = volta.set_index("data_disponivel")["regime"].sort_index()
        vazou = 0
        for dt in idx[reg.notna()]:
            inicio_mes = dt.replace(day=1)
            disponiveis = pub[pub.index < inicio_mes]
            if disponiveis.empty or disponiveis.iloc[-1] != reg.loc[dt]:
                vazou += 1
        checa("nenhum mês usa ata publicada depois do seu início", vazou == 0,
              f"({vazou} meses com vazamento)")
    finally:
        copom.ARQ_REGIMES = original
        tmp.unlink(missing_ok=True)

    # ── 7. Inclinação da carteira ───────────────────────────────────────────
    print("\n7. Inclinação da carteira")
    idx = pd.date_range("2015-01-31", "2026-07-31", freq="ME")
    painel = pd.DataFrame(index=idx)
    for c in cfg.CLASSES:                      # painel sintético só para a regra
        painel[f"nivel_{c}"] = pd.Series(range(len(idx)), index=idx) + 100.0
        painel[f"ret_{c}"] = 0.01
    painel["nivel_CDI"] = pd.Series(range(len(idx)), index=idx) * 0.5 + 100.0

    ciclo = ["aperto", "neutro", "afrouxamento"] * (len(idx) // 3 + 1)
    reg = pd.Series(ciclo[:len(idx)], index=idx)
    base = est.pesos_ranking(painel)
    ia = est.pesos_ranking_ia(painel, reg)

    checa("pesos somam 1", ((ia.sum(axis=1) - 1.0).abs() < 1e-9).all())
    checa("nenhum peso negativo", (ia >= -1e-12).all().all())
    risco = ia[cfg.CLASSES_RISCO].sum(axis=1)
    checa("exposição a risco nunca passa de 100% (sem alavancagem)",
          (risco <= 1.0 + 1e-9).all(), f"(máx {risco.max():.3f})")

    ap, af = reg == "aperto", reg == "afrouxamento"
    r_base = base[cfg.CLASSES_RISCO].sum(axis=1)
    checa("aperto REDUZ risco", (risco[ap] <= r_base[ap] + 1e-9).all())
    checa("afrouxamento não reduz risco", (risco[af] >= r_base[af] - 1e-9).all())
    checa("neutro não altera nada",
          ((ia[reg == "neutro"] - base[reg == "neutro"]).abs() < 1e-9).all().all())

    # A trava do CDI é soberana: se o ranking foi para 100% caixa, nenhuma ata
    # pode tirá-lo de lá.
    so_caixa = r_base < 1e-9
    if so_caixa.any():
        checa("ata não reabilita classe reprovada no momentum absoluto",
              (risco[so_caixa] < 1e-9).all())

    # ── veredito ────────────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    if falhas:
        print(f"{len(falhas)} FALHA(S) de {ok_total + len(falhas)}:")
        for f in falhas:
            print(f"  - {f}")
        sys.exit(1)
    print(f"TODOS OS {ok_total} TESTES PASSARAM.")
    print("O pipeline está pronto: a rodagem paga só depende da resposta do modelo.")
    print("=" * 72)


if __name__ == "__main__":
    main()
