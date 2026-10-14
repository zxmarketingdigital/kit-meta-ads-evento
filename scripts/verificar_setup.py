"""Confere se a configuração da Meta está pronta para criar a campanha.

Uso:  python scripts/verificar_setup.py [--url https://eventos.be-pro.pt/ia-contactos/]
Só lê. Não cria nem altera nada.
"""
from __future__ import annotations

import argparse
import sys
import time
import urllib.request

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
import meta  # noqa: E402

URL_TIMEOUT = meta._env_int("META_URL_TIMEOUT", 30)
ESTADOS_CONTA = {1: "ATIVA", 2: "DESATIVADA", 3: "COM PAGAMENTO EM FALTA", 7: "EM REVISÃO DE RISCO",
                 8: "PAGAMENTO PENDENTE", 9: "EM PERÍODO DE TOLERÂNCIA", 100: "PENDENTE DE FECHO", 101: "FECHADA"}


def linha(ok: bool | None, texto: str):
    marca = {True: "✅", False: "🔴", None: "🟡"}[ok]
    print(f"{marca} {texto}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="https://eventos.be-pro.pt/ia-contactos/")
    args = ap.parse_args()

    cfg = meta.carregar_config()
    falhas = 0

    try:
        me = meta.get("me", {"fields": "id,name"}, cfg)
        linha(True, f"Token válido (utilizador: {me.get('name', me.get('id'))})")
    except meta.MetaErro as e:
        linha(False, f"Token inválido ou expirado: {e}")
        return 1

    try:
        c = meta.get(cfg["META_AD_ACCOUNT_ID"], {
            "fields": "name,account_status,currency,timezone_name,disable_reason,amount_spent"}, cfg)
        estado = c.get("account_status")
        ok = estado == 1
        linha(ok, f"Conta de anúncios {c.get('name')} — {ESTADOS_CONTA.get(estado, estado)} · "
                  f"moeda {c.get('currency')} · fuso {c.get('timezone_name')}")
        falhas += 0 if ok else 1
        if c.get("currency") != "EUR":
            linha(False, f"A conta está em {c.get('currency')}: este kit trabalha em euros. Usa uma conta em EUR.")
            falhas += 1
    except meta.MetaErro as e:
        linha(False, f"Sem acesso à conta {cfg['META_AD_ACCOUNT_ID']}: {e}")
        falhas += 1

    try:
        p = meta.get(cfg["META_PAGE_ID"], {"fields": "name"}, cfg)
        linha(True, f"Página: {p.get('name')}")
    except meta.MetaErro as e:
        linha(False, f"Sem acesso à página {cfg['META_PAGE_ID']}: {e}")
        falhas += 1

    try:
        px = meta.get(cfg["META_PIXEL_ID"], {"fields": "name,last_fired_time,is_unavailable"}, cfg)
        disparo = px.get("last_fired_time")
        linha(bool(disparo), f"Pixel {px.get('name')} — último disparo: {disparo or 'NUNCA disparou'}")
        if not disparo:
            falhas += 1
        try:
            stats = meta.get(f"{cfg['META_PIXEL_ID']}/stats", {
                "aggregation": "event", "start_time": int(time.time()) - 7 * 86400}, cfg)
            eventos: dict[str, int] = {}
            for bloco in stats.get("data", []):
                for d in bloco.get("data", []):
                    eventos[d.get("value")] = eventos.get(d.get("value"), 0) + int(d.get("count", 0))
            if eventos:
                linha(True, "Eventos do pixel nos últimos 7 dias: " +
                      ", ".join(f"{k}={v}" for k, v in sorted(eventos.items())))
            lead = eventos.get("Lead", 0)
            linha(lead > 0 or None, f"Evento Lead (inscrição) nos últimos 7 dias: {lead}"
                  + ("" if lead else " — faz uma inscrição de teste na página e corre de novo"))
        except meta.MetaErro as e:
            linha(None, f"Não consegui ler as estatísticas do pixel: {e}")
    except meta.MetaErro as e:
        linha(False, f"Sem acesso ao pixel {cfg['META_PIXEL_ID']}: {e}")
        falhas += 1

    if cfg.get("META_INSTAGRAM_ID"):
        try:
            ig = meta.get(cfg["META_INSTAGRAM_ID"], {"fields": "username"}, cfg)
            linha(True, f"Instagram: @{ig.get('username')}")
        except meta.MetaErro as e:
            linha(None, f"Instagram configurado mas sem acesso ({e}) — os anúncios saem só com a página")

    try:
        req = urllib.request.Request(args.url, headers={"User-Agent": "Mozilla/5.0", "Accept": "text/html"})
        with urllib.request.urlopen(req, timeout=URL_TIMEOUT) as r:
            linha(r.status == 200, f"Página de inscrição responde HTTP {r.status}: {args.url}")
    except Exception as e:  # noqa: BLE001
        linha(False, f"Página de inscrição não responde: {e}")
        falhas += 1

    print()
    if falhas:
        print(f"🔴 {falhas} item(ns) a corrigir antes de criar a campanha (ver docs/).")
        return 1
    print("✅ Tudo pronto para criar a campanha.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
