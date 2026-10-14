"""Cria a campanha do evento a partir de campanha/<ficheiro>.json.

Uso:
  python scripts/criar_campanha.py campanha/evento-31-10.json            # SIMULAÇÃO: só mostra o plano
  python scripts/criar_campanha.py campanha/evento-31-10.json --criar    # cria tudo PAUSADO
  python scripts/criar_campanha.py campanha/evento-31-10.json --ativar --sim   # liga (depois de rever)

Regras embutidas (vêm de campanhas reais, não mudar sem motivo):
- 1 campanha = 1 conjunto, orçamento diário na campanha (CBO); lance, se houver, no conjunto.
- Tudo nasce PAUSADO. Ativar é um passo separado, só com início no futuro.
- Mínimo de 3 anúncios por conjunto.
- Parâmetros de rastreio (sck) ficam DENTRO do criativo (url_tags). Fora dele a Meta ignora.
- Melhorias automáticas de criativo (Advantage+ creative / animação de imagem) desligadas.
- Idempotente: guarda os IDs em resultados/ e reaproveita o que já foi criado.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
import meta  # noqa: E402

VIDEO_ESPERA = meta._env_int("META_VIDEO_ESPERA", 600)
IMAGENS = {".png", ".jpg", ".jpeg"}
VIDEOS = {".mp4", ".mov"}
CTAS = {"LEARN_MORE", "SIGN_UP", "BOOK_TRAVEL", "GET_OFFER", "APPLY_NOW", "SUBSCRIBE", "REGISTER_NOW"}
OBJETIVO = {"LEAD": "OUTCOME_LEADS", "COMPLETE_REGISTRATION": "OUTCOME_LEADS", "PURCHASE": "OUTCOME_SALES"}
LANCES = {"LOWEST_COST_WITHOUT_CAP", "LOWEST_COST_WITH_BID_CAP", "COST_CAP"}
URL_TAGS = "utm_source=meta&utm_medium=paid&utm_campaign={{campaign.name}}&utm_content={{ad.name}}&sck=meta-{{ad.id}}"
DOF = {"creative_features_spec": {"image_animation": {"enroll_status": "OPT_OUT"},
                                  "advantage_plus_creative": {"enroll_status": "OPT_OUT"}}}


def tem_a_definir(valor) -> bool:
    if isinstance(valor, str):
        return "A_DEFINIR" in valor
    if isinstance(valor, dict):
        return any(tem_a_definir(v) for k, v in valor.items() if not k.startswith("_"))
    if isinstance(valor, list):
        return any(tem_a_definir(v) for v in valor)
    return False


def validar(plano: dict) -> list[str]:
    erros: list[str] = []
    c, p, ads = plano.get("campanha", {}), plano.get("publico", {}), plano.get("anuncios", [])
    ev = plano.get("evento", {})
    for chave, bloco in (("evento", ev), ("campanha", c), ("publico", p), ("anuncios", ads)):
        if tem_a_definir(bloco):
            erros.append(f"'{chave}' ainda tem campos A_DEFINIR")
    if c.get("evento_otimizacao") not in OBJETIVO:
        erros.append(f"evento_otimizacao tem de ser um de {sorted(OBJETIVO)}")
    if c.get("estrategia_lance") not in LANCES:
        erros.append(f"estrategia_lance tem de ser um de {sorted(LANCES)}")
    if c.get("estrategia_lance") != "LOWEST_COST_WITHOUT_CAP" and not c.get("lance_eur"):
        erros.append("estrategia com limite exige lance_eur")
    if not str(ev.get("landing_page", "")).startswith("https://"):
        erros.append("evento.landing_page tem de ser um endereço https://")
    if not tem_a_definir(c):
        for campo in ("orcamento_diario_eur",) + (("lance_eur",) if c.get("lance_eur") is not None else ()):
            try:
                v = float(c[campo])
                if not math.isfinite(v) or v <= 0:
                    erros.append(f"{campo} tem de ser um número > 0")
            except (TypeError, ValueError, KeyError):
                erros.append(f"{campo} inválido")
        datas = {}
        for campo in ("inicio", "fim"):
            try:
                datas[campo] = dt.datetime.fromisoformat(str(c[campo]))
                if datas[campo].tzinfo is None:
                    erros.append(f"{campo} precisa do fuso (ex.: +01:00)")
                    datas.pop(campo)
            except (ValueError, KeyError):
                erros.append(f"{campo} não é data ISO válida")
        if len(datas) == 2 and datas["fim"] <= datas["inicio"]:
            erros.append("fim tem de ser depois do início")
    if not tem_a_definir(p):
        for campo in ("latitude", "longitude", "raio_km", "idade_min", "idade_max"):
            try:
                if not math.isfinite(float(p[campo])):
                    raise ValueError
            except (TypeError, ValueError, KeyError):
                erros.append(f"publico.{campo} inválido")
    if len(ads) < 3:
        erros.append(f"são precisos pelo menos 3 anúncios (há {len(ads)})")
    nomes = [a.get("nome") for a in ads]
    if len(set(nomes)) != len(nomes):
        erros.append("há anúncios com o mesmo nome")
    for a in ads:
        if tem_a_definir(a):
            continue
        f = RAIZ / a.get("ficheiro", "")
        if not f.is_file():
            erros.append(f"{a.get('nome')}: ficheiro não encontrado ({a.get('ficheiro')})")
        elif f.suffix.lower() not in IMAGENS | VIDEOS:
            erros.append(f"{a.get('nome')}: formato {f.suffix} não suportado (usa png/jpg/mp4/mov)")
        if a.get("cta", "LEARN_MORE") not in CTAS:
            erros.append(f"{a.get('nome')}: cta tem de ser um de {sorted(CTAS)}")
        if not a.get("texto") or not a.get("titulo"):
            erros.append(f"{a.get('nome')}: texto e titulo são obrigatórios")
    return erros


def mostrar_plano(plano: dict, cfg: dict):
    c, p, e = plano["campanha"], plano["publico"], plano["evento"]
    print("PLANO DA CAMPANHA")
    print(f"  Conta: {cfg['META_AD_ACCOUNT_ID']} · Página: {cfg['META_PAGE_ID']} · Pixel: {cfg['META_PIXEL_ID']}")
    print(f"  Campanha: {c['nome']}  ({OBJETIVO.get(c['evento_otimizacao'], '?')}, otimiza para {c['evento_otimizacao']})")
    print(f"  Orçamento diário: {c['orcamento_diario_eur']} € · Lance: {c['estrategia_lance']}"
          + (f" {c['lance_eur']} €" if c.get("lance_eur") else ""))
    print(f"  Início: {c['inicio']} · Fim: {c['fim']}")
    print(f"  Público: raio {p['raio_km']} km de ({p['latitude']}, {p['longitude']}) · idades {p['idade_min']}–{p['idade_max']}")
    print(f"  Destino: {e['landing_page']}")
    print(f"  Rastreio no criativo: {URL_TAGS}")
    for a in plano["anuncios"]:
        print(f"  • {a['nome']} — {a['ficheiro']} — CTA {a.get('cta', 'LEARN_MORE')}")
        print(f"      título: {a['titulo']}")
        print(f"      texto: {a['texto'][:160]}{'…' if len(a['texto']) > 160 else ''}")


def carregar_estado(caminho: Path) -> dict:
    if caminho.exists():
        return json.loads(caminho.read_text(encoding="utf-8"))
    return {"anuncios": {}}


def gravar_estado(caminho: Path, estado: dict):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tmp = caminho.with_suffix(".tmp")
    tmp.write_text(json.dumps(estado, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(caminho)


def existe_por_nome(cfg: dict, edge: str, nome: str, filtro_pai: tuple[str, str] | None = None) -> str | None:
    """Procura objeto já criado com o mesmo nome (evita duplicar depois de uma falha a meio)."""
    filtros = [{"field": "name", "operator": "EQUAL", "value": nome}]
    campos = {"campaigns": "id,name", "adsets": "id,name,campaign_id", "ads": "id,name,campaign_id,adset_id"}[edge]
    itens = meta.get_todos(f"{cfg['META_AD_ACCOUNT_ID']}/{edge}", {"fields": campos, "filtering": filtros}, cfg)
    for it in itens:
        if it.get("name") != nome:
            continue
        if filtro_pai and it.get(filtro_pai[0]) != filtro_pai[1]:
            continue
        return it["id"]
    return None


def _instante(valor: str) -> dt.datetime:
    v = str(valor)
    if len(v) > 5 and v[-5] in "+-" and v[-3] != ":":
        v = v[:-2] + ":" + v[-2:]  # a Meta devolve +0100; fromisoformat antigo quer +01:00
    return dt.datetime.fromisoformat(v)


def conteudo_anuncio(a: dict, link: str) -> str:
    chaves = ("texto", "titulo", "descricao", "cta", "ficheiro")
    base = json.dumps([a.get(k, "") for k in chaves] + [link], ensure_ascii=False)
    f = RAIZ / a.get("ficheiro", "")
    dig = hashlib.sha256(base.encode("utf-8"))
    if f.is_file():
        dig.update(f.read_bytes())
    return dig.hexdigest()


def conferir_anuncio(reg: dict, a: dict, link: str):
    if reg.get("conteudo") and reg["conteudo"] != conteudo_anuncio(a, link):
        meta.falhar(f"o anúncio '{a['nome']}' já foi criado e o plano mudou (texto, título, CTA, ficheiro ou link). "
                    "Editar um anúncio já criado não é aplicado. Dá-lhe um nome novo no plano para criar um anúncio "
                    "novo, e pausa o antigo com scripts/ajustar.py.")


def conferir_existente(cfg: dict, est: dict, c: dict, p: dict):
    """Ao reaproveitar campanha/conjunto já criados, recusar se o plano mudou (senão o plano novo não é aplicado)."""
    dif = []
    camp = meta.get(est["campanha_id"], {"fields": "daily_budget,bid_strategy,objective"}, cfg)
    if camp.get("objective") != OBJETIVO[c["evento_otimizacao"]]:
        dif.append(f"objetivo na Meta {camp.get('objective')} ≠ plano {OBJETIVO[c['evento_otimizacao']]}")
    if int(camp.get("daily_budget") or 0) != meta.euros_para_centimos(c["orcamento_diario_eur"]):
        dif.append(f"orçamento na Meta {int(camp.get('daily_budget') or 0) / 100:.2f} € ≠ plano {c['orcamento_diario_eur']} €")
    if camp.get("bid_strategy") != c["estrategia_lance"]:
        dif.append(f"lance na Meta {camp.get('bid_strategy')} ≠ plano {c['estrategia_lance']}")
    if est.get("conjunto_id"):
        conj = meta.get(est["conjunto_id"], {
            "fields": "start_time,end_time,bid_amount,targeting,promoted_object,optimization_goal"}, cfg)
        if (conj.get("promoted_object") or {}).get("custom_event_type") != c["evento_otimizacao"]:
            dif.append(f"evento na Meta {(conj.get('promoted_object') or {}).get('custom_event_type')} "
                       f"≠ plano {c['evento_otimizacao']}")
        tg = conj.get("targeting") or {}
        locs = (tg.get("geo_locations") or {}).get("custom_locations") or []
        loc = locs[0] if len(locs) == 1 else {}
        geo_ok = (len(locs) == 1 and abs(float(loc.get("latitude", 999)) - float(p["latitude"])) < 1e-4
                  and abs(float(loc.get("longitude", 999)) - float(p["longitude"])) < 1e-4
                  and abs(float(loc.get("radius", -1)) - float(p["raio_km"])) < 1e-6)
        if not geo_ok:
            dif.append(f"geografia na Meta {locs} ≠ plano ({p['latitude']}, {p['longitude']}) raio {p['raio_km']} km")
        if int(tg.get("age_min", 0)) != int(p["idade_min"]) or int(tg.get("age_max", 0)) != int(p["idade_max"]):
            dif.append(f"idades na Meta {tg.get('age_min')}–{tg.get('age_max')} ≠ plano {p['idade_min']}–{p['idade_max']}")
        for campo, chave in (("start_time", "inicio"), ("end_time", "fim")):
            if conj.get(campo) and _instante(conj[campo]) != dt.datetime.fromisoformat(c[chave]):
                dif.append(f"{chave} na Meta {conj[campo]} ≠ plano {c[chave]}")
        if c["estrategia_lance"] != "LOWEST_COST_WITHOUT_CAP" and \
                int(conj.get("bid_amount") or 0) != meta.euros_para_centimos(c["lance_eur"]):
            dif.append(f"lance na Meta {int(conj.get('bid_amount') or 0) / 100:.2f} € ≠ plano {c['lance_eur']} €")
    if dif:
        meta.falhar("a campanha já existe e está diferente do plano:\n   - " + "\n   - ".join(dif) +
                    "\nPara mudar o que já existe usa scripts/ajustar.py (orçamento, lance, início). "
                    "Para começar de novo, muda o nome da campanha no plano.")


def esperar_video(cfg: dict, video_id: str) -> str:
    t0 = time.monotonic()
    while time.monotonic() - t0 < VIDEO_ESPERA:
        v = meta.get(video_id, {"fields": "status"}, cfg)
        estado = v.get("status", {}).get("video_status")
        if estado == "ready":
            print(f"  vídeo {video_id} pronto em {time.monotonic() - t0:.0f}s")
            thumbs = meta.get(f"{video_id}/thumbnails", {}, cfg).get("data", [])
            preferida = next((t for t in thumbs if t.get("is_preferred")), thumbs[0] if thumbs else None)
            if not preferida:
                meta.falhar(f"vídeo {video_id} sem miniatura disponível")
            return preferida["uri"]
        if estado == "error":
            meta.falhar(f"a Meta rejeitou o processamento do vídeo {video_id}")
        time.sleep(10)
    meta.falhar(f"vídeo {video_id} não ficou pronto em {VIDEO_ESPERA}s (aumenta META_VIDEO_ESPERA e corre de novo)")
    return ""


def criar(plano: dict, cfg: dict, estado_path: Path):
    c, p, e = plano["campanha"], plano["publico"], plano["evento"]
    est = carregar_estado(estado_path)
    act = cfg["META_AD_ACCOUNT_ID"]
    link = e["landing_page"]
    meta.exigir_eur(cfg)

    inicio = dt.datetime.fromisoformat(c["inicio"])
    if inicio <= dt.datetime.now(dt.timezone.utc):
        meta.falhar(f"início {c['inicio']} já passou. Escolhe a próxima meia-noite de Lisboa.")

    if not est.get("campanha_id"):
        est["campanha_id"] = existe_por_nome(cfg, "campaigns", c["nome"])
    if not est.get("campanha_id"):
        r = meta.post(f"{act}/campaigns", {
            "name": c["nome"],
            "objective": OBJETIVO[c["evento_otimizacao"]],
            "status": "PAUSED",
            "special_ad_categories": [],
            "buying_type": "AUCTION",
            "daily_budget": meta.euros_para_centimos(c["orcamento_diario_eur"]),
            "bid_strategy": c["estrategia_lance"],
        }, cfg)
        est["campanha_id"] = r["id"]
        gravar_estado(estado_path, est)
        print(f"✅ campanha criada: {r['id']}")
    else:
        print(f"↩️  campanha já existe: {est['campanha_id']}")
    gravar_estado(estado_path, est)

    nome_conjunto = c["nome"] + " | CONJUNTO"
    if not est.get("conjunto_id"):
        est["conjunto_id"] = existe_por_nome(cfg, "adsets", nome_conjunto, ("campaign_id", est["campanha_id"]))
    if not est.get("conjunto_id"):
        dados = {
            "name": nome_conjunto,
            "campaign_id": est["campanha_id"],
            "status": "PAUSED",
            "billing_event": "IMPRESSIONS",
            "optimization_goal": "OFFSITE_CONVERSIONS",
            "destination_type": "WEBSITE",
            "promoted_object": {"pixel_id": cfg["META_PIXEL_ID"], "custom_event_type": c["evento_otimizacao"]},
            "start_time": c["inicio"],
            "end_time": c["fim"],
            "targeting": {
                "geo_locations": {
                    "custom_locations": [{"latitude": p["latitude"], "longitude": p["longitude"],
                                          "radius": p["raio_km"], "distance_unit": "kilometer"}],
                    "location_types": ["home"],
                },
                "age_min": int(p["idade_min"]),
                "age_max": int(p["idade_max"]),
                "targeting_automation": {"advantage_audience": 0},
            },
        }
        if c["estrategia_lance"] != "LOWEST_COST_WITHOUT_CAP":
            dados["bid_amount"] = meta.euros_para_centimos(c["lance_eur"])
        r = meta.post(f"{act}/adsets", dados, cfg)
        est["conjunto_id"] = r["id"]
        gravar_estado(estado_path, est)
        print(f"✅ conjunto criado: {r['id']}")
    else:
        print(f"↩️  conjunto já existe: {est['conjunto_id']}")
    gravar_estado(estado_path, est)
    conferir_existente(cfg, est, c, p)

    for a in plano["anuncios"]:
        reg = est["anuncios"].setdefault(a["nome"], {})
        conferir_anuncio(reg, a, link)
        if reg.get("anuncio_id"):
            print(f"↩️  {a['nome']} já existe: {reg['anuncio_id']}")
            continue
        f = RAIZ / a["ficheiro"]
        cta = {"type": a.get("cta", "LEARN_MORE"), "value": {"link": link}}

        if not reg.get("criativo_id"):
            if f.suffix.lower() in IMAGENS:
                if not reg.get("image_hash"):
                    r = meta.upload(f"{act}/adimages", f, "filename", cfg=cfg)
                    reg["image_hash"] = next(iter(r["images"].values()))["hash"]
                    gravar_estado(estado_path, est)
                story = {"page_id": cfg["META_PAGE_ID"], "link_data": {
                    "image_hash": reg["image_hash"], "link": link, "message": a["texto"],
                    "name": a["titulo"], "description": a.get("descricao", ""), "call_to_action": cta}}
            else:
                if not reg.get("video_id"):
                    r = meta.upload(f"{act}/advideos", f, "source", {"name": a["nome"]}, cfg)
                    reg["video_id"] = r["id"]
                    gravar_estado(estado_path, est)
                miniatura = esperar_video(cfg, reg["video_id"])
                story = {"page_id": cfg["META_PAGE_ID"], "video_data": {
                    "video_id": reg["video_id"], "image_url": miniatura, "message": a["texto"],
                    "title": a["titulo"], "link_description": a.get("descricao", ""), "call_to_action": cta}}
            if cfg.get("META_INSTAGRAM_ID"):
                story["instagram_user_id"] = cfg["META_INSTAGRAM_ID"]
            r = meta.post(f"{act}/adcreatives", {
                "name": f"{a['nome']} | criativo",
                "object_story_spec": story,
                "url_tags": URL_TAGS,
                "degrees_of_freedom_spec": DOF,
            }, cfg)
            reg["criativo_id"] = r["id"]
            reg["conteudo"] = conteudo_anuncio(a, link)
            gravar_estado(estado_path, est)

        existente = existe_por_nome(cfg, "ads", a["nome"], ("adset_id", est["conjunto_id"]))
        if existente:
            reg["anuncio_id"] = existente
        else:
            r = meta.post(f"{act}/ads", {
                "name": a["nome"], "adset_id": est["conjunto_id"],
                "creative": {"creative_id": reg["criativo_id"]}, "status": "PAUSED"}, cfg)
            reg["anuncio_id"] = r["id"]
        gravar_estado(estado_path, est)
        print(f"✅ {a['nome']}: anúncio {reg['anuncio_id']} (criativo {reg['criativo_id']})")

    print(f"\nIDs gravados em {estado_path.relative_to(RAIZ)}")
    print("Próximo passo: python scripts/verificar_campanha.py " + str(estado_path.relative_to(RAIZ)))


def ativar(plano: dict, cfg: dict, estado_path: Path):
    est = carregar_estado(estado_path)
    c = plano["campanha"]
    erros = validar(plano)
    if erros:
        meta.falhar("o plano tem erros, não ativo:\n   - " + "\n   - ".join(erros))
    if not est.get("campanha_id") or not est.get("conjunto_id"):
        meta.falhar("nada criado ainda. Corre primeiro com --criar.")
    faltam = [a["nome"] for a in plano["anuncios"] if not est["anuncios"].get(a["nome"], {}).get("anuncio_id")]
    if faltam:
        meta.falhar(f"anúncios do plano ainda não criados: {faltam}. Corre --criar de novo antes de ativar.")
    meta.exigir_eur(cfg)
    conferir_existente(cfg, est, c, plano["publico"])
    for a in plano["anuncios"]:
        conferir_anuncio(est["anuncios"][a["nome"]], a, plano["evento"]["landing_page"])
    ids_plano = {est["anuncios"][a["nome"]]["anuncio_id"] for a in plano["anuncios"]}
    no_conjunto = meta.get_todos(f"{est['conjunto_id']}/ads", {"fields": "id,name,status"}, cfg)
    intrusos = [f"{x.get('name')} [{x['id']}]" for x in no_conjunto
                if x["id"] not in ids_plano and x.get("status") == "ACTIVE"]
    if intrusos:
        meta.falhar(f"há anúncios ativos no conjunto que não estão no plano: {intrusos}. Ligar o conjunto pô-los-ia "
                    "a gastar. Pausa-os no Gestor de Anúncios (ou acrescenta-os ao plano) e ativa de novo.")
    fora = [n for n in est["anuncios"] if n not in {a["nome"] for a in plano["anuncios"]}]
    conj = meta.get(est["conjunto_id"], {"fields": "start_time,end_time"}, cfg)
    if _instante(conj["start_time"]) <= dt.datetime.now(dt.timezone.utc):
        meta.falhar(f"o início do conjunto ({conj['start_time']}) já passou. Ligar agora começa a meio do dia "
                    "e gasta o orçamento em poucas horas. Muda o início para a próxima meia-noite "
                    "(python scripts/ajustar.py <ids> --inicio <data> --sim) e ativa de novo.")
    print(f"A ATIVAR: {c['nome']} · {c['orcamento_diario_eur']} €/dia · {conj['start_time']} → {conj.get('end_time')}")
    for a in plano["anuncios"]:
        meta.post(est["anuncios"][a["nome"]]["anuncio_id"], {"status": "ACTIVE"}, cfg)
        print(f"✅ anúncio ativo: {a['nome']}")
    if fora:
        print(f"⚠️  ficam como estão (não estão no plano): {fora}")
    meta.post(est["conjunto_id"], {"status": "ACTIVE"}, cfg)
    meta.post(est["campanha_id"], {"status": "ACTIVE"}, cfg)
    print(f"✅ campanha e conjunto ativos — entregam a partir de {conj['start_time']}")
    print("Confere: python scripts/verificar_campanha.py " + str(estado_path.relative_to(RAIZ)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("plano")
    modo = ap.add_mutually_exclusive_group()
    modo.add_argument("--criar", action="store_true", help="cria tudo PAUSADO")
    modo.add_argument("--ativar", action="store_true", help="liga anúncios, conjunto e campanha")
    ap.add_argument("--sim", action="store_true", help="confirmação obrigatória para --ativar")
    args = ap.parse_args()

    plano_path = (RAIZ / args.plano) if not Path(args.plano).is_absolute() else Path(args.plano)
    plano = json.loads(plano_path.read_text(encoding="utf-8"))
    estado_path = RAIZ / "resultados" / (plano_path.stem + ".ids.json")
    cfg = meta.carregar_config()

    if args.ativar:
        if not args.sim:
            meta.falhar("--ativar liga a campanha e começa a gastar. Repete com --sim para confirmar.")
        try:
            ativar(plano, cfg, estado_path)
        except meta.MetaErro as e:
            meta.falhar(f"a Meta recusou: {e}\nConfere o estado com scripts/verificar_campanha.py antes de repetir.")
        return 0

    erros = validar(plano)
    if erros:
        print("🔴 O plano ainda não está pronto:")
        for e in erros:
            print(f"   - {e}")
        return 1
    mostrar_plano(plano, cfg)
    if not args.criar:
        print("\n(SIMULAÇÃO — nada foi criado. Para criar tudo PAUSADO: acrescenta --criar)")
        return 0
    try:
        criar(plano, cfg, estado_path)
    except meta.MetaErro as e:
        meta.falhar(f"a Meta recusou: {e}\nO que já foi criado está em {estado_path.relative_to(RAIZ)}; "
                    "corrige e corre de novo — o script reaproveita o que existe.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
