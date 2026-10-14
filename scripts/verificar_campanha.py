"""Confere, objeto a objeto e pelo ID, o que ficou criado na Meta.

Uso:  python scripts/verificar_campanha.py resultados/evento-31-10.ids.json
Só lê. A listagem do Gestor de Anúncios às vezes atrasa: aqui cada objeto é lido pelo ID.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
import meta  # noqa: E402

URL_TIMEOUT = meta._env_int("META_URL_TIMEOUT", 30)


def main() -> int:
    if len(sys.argv) < 2:
        meta.falhar("uso: python scripts/verificar_campanha.py resultados/<plano>.ids.json")
    caminho = Path(sys.argv[1])
    caminho = caminho if caminho.is_absolute() else RAIZ / caminho
    est = json.loads(caminho.read_text(encoding="utf-8"))
    cfg = meta.carregar_config()
    problemas = 0

    camp = meta.get(est["campanha_id"], {
        "fields": "name,status,effective_status,objective,daily_budget,bid_strategy,issues_info"}, cfg)
    print(f"CAMPANHA {camp['name']} [{est['campanha_id']}]")
    print(f"  estado: {camp.get('status')} / efetivo {camp.get('effective_status')} · objetivo {camp.get('objective')}")
    print(f"  orçamento diário: {int(camp.get('daily_budget', 0)) / 100:.2f} € · lance {camp.get('bid_strategy')}")
    for i in camp.get("issues_info") or []:
        problemas += 1
        print(f"  🔴 {i.get('error_message') or i}")

    conj = meta.get(est["conjunto_id"], {
        "fields": "name,status,effective_status,start_time,end_time,optimization_goal,promoted_object,"
                  "bid_amount,targeting,issues_info"}, cfg)
    print(f"\nCONJUNTO {conj['name']} [{est['conjunto_id']}]")
    print(f"  estado: {conj.get('status')} / efetivo {conj.get('effective_status')}")
    print(f"  início {conj.get('start_time')} · fim {conj.get('end_time')}")
    print(f"  otimiza: {conj.get('optimization_goal')} → {conj.get('promoted_object')}")
    if conj.get("bid_amount"):
        print(f"  lance: {int(conj['bid_amount']) / 100:.2f} €")
    geo = conj.get("targeting", {}).get("geo_locations", {})
    print(f"  geografia: {json.dumps(geo, ensure_ascii=False)}")
    for i in conj.get("issues_info") or []:
        problemas += 1
        print(f"  🔴 {i.get('error_message') or i}")

    print(f"\nANÚNCIOS ({len(est.get('anuncios', {}))})")
    destinos = set()
    for nome, reg in est.get("anuncios", {}).items():
        ad = meta.get(reg["anuncio_id"], {"fields": "status,effective_status,ad_review_feedback,issues_info"}, cfg)
        cr = meta.get(reg["criativo_id"], {"fields": "url_tags,object_story_spec"}, cfg)
        oss = cr.get("object_story_spec", {})
        bloco = oss.get("link_data") or oss.get("video_data") or {}
        destino = bloco.get("link") or bloco.get("call_to_action", {}).get("value", {}).get("link")
        destinos.add(destino)
        tags_ok = "sck=" in (cr.get("url_tags") or "")
        print(f"  • {nome} [{reg['anuncio_id']}] {ad.get('status')} / {ad.get('effective_status')}")
        print(f"      rastreio no criativo: {'✅' if tags_ok else '🔴 sem sck'} · destino: {destino}")
        problemas += 0 if tags_ok else 1
        fb = ad.get("ad_review_feedback")
        if fb:
            problemas += 1
            print(f"      🔴 revisão da Meta: {json.dumps(fb, ensure_ascii=False)}")
        for i in ad.get("issues_info") or []:
            problemas += 1
            print(f"      🔴 {i.get('error_message') or i}")
        if ad.get("effective_status") in ("DISAPPROVED", "WITH_ISSUES"):
            problemas += 1

    for d in filter(None, destinos):
        try:
            req = urllib.request.Request(d, headers={"User-Agent": "Mozilla/5.0", "Accept": "text/html"})
            with urllib.request.urlopen(req, timeout=URL_TIMEOUT) as r:
                print(f"\n{'✅' if r.status == 200 else '🔴'} destino responde HTTP {r.status}: {d}")
        except Exception as e:  # noqa: BLE001
            problemas += 1
            print(f"\n🔴 destino não responde: {d} ({e})")
    print("   (abre o destino no telemóvel e confirma que o botão de inscrição funciona — o HTTP 200 não prova isso)")

    print()
    if len(est.get("anuncios", {})) < 3:
        problemas += 1
        print("🔴 menos de 3 anúncios no conjunto")
    print("🔴 Há problemas a resolver." if problemas else "✅ Tudo conferido.")
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())
