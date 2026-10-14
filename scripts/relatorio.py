"""Relatório da campanha: dia a dia (4 dias), por anúncio, ritmo de gasto de hoje.

Uso:
  python scripts/relatorio.py resultados/evento-31-10.ids.json
  python scripts/relatorio.py resultados/evento-31-10.ids.json --inscricoes-pagas 23 --dias 7

--inscricoes-pagas: número REAL de inscrições pagas (contadas fora da Meta, ex.: comprovativos
recebidos). Com ele o relatório mostra o custo real por inscrição paga, que é o número que decide.
Só lê. Não altera nada.
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

TIPOS_LEAD = ("offsite_conversion.fb_pixel_lead", "lead", "onsite_web_lead")
TIPOS_COMPRA = ("offsite_conversion.fb_pixel_purchase", "purchase", "omni_purchase")
CAMPOS = "spend,impressions,reach,frequency,cpm,inline_link_clicks,inline_link_click_ctr,actions"


def acao(linha: dict, tipos: tuple[str, ...]) -> int:
    """Primeiro tipo presente na ordem de prioridade (somar todos contaria a mesma inscrição 2x)."""
    por_tipo = {a.get("action_type"): a.get("value") for a in linha.get("actions") or []}
    for t in tipos:
        if t in por_tipo:
            return int(float(por_tipo[t]))
    return 0


def eur(v) -> str:
    return f"{float(v or 0):.2f} €"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ids")
    ap.add_argument("--dias", type=int, default=4)
    ap.add_argument("--inscricoes-pagas", type=int, default=None)
    args = ap.parse_args()

    caminho = Path(args.ids)
    caminho = caminho if caminho.is_absolute() else RAIZ / caminho
    est = json.loads(caminho.read_text(encoding="utf-8"))
    cfg = meta.carregar_config()
    conta = meta.get(cfg["META_AD_ACCOUNT_ID"], {"fields": "timezone_offset_hours_utc,timezone_name"}, cfg)
    fuso = dt.timezone(dt.timedelta(hours=float(conta.get("timezone_offset_hours_utc", 0))))
    agora = dt.datetime.now(fuso)
    hoje = agora.date()
    desde = hoje - dt.timedelta(days=max(1, args.dias) - 1)
    rng = {"since": desde.isoformat(), "until": hoje.isoformat()}

    camp = meta.get(est["campanha_id"], {"fields": "name,effective_status,daily_budget,start_time"}, cfg)
    orc = int(camp.get("daily_budget", 0)) / 100
    print(f"{camp['name']} — {camp.get('effective_status')} · orçamento {orc:.2f} €/dia")
    print(f"Janela: {rng['since']} → {rng['until']} (fuso da conta: {conta.get('timezone_name')})\n")

    dias = meta.get_todos(f"{est['campanha_id']}/insights", {
        "fields": CAMPOS, "time_range": rng, "time_increment": 1}, cfg)
    print(f"{'dia':<11}{'gasto':>10}{'impr.':>9}{'cliques':>9}{'CTR':>7}{'CPM':>9}{'inscr.':>8}{'custo/inscr.':>14}")
    tot_gasto = tot_lead = 0.0
    for d in dias:
        g, l = float(d.get("spend", 0)), acao(d, TIPOS_LEAD)
        tot_gasto, tot_lead = tot_gasto + g, tot_lead + l
        print(f"{d['date_start']:<11}{eur(g):>10}{d.get('impressions', 0):>9}{d.get('inline_link_clicks', 0):>9}"
              f"{float(d.get('inline_link_click_ctr', 0)):>6.2f}%{eur(d.get('cpm')):>9}{l:>8}"
              f"{(eur(g / l) if l else '—'):>14}")
    print(f"{'TOTAL':<11}{eur(tot_gasto):>10}{'':>34}{int(tot_lead):>8}"
          f"{(eur(tot_gasto / tot_lead) if tot_lead else '—'):>14}")

    hoje_linha = next((d for d in dias if d.get("date_start") == hoje.isoformat()), None)
    if orc and hoje_linha:
        frac = (agora.hour * 60 + agora.minute) / 1440
        gasto_hoje = float(hoje_linha.get("spend", 0))
        esperado = orc * frac
        ritmo = gasto_hoje / esperado * 100 if esperado else 0
        print(f"\nRitmo de hoje: gastou {eur(gasto_hoje)} de {eur(orc)} ({gasto_hoje / orc * 100:.0f}% do orçamento) "
              f"com {frac * 100:.0f}% do dia passado → {ritmo:.0f}% do ritmo esperado")
        if frac < 0.5:
            print("   (antes do meio-dia o ritmo engana: não decidir só por ele)")

    ads = meta.get_todos(f"{est['campanha_id']}/insights", {
        "fields": "ad_id,ad_name," + CAMPOS, "time_range": rng, "level": "ad"}, cfg)
    print(f"\nPOR ANÚNCIO ({rng['since']} → {rng['until']})")
    for a in sorted(ads, key=lambda x: -float(x.get("spend", 0))):
        g, l = float(a.get("spend", 0)), acao(a, TIPOS_LEAD)
        print(f"  {a.get('ad_name')}: gasto {eur(g)} · CTR {float(a.get('inline_link_click_ctr', 0)):.2f}% · "
              f"CPM {eur(a.get('cpm'))} · freq {float(a.get('frequency', 0)):.2f} · inscr. {l} · "
              f"custo/inscr. {eur(g / l) if l else '—'}")

    total = meta.get_todos(f"{est['campanha_id']}/insights", {
        "fields": "spend,reach,frequency,actions", "date_preset": "maximum"}, cfg)
    if total:
        t = total[0]
        g = float(t.get("spend", 0))
        print(f"\nDESDE O INÍCIO: gasto {eur(g)} · alcance {t.get('reach')} · frequência {float(t.get('frequency', 0)):.2f}"
              f" · inscrições (pixel) {acao(t, TIPOS_LEAD)} · compras (pixel) {acao(t, TIPOS_COMPRA)}")
        if args.inscricoes_pagas:
            print(f"CUSTO REAL por inscrição paga: {eur(g / args.inscricoes_pagas)} "
                  f"({args.inscricoes_pagas} inscrições pagas contadas fora da Meta)")
        else:
            print("Para o custo REAL, corre de novo com --inscricoes-pagas N (inscrições pagas confirmadas).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
