"""Ajustes na campanha. Sem --sim só mostra o que faria.

Uso (sempre com o ficheiro de IDs):
  python scripts/ajustar.py resultados/evento-31-10.ids.json --orcamento 30 --sim
  python scripts/ajustar.py resultados/evento-31-10.ids.json --pausar-anuncio "AD02 - ..." --sim
  python scripts/ajustar.py resultados/evento-31-10.ids.json --ativar-anuncio "AD02 - ..." --sim
  python scripts/ajustar.py resultados/evento-31-10.ids.json --lance 12 --sim
  python scripts/ajustar.py resultados/evento-31-10.ids.json --inicio 2026-10-18T00:00:00+01:00 --sim
  python scripts/ajustar.py resultados/evento-31-10.ids.json --pausar-campanha --sim
  python scripts/ajustar.py resultados/evento-31-10.ids.json --ativar-campanha --sim

Travas (vêm da skill de estratégia):
- Orçamento sobe no máximo 30% de uma vez, e só uma subida por dia (passar disso exige --forcar).
- Não pausa um anúncio se ficarem menos de 3 ativos (passar disso exige --forcar).
- Cada alteração fica registada em resultados/ajustes.log.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
import meta  # noqa: E402

SUBIDA_MAX = 0.30
LOG = RAIZ / "resultados" / "ajustes.log"


def registar(texto: str):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now().isoformat(timespec='seconds')} {texto}\n")


def subiu_hoje() -> bool:
    if not LOG.exists():
        return False
    hoje = dt.date.today().isoformat()
    return any(l.startswith(hoje) and "ORCAMENTO_SUBIU" in l for l in LOG.read_text(encoding="utf-8").splitlines())


def anuncio_id(est: dict, nome: str) -> str:
    if nome in est["anuncios"]:
        return est["anuncios"][nome]["anuncio_id"]
    for reg in est["anuncios"].values():
        if reg.get("anuncio_id") == nome:
            return nome
    meta.falhar(f"anúncio '{nome}' não está em {sorted(est['anuncios'])}")
    return ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ids")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--orcamento", type=float, help="novo orçamento diário em €")
    g.add_argument("--lance", type=float, help="novo lance em € (só com estratégia de lance com limite)")
    g.add_argument("--pausar-anuncio")
    g.add_argument("--ativar-anuncio")
    g.add_argument("--inicio", help="novo início do conjunto, ISO com fuso")
    g.add_argument("--pausar-campanha", action="store_true")
    g.add_argument("--ativar-campanha", action="store_true")
    ap.add_argument("--sim", action="store_true", help="executa de verdade")
    ap.add_argument("--forcar", action="store_true", help="passa por cima das travas")
    args = ap.parse_args()

    caminho = Path(args.ids)
    caminho = caminho if caminho.is_absolute() else RAIZ / caminho
    est = json.loads(caminho.read_text(encoding="utf-8"))
    cfg = meta.carregar_config()
    alvo, dados, rotulo = None, {}, ""

    if args.orcamento is not None:
        camp = meta.get(est["campanha_id"], {"fields": "daily_budget"}, cfg)
        atual = int(camp["daily_budget"]) / 100
        novo = round(args.orcamento, 2)
        if novo <= 0:
            meta.falhar("o orçamento tem de ser > 0")
        if novo > atual and not args.forcar:
            if novo > atual * (1 + SUBIDA_MAX) + 0.005:
                meta.falhar(f"subida de {atual:.2f} € para {novo:.2f} € é +{(novo / atual - 1) * 100:.0f}%. "
                            f"Máximo {SUBIDA_MAX * 100:.0f}% de uma vez ({atual * (1 + SUBIDA_MAX):.2f} €) — "
                            "subir mais do que isso reinicia a aprendizagem. Usa --forcar se for decisão consciente.")
            if subiu_hoje():
                meta.falhar("o orçamento já subiu hoje. Espera pelo dia seguinte (ou --forcar).")
        alvo, dados = est["campanha_id"], {"daily_budget": meta.euros_para_centimos(novo)}
        rotulo = f"{'ORCAMENTO_SUBIU' if novo > atual else 'ORCAMENTO_DESCEU'} {atual:.2f} -> {novo:.2f}"
    elif args.lance is not None:
        if args.lance <= 0:
            meta.falhar("o lance tem de ser > 0")
        camp = meta.get(est["campanha_id"], {"fields": "bid_strategy"}, cfg)
        if camp.get("bid_strategy") == "LOWEST_COST_WITHOUT_CAP":
            meta.falhar("a campanha está sem limite de lance: não há lance para mudar.")
        alvo, dados = est["conjunto_id"], {"bid_amount": meta.euros_para_centimos(args.lance)}
        rotulo = f"LANCE -> {args.lance:.2f}"
    elif args.pausar_anuncio or args.ativar_anuncio:
        nome = args.pausar_anuncio or args.ativar_anuncio
        alvo = anuncio_id(est, nome)
        if args.pausar_anuncio and not args.forcar:
            ativos = 0
            for reg in est["anuncios"].values():
                st = meta.get(reg["anuncio_id"], {"fields": "status"}, cfg).get("status")
                ativos += st == "ACTIVE" and reg["anuncio_id"] != alvo
            if ativos < 3:
                meta.falhar(f"pausar deixa {ativos} anúncio(s) ativo(s). O mínimo é 3: sobe um criativo novo "
                            "antes (ou --forcar).")
        dados = {"status": "PAUSED" if args.pausar_anuncio else "ACTIVE"}
        rotulo = f"ANUNCIO {dados['status']} {nome}"
    elif args.inicio:
        quando = dt.datetime.fromisoformat(args.inicio)
        if quando.tzinfo is None or quando <= dt.datetime.now(dt.timezone.utc):
            meta.falhar("o início tem de ter fuso e estar no futuro")
        alvo, dados, rotulo = est["conjunto_id"], {"start_time": args.inicio}, f"INICIO -> {args.inicio}"
    else:
        # Pausar/ativar o conjunto sozinho deixa a campanha num estado confuso: mexe nos dois.
        st = "PAUSED" if args.pausar_campanha else "ACTIVE"
        if not args.sim:
            print(f"SIMULAÇÃO: campanha e conjunto → {st}. Repete com --sim para executar.")
            return 0
        meta.post(est["conjunto_id"], {"status": st}, cfg)
        meta.post(est["campanha_id"], {"status": st}, cfg)
        registar(f"CAMPANHA {st}")
        print(f"✅ campanha e conjunto → {st}")
        return 0

    if not args.sim:
        print(f"SIMULAÇÃO: {rotulo} (objeto {alvo}). Repete com --sim para executar.")
        return 0
    meta.post(alvo, dados, cfg)
    registar(rotulo)
    print(f"✅ {rotulo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
